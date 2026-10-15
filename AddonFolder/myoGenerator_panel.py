"""The MyoGeneratorRemix sidebar panel (View3D > Sidebar > MyoGeneratorRemix).

Drawing only. Sections in working order: units/scale status, muscle name,
attachments (origin and insertion), muscle creation (preview, type, path,
rings, settings, final mesh, next muscle), measurements (parameters, fibres,
CSV location, Check / Calculate & Export), the muscle list (QA and texture)
and the experimental tools. Showing/hiding objects by type is the separate
*Show in Scene* panel (:mod:`visibility`).
"""
import json

import bpy

from . import myo_record


def _format_quantity(value, unit):
    if value == 0:
        return f"0 {unit}"
    if abs(value) < 1.0:
        return f"{value:.4f} {unit}"
    if abs(value) < 1000.0:
        return f"{value:.2f} {unit}"
    return f"{value:,.0f} {unit}"


def _draw_findings(layout, findings, max_lines=None):
    for level, message in findings[:max_lines]:
        row = layout.row()
        row.alert = level == myo_record.QA_ERROR
        row.label(text=message, icon=myo_record.LEVEL_ICONS.get(level, 'INFO'))


def draw_units_box(layout, context):
    """Draw the scene scale (1 BU = ... mm), the result of the last scale check and
    the "Set" unit-scale menu.

    :arg layout: Layout to draw into.
    :type layout: :class:`bpy.types.UILayout`
    :arg context: Draw context.
    :type context: :class:`bpy.types.Context`
    """
    scene = context.scene
    props = scene.myogen
    box = layout.box()
    mpu = myo_record.metres_per_unit(scene)
    header = box.row()
    header.label(text=f"Units: 1 BU = {mpu * 1000:g} mm", icon='DRIVER_DISTANCE')
    header.operator_menu_enum("myogen.set_unit_scale", "unit", text="Set", icon='PREFERENCES')
    try:
        findings = json.loads(props.scene_qa or "[]")
    except ValueError:
        findings = []
    if findings:
        _draw_findings(box, [f for f in findings if f[0] != myo_record.QA_OK] or findings)
    else:
        box.label(text="Run 'Check Muscles' to verify the scale", icon='INFO')


#: Short labels of the QA findings: (regex on the full message, label template).
SHORT_FINDINGS = (
    (r"Overlaps '([^']+)'.*?\(([\d.]+)% of the smaller", "Overlap {0} {1}%"),
    (r"Overlap with other muscles not checked", "Overlap not checked"),
    (r"The belly touches only (\d+)% of the (\w+)", "{1} contact {0}%"),
    (r"Only (\d+)% of the belly fibres reach", "Fibres arriving {0}%"),
    (r"(\d+)% of the belly fibres detour", "Fibre detours {0}%"),
    (r"Longest belly fibre is ([\d.]+)x the path", "Longest fibre {0}× path"),
    (r"Belly fibres could not be traced", "Fibres not traced"),
    (r"Belly mesh is defective", "Defective mesh"),
    (r"Belly has minor defects", "Minor mesh defects"),
    (r"Belly mesh has holes.*?([\d.]+)%", "Holes: volume {0}%"),
    (r"Belly mesh has small holes", "Small holes"),
    (r"Belly normals point inwards", "Inverted normals"),
    (r"Volume is zero", "Zero volume"),
    (r"No belly mesh", "No final mesh"),
    (r"Origin or insertion surface missing", "Attachment missing"),
    (r"Path curve is missing", "No path"),
    (r"Path \(.*\) is shorter", "Path < straight line"),
    (r"Path is ([\d.]+)x the straight", "Path {0}× straight line"),
    (r"Fibre length is ([\d.]+)x the skull", "Fibre {0}× skull"),
    (r"Muscle size .* is ([\d.]+)x the skull", "Size {0}× skull"),
    (r"Left/right volumes .* differ ([\d.]+)x", "Left/right volume {0}×"),
)
#: Longest label made from an unknown message.
SHORT_FINDING_MAX = 32


