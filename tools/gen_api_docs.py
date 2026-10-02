#!/usr/bin/env python3
"""Generate a Blender-style API reference for a Blender extension, statically.

The code is parsed with :mod:`ast`; nothing is imported, so this runs with any
Python 3.11+ outside Blender. Shared by MUFIS and MyoGeneratorRemix (owned by
MUFIS, copied by ``tools/sync_shared.py``).

What is documented
------------------
* **Operators** (classes with ``bl_idname`` deriving from ``Operator``) as
  ``bpy.ops.<ns>.<name>(prop=default, ...)`` with a parameter table built from
  their property annotations, like Blender's ``bpy.ops`` pages.
* **Property groups / preferences** with the path where they are registered
  (``bpy.types.Scene.mufis_props`` ...) and one row per property.
* **Panels** (id, category, label).
* **Modules**: module docstring, public functions and classes (signature +
  docstring, with Sphinx ``:arg:/:type:/:return:/:rtype:/:raises:/:ivar:``
  fields rendered as tables).

Docstring convention (Blender's own)::

    def metres_per_unit(scene):
        \"\"\"Length of one Blender unit in metres.

        :arg scene: Scene whose unit settings are read.
        :type scene: :class:`bpy.types.Scene`
        :return: Metres per Blender unit.
        :rtype: float
        \"\"\"

Configuration: ``devdocs/apidoc.toml`` at the repository root::

    name = "MUFIS"                 # title
    package = "."                  # package directory, relative to the repo root
    exclude = ["tools", "boneload/boneload.py"]   # path prefixes to skip
    identity = "identity.py"       # optional: module defining OP_NS & co.
    out = "devdocs/reference"      # Markdown output
    quarto = "website/developer/reference"     # optional: also write .qmd pages here
    [quarto_pages]                             # optional: hand-written pages to publish,
    "devdocs/ARCHITECTURE.md" = "index.qmd"    # relative to the parent of `quarto`

Usage::

    python tools/gen_api_docs.py            # write the reference
    python tools/gen_api_docs.py --check    # report undocumented API, exit 1 if any
"""

import argparse
import ast
import os
import re
import sys
import tomllib

STANDARD_METHODS = {"execute", "invoke", "poll", "draw", "modal", "cancel", "check", "description",
                    "register", "unregister", "__init__", "__repr__", "__str__"}
PROP_TYPES = {"BoolProperty": "boolean", "IntProperty": "int", "FloatProperty": "float",
              "StringProperty": "string", "EnumProperty": "enum", "PointerProperty": "pointer",
              "CollectionProperty": "collection", "FloatVectorProperty": "float array",
              "IntVectorProperty": "int array", "BoolVectorProperty": "boolean array"}
FIELD_RE = re.compile(r"^:(arg|param|type|return|returns|rtype|raises|ivar|vartype)\s*([^:]*):\s*(.*)$")


# --------------------------------------------------------------------------
# Docstrings
# --------------------------------------------------------------------------

def parse_docstring(doc):
    """Split a docstring into prose and Sphinx fields.

    :arg doc: Docstring text (may be None).
    :type doc: str or None
    :return: ``(prose, fields)``; ``fields`` maps ``'args'``, ``'types'``,
       ``'ivars'`` to dicts and ``'return'``, ``'rtype'`` to strings and
       ``'raises'`` to a list of ``(exception, text)``.
    :rtype: tuple
    """
    fields = {"args": {}, "types": {}, "ivars": {}, "return": "", "rtype": "", "raises": []}
    if not doc:
        return "", fields
    prose, current = [], None
    for line in doc.splitlines():
        m = FIELD_RE.match(line.strip())
        if m:
            kind, name, text = m.group(1), m.group(2).strip(), m.group(3).strip()
            if kind in ("arg", "param"):
                fields["args"][name] = text
                current = ("args", name)
            elif kind == "type":
                fields["types"][name] = text
                current = ("types", name)
            elif kind in ("return", "returns"):
                fields["return"] = text
                current = ("return", None)
            elif kind == "rtype":
                fields["rtype"] = text
                current = ("rtype", None)
            elif kind == "raises":
                fields["raises"].append((name, text))
                current = ("raises", len(fields["raises"]) - 1)
            elif kind in ("ivar", "vartype"):
                fields["ivars"][name] = text
                current = ("ivars", name)
        elif current and line.startswith((" ", "\t")) and line.strip():
            kind, key = current
            extra = " " + line.strip()
            if kind in ("args", "types", "ivars"):
                fields[kind][key] += extra
            elif kind == "raises":
                exc, text = fields["raises"][key]
                fields["raises"][key] = (exc, text + extra)
            else:
                fields[kind] += extra
        else:
            current = None
            prose.append(line)
    return "\n".join(prose).strip(), fields


