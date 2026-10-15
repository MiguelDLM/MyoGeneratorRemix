"""Show and hide MyoGen objects by type, for every muscle of the scene.

Types (:data:`KINDS`): origin areas, insertion areas (each with its contour),
bellies, paths and fibres (``<M>_fibres`` and ``<M>_fibre_detours``, written by
*Check Muscles* / *Calculate* with *Fibre length from: Belly fibres*). The
construction helpers of the muscle being built (preview, rings) are not
types: they exist for one muscle at a time and are removed by *Generate
Final Mesh*. **Toggle** shows or hides one type in every muscle, **Only** shows one
type and hides the others, **Show All** shows everything. Fine control of single
muscles is left to Blender's outliner.
"""

import bpy

from . import myo_record
from .belly_fibres import DETOURS_SUFFIX

#: Object types: key -> (label, icon).
KINDS = {
    'ORIGIN': ("Origins", 'TRIA_UP'),
    'INSERTION': ("Insertions", 'TRIA_DOWN'),
    'BELLY': ("Bellies", 'MESH_CUBE'),
    'PATH': ("Paths", 'CURVE_BEZCURVE'),
    'FIBRES': ("Fibres", 'STRANDS'),
}

_ROLE_KIND = {
    "origin": 'ORIGIN', "origin_contour": 'ORIGIN',
    "insertion": 'INSERTION', "insertion_contour": 'INSERTION',
    "belly": 'BELLY', "path": 'PATH', "fibres": 'FIBRES',
}


def kind_of(obj, muscle_name, roles):
    """Type of an object of a muscle collection, or None for other objects.

    :arg obj: Object of the muscle collection.
    :type obj: :class:`bpy.types.Object`
    :arg muscle_name: Muscle (collection) name.
    :type muscle_name: str
    :arg roles: Object -> role, from :func:`myo_record.resolve_objects`.
    :type roles: dict
    :rtype: str or None
    """
    if obj in roles:
        return _ROLE_KIND.get(roles[obj])
    if obj.name == muscle_name + DETOURS_SUFFIX:
        return 'FIBRES'
    return None


def objects_by_kind():
    """Every MyoGen object of the scene, grouped by type.

    :return: Kind (see :data:`KINDS`) -> list of objects (every kind present).
    :rtype: dict
    """
    out = {k: [] for k in KINDS}
    for coll in myo_record.iter_muscle_collections():
        roles = {obj: role for role, obj in myo_record.resolve_objects(coll).items()}
        for obj in coll.objects:
            kind = kind_of(obj, coll.name, roles)
            if kind is not None:
                out[kind].append(obj)
    return out


def is_visible(obj):
    """True if the object is shown in the viewport (neither hidden nor disabled).

    :arg obj: Any object.
    :type obj: :class:`bpy.types.Object`
    :rtype: bool
    """
    if obj.hide_viewport:
        return False
    try:
        return not obj.hide_get()
    except RuntimeError:                                        # not in the view layer
        return False


def set_visible(objs, visible):
    """Show or hide objects in the viewport.

    :arg objs: Objects.
    :type objs: iterable of :class:`bpy.types.Object`
    :arg visible: True to show.
    :type visible: bool
    """
    for obj in objs:
        obj.hide_viewport = not visible
        try:
            obj.hide_set(not visible)
        except RuntimeError:
            pass
        if visible:
            for coll in obj.users_collection:
                coll.hide_viewport = False


def kind_items(self, context):
    """Enum items of :data:`KINDS` (for operator properties).

    :arg self: The operator.
    :type self: :class:`bpy.types.Operator`
    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :rtype: list of tuple
    """
    return [(k, label, f"MyoGen {label.lower()} of every muscle", icon, i)
            for i, (k, (label, icon)) in enumerate(KINDS.items())]


class MYOGEN_OT_toggle_kind(bpy.types.Operator):
    """Show or hide one type of object in every muscle"""
    bl_idname = "myogen.toggle_kind"
    bl_label = "Toggle Type"
    bl_description = "Show or hide this type of object in every muscle (hide if any is visible)"
    bl_options = {'REGISTER', 'UNDO'}

    kind: bpy.props.EnumProperty(name="Type", items=kind_items, description="Type of object")

    def execute(self, context):
        objs = objects_by_kind()[self.kind]
        if not objs:
            self.report({'INFO'}, f"No {KINDS[self.kind][0].lower()} in the scene")
            return {'CANCELLED'}
        set_visible(objs, not any(is_visible(o) for o in objs))
        return {'FINISHED'}


class MYOGEN_OT_solo_kind(bpy.types.Operator):
    """Show only one type of object in every muscle"""
    bl_idname = "myogen.solo_kind"
    bl_label = "Show Only Type"
    bl_description = "Show this type of object in every muscle and hide every other MyoGen object"
    bl_options = {'REGISTER', 'UNDO'}

    kind: bpy.props.EnumProperty(name="Type", items=kind_items, description="Type of object")

    def execute(self, context):
        for kind, objs in objects_by_kind().items():
            set_visible(objs, kind == self.kind)
        return {'FINISHED'}


class MYOGEN_OT_show_all_kinds(bpy.types.Operator):
    """Show every MyoGen object"""
    bl_idname = "myogen.show_all_kinds"
    bl_label = "Show All"
    bl_description = "Show every MyoGen object of every muscle (also the fibres, hidden when written)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for objs in objects_by_kind().values():
            set_visible(objs, True)
        return {'FINISHED'}


def draw_visibility(layout):
    """Draw the visibility buttons: per type a toggle (pressed = visible) and *Only*.

    :arg layout: Panel layout.
    :type layout: :class:`bpy.types.UILayout`
    """
    groups = objects_by_kind()
    layout.operator("myogen.show_all_kinds", icon='HIDE_OFF')
    grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
    for kind, (label, icon) in KINDS.items():
        objs = groups[kind]
        row = grid.row(align=True)
        row.enabled = bool(objs)
        op = row.operator("myogen.toggle_kind", text=label, icon=icon,
                          depress=any(is_visible(o) for o in objs))
        op.kind = kind
        row.operator("myogen.solo_kind", text="", icon='VIEWZOOM').kind = kind


class MYOGENERATOR_PT_visibility(bpy.types.Panel):
    """Show and hide MyoGen objects by type, for every muscle"""
    bl_idname = "MYOGENERATOR_PT_visibility"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Show in Scene"
    bl_category = "MyoGeneratorRemix"

    def draw(self, context):
        draw_visibility(self.layout)


classes = (MYOGEN_OT_toggle_kind, MYOGEN_OT_solo_kind, MYOGEN_OT_show_all_kinds, MYOGENERATOR_PT_visibility)