def short_finding(message):
    """A few words for a QA finding (its full text is the tooltip).

    :arg message: Full finding text.
    :type message: str
    :rtype: str
    """
    import re
    for pattern, template in SHORT_FINDINGS:
        m = re.search(pattern, message)
        if m:
            return template.format(*(g.capitalize() if g.isalpha() else g for g in m.groups()))
    head = re.split(r"[:;(]", message, maxsplit=1)[0].strip()
    return head if len(head) <= SHORT_FINDING_MAX else head[:SHORT_FINDING_MAX - 1].rstrip() + "…"


class MYOGEN_OT_qa_finding(bpy.types.Operator):
    """One QA finding: hover for the full text, click to print it"""
    bl_idname = "myogen.qa_finding"
    bl_label = "QA Finding"
    bl_description = "QA finding"
    bl_options = {'INTERNAL'}

    message: bpy.props.StringProperty(name="Message", description="Full text of the finding")
    level: bpy.props.StringProperty(name="Level", description="Finding level (OK, INFO, WARNING, ERROR)")

    @classmethod
    def description(cls, context, properties):
        return properties.message

    def execute(self, context):
        self.report({'WARNING'} if self.level in (myo_record.QA_WARNING, myo_record.QA_ERROR) else {'INFO'},
                    self.message)
        return {'FINISHED'}


def _format_record(rec):
    parts = []
    if rec.get("myo_volume_m3"):
        parts.append(f"{rec['myo_volume_m3'] * 1e6:.3g} cm³")
    if rec["has_pcsa"]:
        parts.append(f"{rec['myo_pcsa_m2'] * 1e4:.3g} cm²")
    if rec.get("myo_force_n"):
        parts.append(f"{rec['myo_force_n']:.3g} N")
    return " · ".join(parts) or "no values"


def _draw_texture(layout, coll):
    """Texture of a finished belly (collapsible): arrangement, bundles, relief, tendons."""
    belly = myo_record.resolve_objects(coll).get("belly")
    if belly is None or belly.type != 'MESH':
        return
    from .fibre_texture import PENNATE
    body = _section(layout, f"myogen_tex_{coll.name}", "Texture")
    if body is None:
        return
    col = body.column(align=True)
    col.prop(belly, "myogen_fibres", text="Fibres")
    if belly.myogen_fibres in PENNATE:
        col.prop(belly, "myogen_pennation")
    row = col.row(align=True)
    row.prop(belly, "myogen_fibre_bundles", text="Bundles")
    row.prop(belly, "myogen_relief", text="Relief")
    row = col.row(align=True)
    row.prop(belly, "myogen_tendon_origin", text="Tendon O", slider=True)
    row.prop(belly, "myogen_tendon_insertion", text="I", slider=True)
    row.prop(belly, "myogen_tendon_fade", text="Fade", slider=True)


def _counts(findings):
    """``(errors, warnings, notes)`` of a list of findings."""
    levels = [lvl for lvl, _msg in findings]
    return (levels.count(myo_record.QA_ERROR), levels.count(myo_record.QA_WARNING),
            levels.count(myo_record.QA_INFO))


def _summary(measured, findings):
    if not measured:
        return "not measured"
    errors, warnings, _notes = _counts(findings)
    parts = ([f"{errors} error{'s' * (errors != 1)}"] if errors else []) + \
            ([f"{warnings} warning{'s' * (warnings != 1)}"] if warnings else [])
    return ", ".join(parts) or "OK"