def rst_to_md(text):
    """Convert the few RST roles used in docstrings to Markdown."""
    text = re.sub(r":(?:class|func|meth|mod|attr|data|obj):`~?([^`]+)`", r"`\1`", text)
    text = re.sub(r"``([^`]+)``", r"`\1`", text)
    text = re.sub(r"::\s*$", ":", text, flags=re.M)
    return text


def cell(text):
    return rst_to_md(text).replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------
# AST helpers
# --------------------------------------------------------------------------

class SortedSet(frozenset):
    """A set literal rendered in sorted order, so generated pages are stable."""

    def __repr__(self):
        return "{" + ", ".join(repr(x) for x in sorted(self, key=str)) + "}"


def literal(node, constants):
    """Best-effort value of an AST node: literal, identity constant or source.

    :arg node: Expression node.
    :type node: ast.AST
    :arg constants: Module-level constants of the identity module.
    :type constants: dict
    :return: The evaluated value, or the expression's source text.
    """
    try:
        value = ast.literal_eval(node)
        return SortedSet(value) if isinstance(value, (set, frozenset)) else value
    except (ValueError, SyntaxError, TypeError):
        pass
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.attr in constants:
        return constants[node.attr]
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "op" \
            and node.args and "OP_NS" in constants:
        arg = literal(node.args[0], constants)
        return f"{constants['OP_NS']}.{arg}"
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            else:
                parts.append(str(literal(value.value, constants)))
        return "".join(parts)
    return ast.unparse(node)


def class_assigns(cls, constants):
    out = {}
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            out[stmt.targets[0].id] = literal(stmt.value, constants)
    return out


def class_properties(cls, constants):
    """Property annotations of a class: list of dicts (name, type, kwargs)."""
    props = []
    for stmt in cls.body:
        if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
                and isinstance(stmt.annotation, ast.Call)):
            continue
        func = stmt.annotation.func
        ptype = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if ptype not in PROP_TYPES:
            continue
        kwargs = {kw.arg: kw.value for kw in stmt.annotation.keywords if kw.arg}
        props.append({"attr": stmt.target.id, "ptype": ptype,
                      "kw": {k: literal(v, constants) for k, v in kwargs.items()}})
    return props


def base_names(cls):
    return [b.attr if isinstance(b, ast.Attribute) else getattr(b, "id", "") for b in cls.bases]


def signature(fn):
    """``name(args)`` without ``self`` / ``cls``, as in Blender's reference."""
    args = ast.unparse(fn.args)
    args = re.sub(r"^(self|cls)(, )?", "", args)
    return f"{fn.name}({args})"


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def prop_type_text(prop):
    kw = prop["kw"]
    text = PROP_TYPES[prop["ptype"]]
    if prop["ptype"] == "EnumProperty" and isinstance(kw.get("items"), list):
        ids = [item[0] for item in kw["items"] if isinstance(item, (tuple, list)) and item]
        text = f"enum in {ids}"
    elif prop["ptype"] == "PointerProperty":
        text = f"pointer to `{kw.get('type', '?')}`"
    rng = [f"{k} {kw[k]}" for k in ("min", "max") if k in kw]
    if rng:
        text += f" ({', '.join(rng)})"
    return text


def property_table(props):
    if not props:
        return "_No parameters._\n"
    lines = ["| Name | Type | Default | Description |", "|---|---|---|---|"]
    for p in props:
        kw = p["kw"]
        label = kw.get("name", "")
        desc = kw.get("description", "")
        text = f"**{label}**. {desc}" if label and desc else (label or desc)
        default = kw.get("default", "")
        lines.append(f"| `{p['attr']}` | {cell(prop_type_text(p))} | `{default!r}` | {cell(str(text))} |")
    return "\n".join(lines) + "\n"


def fields_md(fields, params=None):
    out = []
    names = list(params or []) + [n for n in fields["args"] if n not in (params or [])]
    rows = [(n, fields["types"].get(n, ""), fields["args"].get(n, "")) for n in names
            if n in fields["args"] or n in fields["types"]]
    if rows:
        out += ["| Parameter | Type | Description |", "|---|---|---|"]
        out += [f"| `{n}` | {cell(t)} | {cell(d)} |" for n, t, d in rows]
        out.append("")
    if fields["return"] or fields["rtype"]:
        rtype = f" ({cell(fields['rtype'])})" if fields["rtype"] else ""
        out.append(f"**Returns**{rtype}: {rst_to_md(fields['return'])}\n")
    for exc, text in fields["raises"]:
        out.append(f"**Raises** `{exc}`: {rst_to_md(text)}\n")
    if fields["ivars"]:
        out += ["| Attribute | Description |", "|---|---|"]
        out += [f"| `{n}` | {cell(d)} |" for n, d in fields["ivars"].items()]
        out.append("")
    return "\n".join(out)


def function_md(fn, level="###", prefix=""):
    prose, fields = parse_docstring(ast.get_docstring(fn))
    params = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs if a.arg not in ("self", "cls")]
    out = [f"{level} `{prefix}{signature(fn)}`\n"]
    if prose:
        out.append(rst_to_md(prose) + "\n")
    out.append(fields_md(fields, params))
    return "\n".join(out)


# --------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------

class Project:
    """All modules of one extension, parsed."""

    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.package = os.path.normpath(os.path.join(root, config.get("package", ".")))
        self.constants = self._identity_constants()
        self.modules = self._parse_modules()
        self.registrations = self._registrations()

    def _identity_constants(self):
        ident = self.config.get("identity")
        if not ident:
            return {}
        tree = ast.parse(open(os.path.join(self.package, ident), encoding="utf-8").read())
        consts = {}
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                try:
                    consts[stmt.targets[0].id] = ast.literal_eval(stmt.value)
                except ValueError:
                    pass
        return consts

    def _excluded(self, rel):
        return any(rel == e or rel.startswith(e.rstrip("/") + "/") for e in self.config.get("exclude", []))

    def _parse_modules(self):
        modules = {}
        for dirpath, dirnames, filenames in os.walk(self.package):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith((".", "__pycache__")))
            for fn in sorted(filenames):
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, self.package).replace(os.sep, "/")
                if self._excluded(rel):
                    continue
                modules[rel] = ast.parse(open(path, encoding="utf-8").read(), filename=rel)
        return modules

    def _registrations(self):
        """PropertyGroup class name -> 'bpy.types.X.attr' where it is registered."""
        regs = {}
        for tree in self.modules.values():
            for node in ast.walk(tree):
                target = value = None
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Attribute):
                    target, value = ast.unparse(node.targets[0]), node.value
                elif isinstance(node, ast.Call) and getattr(node.func, "id", "") == "setattr" and len(node.args) == 3:
                    target = f"{ast.unparse(node.args[0])}.{literal(node.args[1], self.constants)}"
                    value = node.args[2]
                if isinstance(value, ast.Call):
                    for kw in value.keywords:
                        if kw.arg == "type" and isinstance(kw.value, ast.Name):
                            regs[kw.value.id] = target
        return regs

    def module_name(self, rel):
        """Dotted module name of a file (the package root is the project name)."""
        if rel == "__init__.py":
            return self.config["name"]
        return rel[:-3].replace("/", ".").replace(".__init__", "")

    def iter_classes(self):
        for rel, tree in self.modules.items():
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    yield rel, node

    def kind(self, cls):
        bases = base_names(cls)
        assigns = class_assigns(cls, self.constants)
        if any(b.endswith("Operator") or b == "Operator" for b in bases) and "bl_idname" in assigns:
            return "operator"
        if any(b in ("PropertyGroup", "AddonPreferences") for b in bases):
            return "properties"
        if any(b == "Panel" for b in bases):
            return "panel"
        if any(b == "UIList" for b in bases):
            return "panel"
        return "class"


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

def operators_page(project):
    out = [f"# Operators\n",
           f"All operators of {project.config['name']}, as callable from Python. "
           "Generated from the source; do not edit by hand.\n"]
    by_module = {}
    for rel, cls in project.iter_classes():
        if project.kind(cls) == "operator":
            by_module.setdefault(rel, []).append(cls)
    for rel, classes in by_module.items():
        out.append(f"## `{project.module_name(rel)}`\n")
        for cls in classes:
            a = class_assigns(cls, project.constants)
            props = class_properties(cls, project.constants)
            if any(b in ("ExportHelper", "ImportHelper") for b in base_names(cls)):
                props = [{"attr": "filepath", "ptype": "StringProperty",
                          "kw": {"default": "", "description": "File path, chosen in the file browser "
                                 "(inherited from " + next(b for b in base_names(cls) if b.endswith("Helper"))
                                 + ")"}}] + props
            args = ", ".join(f"{p['attr']}={p['kw'].get('default', '...')!r}" for p in props)
            out.append(f"### `bpy.ops.{a['bl_idname']}({args})`\n")
            out.append(f"**{a.get('bl_label', '')}** — {rst_to_md(str(a.get('bl_description', '')))}\n")
            doc = ast.get_docstring(cls)
            if doc and doc.strip() != str(a.get('bl_description', '')).strip():
                out.append(rst_to_md(parse_docstring(doc)[0]) + "\n")
            meta = [f"class `{cls.name}`", f"`{rel}`"]
            if "bl_options" in a:
                meta.append(f"options `{a['bl_options']}`")
            methods = [f.name for f in cls.body if isinstance(f, ast.FunctionDef)]
            if "poll" in methods:
                poll = next(f for f in cls.body if isinstance(f, ast.FunctionDef) and f.name == "poll")
                pdoc = ast.get_docstring(poll)
                meta.append("poll: " + (pdoc.splitlines()[0] if pdoc else f"`{ast.unparse(poll.body[-1])}`"))
            out.append(" · ".join(meta) + "\n")
            out.append(property_table(props))
    return "\n".join(out)