def draw_qa_box(layout, context):
    """The muscle list: one collapsible row per muscle (status icon, name,
    number of errors and warnings); expanded: volume · PCSA · force, a short
    label per finding (full text on hover; errors, warnings, then notes) and
    the texture.

    :arg layout: Layout to draw into.
    :type layout: :class:`bpy.types.UILayout`
    :arg context: Draw context.
    :type context: :class:`bpy.types.Context`
    """
    collections = myo_record.iter_muscle_collections()
    if not collections:
        return
    box = layout.box()
    box.label(text="Muscles (results of the last Check)", icon='OUTLINER_COLLECTION')
    order = {myo_record.QA_ERROR: 0, myo_record.QA_WARNING: 1, myo_record.QA_INFO: 2}
    for coll in collections:
        rec = myo_record.read_record(coll)
        findings = [f for f in rec["qa"] if f[0] in order]
        measured = bool(rec.get("myo_updated"))
        level = myo_record.worst_level(rec["qa"]) if measured else None
        icon = myo_record.LEVEL_ICONS[level] if level is not None else 'QUESTION'
        if hasattr(box, "panel"):                                    # Blender 4.1+
            header, body = box.panel(f"myogen_muscle_{coll.name}", default_closed=True)
            row = header.row()
            row.alert = level == myo_record.QA_ERROR
            row.label(text=coll.name, icon=icon)
            row.label(text=_summary(measured, findings))
            sel = row.operator("myogen.select_muscle", text="", icon='RESTRICT_SELECT_OFF')
            sel.name = coll.name
        else:
            row = box.row()
            row.label(text=f"{coll.name}: {_summary(measured, findings)}", icon=icon)
            sel = row.operator("myogen.select_muscle", text="", icon='RESTRICT_SELECT_OFF')
            sel.name = coll.name
            body = box.column()
        if body is None:
            continue
        act_row = body.row(align=True)
        active_curr = getattr(context.scene.myogen, "active_muscle", "").strip() or context.scene.myogen.muscle_name.strip()
        is_active = (active_curr == coll.name)
        sel_op = act_row.operator("myogen.select_muscle",
                                  text="Active" if is_active else "Select / Edit",
                                  icon='CHECKMARK' if is_active else 'RESTRICT_SELECT_OFF')
        sel_op.name = coll.name
        ren_op = act_row.operator("myogen.rename_muscle", text="Rename", icon='GREASEPENCIL')
        ren_op.muscle = coll.name
        del_op = act_row.operator("myogen.delete_muscle", text="", icon='TRASH')
        del_op.muscle = coll.name
        if measured:
            body.label(text=_format_record(rec), icon='BLANK1')
        if findings:
            grid = body.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
            for lvl, msg in sorted(findings, key=lambda f: order[f[0]]):
                cell = grid.row(align=True)
                cell.alert = lvl == myo_record.QA_ERROR
                op = cell.operator("myogen.qa_finding", text=short_finding(msg),
                                   icon=myo_record.LEVEL_ICONS.get(lvl, 'INFO'), emboss=False)
                op.message, op.level = msg, lvl
        _draw_texture(body, coll)


def _hint(layout, text, icon='INFO'):
    row = layout.row()
    row.scale_y = 0.75
    row.label(text=text, icon=icon)


def _section(layout, idname, title, default_closed=True):
    """Collapsible sub-section (Blender 4.1+), or a plain column."""
    if hasattr(layout, "panel"):
        header, body = layout.panel(idname, default_closed=default_closed)
        header.label(text=title)
        return body
    layout.label(text=title)
    return layout.column()


def _draw_path_and_rings(col, context, props):
    col.label(text="Path")
    row = col.row(align=True)
    row.operator("myogen.edit_path", icon='EDITMODE_HLT')
    row.operator("myogen.reset_path", text="", icon='FILE_REFRESH')
    col.prop(props, "use_controls")
    if not props.use_controls:
        return
    row = col.row(align=True)
    row.operator("myogen.select_rings", icon='MESH_CIRCLE')
    row.operator("myogen.reset_rings", text="", icon='FILE_REFRESH')
    col.prop(props, "ring_count")
    _hint(col, "G slides a ring along the path, S sizes it, R turns it")
    if props.muscle_shape == 'FAN':
        _hint(col, "Fan: ring X = width of the fan, Y = thickness")