def properties_page(project):
    out = ["# Properties and panels\n",
           "Data that the extension registers on Blender types, and its UI panels. "
           "Generated from the source; do not edit by hand.\n"]
    for rel, cls in project.iter_classes():
        if project.kind(cls) != "properties":
            continue
        where = project.registrations.get(cls.name)
        if "AddonPreferences" in base_names(cls):
            where = "context.preferences.addons[__package__].preferences"
        out.append(f"## `{cls.name}`\n")
        out.append(f"Registered at `{where or '(nested PropertyGroup)'}` · `{rel}`\n")
        prose, fields = parse_docstring(ast.get_docstring(cls))
        if prose:
            out.append(rst_to_md(prose) + "\n")
        out.append(property_table(class_properties(cls, project.constants)))
    panels = [(rel, cls) for rel, cls in project.iter_classes() if project.kind(cls) == "panel"]
    if panels:
        out += ["## Panels\n", "| Panel | Space / region | Category | Label | Module |", "|---|---|---|---|---|"]
        for rel, cls in panels:
            a = class_assigns(cls, project.constants)
            out.append(f"| `{a.get('bl_idname', cls.name)}` | {a.get('bl_space_type', '')} / "
                       f"{a.get('bl_region_type', '')} | {a.get('bl_category', '')} | {a.get('bl_label', '')} "
                       f"| `{rel}` |")
        out.append("")
    return "\n".join(out)


def module_page(project, rel, tree):
    name = project.module_name(rel)
    out = [f"# `{name}`\n", f"Source: `{rel}`\n"]
    doc = ast.get_docstring(tree)
    if doc:
        out.append(rst_to_md(doc) + "\n")
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
             and n.name not in ("register", "unregister")]
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)
               and project.kind(n) == "class" and not n.name.startswith("_")]
    consts = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
              and isinstance(n.targets[0], ast.Name) and n.targets[0].id.isupper()]
    if consts:
        out += ["## Constants\n", "| Name | Value |", "|---|---|"]
        for c in consts:
            value = ast.unparse(c.value)
            value = value if len(value) < 90 else value[:87] + "..."
            out.append(f"| `{c.targets[0].id}` | `{cell(value)}` |")
        out.append("")
    if funcs:
        out.append("## Functions\n")
        out += [function_md(f) for f in funcs]
    for cls in classes:
        bases = ", ".join(ast.unparse(b) for b in cls.bases)
        init = next((f for f in cls.body if isinstance(f, ast.FunctionDef) and f.name == "__init__"), None)
        sig = f"({ast.unparse(init.args)})".replace("(self, ", "(").replace("(self)", "()") if init else ""
        out.append(f"## class `{cls.name}{sig}`" + (f" — bases: `{bases}`" if bases else "") + "\n")
        prose, fields = parse_docstring(ast.get_docstring(cls))
        if prose:
            out.append(rst_to_md(prose) + "\n")
        out.append(fields_md(fields))
        for f in cls.body:
            if isinstance(f, ast.FunctionDef) and (not f.name.startswith("_")):
                out.append(function_md(f, level="###", prefix=f"{cls.name}."))
    others = [n.name for n in tree.body if isinstance(n, ast.ClassDef) and project.kind(n) != "class"]
    if others:
        out.append("## Blender classes\n")
        out.append("Operators, property groups and panels of this module are listed in "
                   "[operators](../operators.md) and [properties](../properties.md): "
                   + ", ".join(f"`{n}`" for n in others) + ".\n")
    return "\n".join(out)


def index_page(project, module_files):
    out = [f"# {project.config['name']} — API reference\n",
           "Generated by `tools/gen_api_docs.py` from the source code. "
           "Edit the docstrings, not these pages.\n",
           "* [Operators](operators.md) — `bpy.ops` entry points",
           "* [Properties and panels](properties.md) — data stored in the .blend, UI\n",
           "## Modules\n", "| Module | Summary |", "|---|---|"]
    for rel, fname in module_files:
        doc = ast.get_docstring(project.modules[rel]) or ""
        summary = doc.strip().splitlines()[0] if doc.strip() else ""
        out.append(f"| [`{project.module_name(rel)}`](modules/{fname}) | {cell(summary)} |")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------

def check(project):
    """List documentation problems: missing docstrings, undocumented
    parameters, operators or properties without a description.

    :arg project: Parsed project.
    :type project: :class:`Project`
    :return: Problems, one per line, ``path:line: message``.
    :rtype: list of str
    """
    problems = []

    def need_doc(rel, node, what):
        if not ast.get_docstring(node):
            problems.append(f"{rel}:{node.lineno}: {what} '{node.name}' has no docstring")
            return False
        return True

    def need_args(rel, fn, qual):
        _prose, fields = parse_docstring(ast.get_docstring(fn))
        for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
            if a.arg not in ("self", "cls") and a.arg not in fields["args"]:
                problems.append(f"{rel}:{fn.lineno}: '{qual}' does not document argument '{a.arg}'")

    for rel, tree in project.modules.items():
        if not ast.get_docstring(tree):
            problems.append(f"{rel}:1: module has no docstring")
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_") \
                    and node.name not in ("register", "unregister"):
                if need_doc(rel, node, "function"):
                    need_args(rel, node, node.name)
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                kind = project.kind(node)
                if kind == "operator":
                    a = class_assigns(node, project.constants)
                    if not a.get("bl_description") and not ast.get_docstring(node):
                        problems.append(f"{rel}:{node.lineno}: operator '{node.name}' has no bl_description")
                if kind in ("operator", "properties"):
                    for p in class_properties(node, project.constants):
                        if not p["kw"].get("description") and p["attr"] not in ("role",):
                            problems.append(f"{rel}:{node.lineno}: property '{node.name}.{p['attr']}' "
                                            "has no description")
                    if kind == "properties":
                        need_doc(rel, node, "property group")
                    continue
                if kind == "panel":
                    continue
                need_doc(rel, node, "class")
                for f in node.body:
                    if isinstance(f, ast.FunctionDef) and not f.name.startswith("_") \
                            and f.name not in STANDARD_METHODS:
                        if need_doc(rel, f, "method"):
                            need_args(rel, f, f"{node.name}.{f.name}")
    return problems


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def write(path, text, quarto_title=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if quarto_title is not None:
        text = f'---\ntitle: "{quarto_title}"\n---\n\n' + re.sub(r"^# .*\n", "", text, count=1)
        text = re.sub(r"\]\(([^)]+)\.md\)", r"](\1.qmd)", text)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--config", default="devdocs/apidoc.toml")
    parser.add_argument("--check", action="store_true", help="report undocumented API and exit 1 if any")
    args = parser.parse_args()

    with open(os.path.join(args.root, args.config), "rb") as fh:
        config = tomllib.load(fh)
    project = Project(args.root, config)

    if args.check:
        problems = check(project)
        print("\n".join(problems) if problems else "API documentation complete.")
        sys.exit(1 if problems else 0)

    pages = {"index.md": None, "operators.md": operators_page(project),
             "properties.md": properties_page(project)}
    module_files = []
    for rel, tree in project.modules.items():
        fname = project.module_name(rel).replace(".", "_") + ".md"
        module_files.append((rel, fname))
        pages[f"modules/{fname}"] = module_page(project, rel, tree)
    pages["index.md"] = index_page(project, module_files)

    # Hand-written pages also published on the Quarto site (single source).
    if config.get("quarto"):
        for source, dest in config.get("quarto_pages", {}).items():
            with open(os.path.join(args.root, source), encoding="utf-8") as fh:
                text = fh.read()
            title = text.splitlines()[0].lstrip("# ").replace("`", "")
            write(os.path.join(args.root, os.path.dirname(config["quarto"]), dest), text, quarto_title=title)

    for target, quarto in ((config["out"], False), (config.get("quarto"), True)):
        if not target:
            continue
        for name, text in pages.items():
            path = os.path.join(args.root, target, name)
            if quarto:
                path = path[:-3] + ".qmd"
                title = text.splitlines()[0].lstrip("# ").replace("`", "")
                write(path, text, quarto_title=title)
            else:
                write(path, text)
        print(f"Wrote {len(pages)} pages to {target}")


if __name__ == "__main__":
    main()