def draw_muscle_creation(layout, context):
    """Preview first, then the muscle type, the controls and the settings, then the final mesh.

    The preview is the belly as it will be generated (draft resolution); its
    ring controls deform it in real time.

    :arg layout: Layout to draw into.
    :type layout: :class:`bpy.types.UILayout`
    :arg context: Draw context.
    :type context: :class:`bpy.types.Context`
    """
    props = context.scene.myogen
    box = layout.box()
    box.label(text="Muscle Creation", icon='CURVE_BEZCURVE')

    row = box.row(align=True)
    row.scale_y = 1.3
    if props.preview_live:
        row.label(text="Live preview: edit the path, rings or settings", icon='REC')
        row.operator("myogen.muscle_preview_discard", text="", icon='X')
    else:
        row.operator("myogen.muscle_preview_update", text="Start Preview", icon='PLAY')
    if props.preview_status:
        _hint(box, props.preview_status, icon='ERROR' if "fail" in props.preview_status
              or "pieces" in props.preview_status else 'INFO')

    col = box.column()
    col.prop(props, "muscle_shape", text="Type")
    _draw_path_and_rings(col, context, props)
    more = _section(col, "myogen_more", "More settings")
    if more is not None:
        more.prop(props, "attachment_thickness_mm")
        more.prop(props, "surface_smoothing_mm")
        more.prop(props, "voxel_size_mm")
        more.prop(props, "bone_clearance_mm")

    row = box.row()
    row.scale_y = 1.2
    row.operator("myogen.muscle_mesh_generation", text="Generate Final Mesh", icon='MESH_CUBE')
    box.operator("myogen.next_muscle", text="Next Muscle", icon='FORWARD')


class MYOGENERATOR_PT_panel(bpy.types.Panel):
    bl_idname = "MYOGENERATOR_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "MyoGeneratorRemix"
    bl_category = "MyoGeneratorRemix"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.myogen

        draw_units_box(layout, context)

        box = layout.box()
        box.label(text="Muscle", icon='GREASEPENCIL')
        existing_muscles = list(myo_record.iter_all_myo_collections())
        active_name = getattr(props, "active_muscle", "").strip()
        active_coll = bpy.data.collections.get(active_name) if active_name else None
        if active_coll is None or not myo_record.is_muscle_collection(active_coll):
            cand = bpy.data.collections.get(props.muscle_name.strip())
            if cand is not None and myo_record.is_muscle_collection(cand):
                active_coll = cand
                active_name = cand.name

        if existing_muscles:
            row_sel = box.row(align=True)
            sel_text = active_name if (active_name and bpy.data.collections.get(active_name)) else "Select Existing Muscle"
            row_sel.operator_menu_enum("myogen.select_muscle_menu", "muscle", text=sel_text, icon='OUTLINER_COLLECTION')
            row_sel.operator("myogen.next_muscle", text="New", icon='ADD')

        row = box.row(align=True)
        row.prop(props, "muscle_name", text="")
        if active_coll is not None:
            is_renamed = (props.muscle_name.strip() != active_name) and (props.muscle_name.strip() not in ("", "Insert muscle name"))
            ren_op = row.operator("myogen.rename_muscle", text="Rename", icon='GREASEPENCIL')
            ren_op.muscle = active_name
            if is_renamed:
                ren_op.new_name = props.muscle_name.strip()
            del_op = row.operator("myogen.delete_muscle", text="", icon='TRASH')
            del_op.muscle = active_name
        else:
            sub = row.row(align=True)
            sub.enabled = props.muscle_name.strip() not in ("", "Insert muscle name")
            sub.operator('myogen.submit_muscle', text="Submit")

        box = layout.box()
        box.label(text="Attachments", icon='CONSTRAINT_BONE')
        active_att_name = active_name or props.muscle_name.strip()
        active_att_coll = bpy.data.collections.get(active_att_name)
        objs = myo_record.resolve_objects(active_att_coll) if active_att_coll else {}

        for role, label, bone, start, submit in (
            ("origin", "Origin", "origin_object", "myogen.select_origin", "myogen.submit_origin"),
            ("insertion", "Insertion", "insertion_object", "myogen.select_insertion", "myogen.submit_insertion")
        ):
            col = box.column(align=True)
            col.prop(props, bone, text=f"{label} bone")
            row = col.row(align=True)
            row.enabled = getattr(props, bone) is not None
            has_att = bool(objs.get(role))
            if has_att:
                rec_op = row.operator("myogen.recall_attachment", text=f"Edit {label}", icon='EDITMODE_HLT')
                rec_op.role = role
                row.operator(submit, text="Update", icon='FILE_REFRESH')
                row.operator(start, text="", icon='BRUSH_DATA')
            else:
                row.operator(start, text=f"Paint {label}", icon='BRUSH_DATA')
                row.operator(submit, text="Submit")

        draw_muscle_creation(layout, context)

        box = layout.box()
        box.label(text="Measurements", icon='FORCE_FORCE')
        col = box.column(align=True)
        col.prop(props, "specific_tension")
        col.prop(props, "density_g_cm3")
        col.prop(props, "fiber_length_ratio")
        col.prop(props, "pennation_deg")
        col = box.column(align=True)
        col.prop(props, "fiber_length_source")
        fibres = props.fiber_length_source == 'BELLY_FIBRES'
        if fibres:
            col.prop(props, "pcsa_model")
            col.prop(props, "fibre_seeding")
            col.prop(props, "belly_fibre_count")
            row = box.row()
            row.scale_y = 1.2
            row.operator("myogen.trace_fibres", icon='STRANDS')
        info = box.column(align=True)
        info.scale_y = 0.75
        if not fibres:
            info.label(text="PCSA = V·cos(pennation) / (path length × ratio).", icon='INFO')
            info.label(text="Ratio 1 and 0° reproduce Herbst et al. (2022).", icon='BLANK1')
        else:
            if props.pcsa_model == 'WEIGHTED':
                info.label(text="PCSA = cos(pennation) · Σ Vᵢ / (Lᵢ × ratio).", icon='INFO')
            else:
                info.label(text="PCSA = V·cos(pennation) / (mean fibre × ratio).", icon='INFO')
            info.label(text="Check / Calculate also update the fibres (Show in Scene > Fibres).", icon='BLANK1')
        col = box.column(align=True)
        col.prop(props, "conf_path", text="CSV folder")
        col.prop(props, "file_name", text="CSV name")
        row = box.row(align=True)
        row.operator("myogen.check_muscles", text="Check Muscles", icon='VIEWZOOM')
        sub = row.row(align=True)
        sub.enabled = bool(props.conf_path and props.file_name)
        sub.operator("myogen.calculate_muscle_parameters", text="Calculate & Export CSV", icon='EXPORT')

        draw_qa_box(layout, context)

        addon = context.preferences.addons.get(__package__)
        if not (addon and addon.preferences.show_advanced):
            return

        adv_box = layout.box()
        adv_box.label(text="Advanced (experimental)")
        adv_box.label(text=f"Selected Total Volume: "
                           f"{_format_quantity(props.advanced_selected_volume * 1e6, 'cm³')}")
        adv_box.label(text=f"Estimated Total Mass: {_format_quantity(props.advanced_selected_mass * 1e3, 'g')}")
        adv_box.label(text=props.advanced_selected_pcsa or "Total PCSA: NA")
        adv_box.operator("myogen.estimate_selected_volumes", text="Estimate Selected Volumes")

        row = adv_box.row(align=True)
        row.prop(props, "mirror_axis", expand=True)
        op = row.operator("myogen.mirror_duplicate", text="Mirror Duplicate")
        op.axis = props.mirror_axis
