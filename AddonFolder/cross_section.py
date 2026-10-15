"""Non-destructive cross-section slicing for visual inspection of internal anatomy.

Allows cutting through muscle bellies, bones and other scene meshes using a
transformable wireframe cutter cube in the 3D viewport. The underlying geometry
is never modified; disabling the cut restores all original meshes immediately.
"""

import math
import bmesh
import bpy
import mathutils

CUTTER_NAME = "MyoGen_Cutter"
MODIFIER_NAME = "MyoGen_CrossSection"


def best_solver(obj, preferred='AUTO'):
    """Determine the most appropriate Boolean solver for a target object.

    :arg obj: The target mesh object.
    :type obj: :class:`bpy.types.Object`
    :arg preferred: Preferred solver ('AUTO' or 'EXACT').
    :type preferred: str
    :return: Solver identifier supported by Blender ('MANIFOLD', 'FLOAT', 'FAST', or 'EXACT').
    :rtype: str
    """
    if preferred == 'EXACT':
        return 'EXACT'

    mod = obj.modifiers.get(MODIFIER_NAME)
    temp = False
    if not mod:
        try:
            mod = obj.modifiers.new(name="_temp_check", type='BOOLEAN')
            temp = True
        except RuntimeError:
            return 'EXACT'

    available = [item.identifier for item in mod.bl_rna.properties['solver'].enum_items]
    if temp:
        obj.modifiers.remove(mod)

    for cand in ('MANIFOLD', 'FLOAT', 'FAST'):
        if cand in available:
            return cand
    return 'EXACT'


def find_cutter(context=None):
    """Find the existing cross-section cutter object in the scene.

    :arg context: Blender context.
    :type context: :class:`bpy.types.Context` or None
    :return: The cutter object, or None if not present.
    :rtype: :class:`bpy.types.Object` or None
    """
    return bpy.data.objects.get(CUTTER_NAME)


def ensure_cutter(context):
    """Ensure the cross-section cutter cube exists, is linked and styled.

    :arg context: Blender context.
    :type context: :class:`bpy.types.Context`
    :return: The cutter object.
    :rtype: :class:`bpy.types.Object`
    """
    cutter = bpy.data.objects.get(CUTTER_NAME)
    if cutter is None:
        mesh = bpy.data.meshes.new(CUTTER_NAME)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bm.to_mesh(mesh)
        bm.free()
        cutter = bpy.data.objects.new(CUTTER_NAME, mesh)
        context.scene.collection.objects.link(cutter)

    cutter.display_type = 'WIRE'
    cutter.show_in_front = True
    cutter.hide_render = True
    cutter.color = (0.2, 0.7, 1.0, 1.0)
    cutter["myo_role"] = "cutter"

    cutter.hide_viewport = False
    try:
        cutter.hide_set(False)
    except RuntimeError:
        pass

    return cutter


def get_target_objects(context, scope='SCENE'):
    """Retrieve all mesh objects that should participate in the cross-section cut.

    :arg context: Blender context.
    :type context: :class:`bpy.types.Context`
    :arg scope: Target scope ('SCENE', 'MUSCLES_BONES', 'MUSCLES', or 'ACTIVE').
    :type scope: str
    :return: List of target mesh objects.
    :rtype: list of :class:`bpy.types.Object`
    """
    cutter = find_cutter(context)
    props = context.scene.myogen
    targets = []

    active_name = getattr(props, "active_muscle", "").strip() or props.muscle_name.strip()
    active_coll = bpy.data.collections.get(active_name) if active_name else None

    origin_bone = getattr(props, "origin_object", None)
    insertion_bone = getattr(props, "insertion_object", None)

    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj == cutter:
            continue
        if obj.name.endswith("_tube") or obj.name.startswith("_temp_"):
            continue

        if scope == 'SCENE':
            targets.append(obj)
        elif scope == 'MUSCLES':
            if obj.name.endswith("_muscle") or obj.get("myo_role") == "belly":
                targets.append(obj)
        elif scope == 'MUSCLES_BONES':
            is_muscle = obj.name.endswith("_muscle") or obj.get("myo_role") == "belly"
            is_bone = (obj in (origin_bone, insertion_bone) or
                       obj.get("myo_role") in ("origin_bone", "insertion_bone") or
                       "Cranium" in obj.name or "Mandible" in obj.name or "bone" in obj.name.lower())
            if is_muscle or is_bone:
                targets.append(obj)
        elif scope == 'ACTIVE':
            if active_coll and obj.name in active_coll.objects:
                if obj.name.endswith("_muscle") or obj.get("myo_role") == "belly":
                    targets.append(obj)
            elif obj in (origin_bone, insertion_bone):
                targets.append(obj)

    return targets


def compute_bounds(objects):
    """Compute the combined axis-aligned world bounding box for a set of objects.

    :arg objects: Sequence of Blender objects.
    :type objects: sequence of :class:`bpy.types.Object`
    :return: Tuple of ``(center, dimensions, min_corner, max_corner)``.
    :rtype: tuple
    """
    if not objects:
        zero = mathutils.Vector((0.0, 0.0, 0.0))
        one = mathutils.Vector((1.0, 1.0, 1.0))
        return zero, one, -one, one

    # Temporarily disable cross-section modifier to measure un-cut geometry
    disabled_mods = []
    for obj in objects:
        mod = obj.modifiers.get(MODIFIER_NAME)
        if mod and mod.show_viewport:
            mod.show_viewport = False
            disabled_mods.append(mod)

    if disabled_mods:
        try:
            bpy.context.view_layer.update()
        except Exception:
            pass

    min_co = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_co = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))

    valid = False
    for obj in objects:
        if not hasattr(obj, "bound_box") or not obj.bound_box:
            continue
        valid = True
        for corner in obj.bound_box:
            wc = obj.matrix_world @ mathutils.Vector(corner)
            min_co.x = min(min_co.x, wc.x)
            min_co.y = min(min_co.y, wc.y)
            min_co.z = min(min_co.z, wc.z)
            max_co.x = max(max_co.x, wc.x)
            max_co.y = max(max_co.y, wc.y)
            max_co.z = max(max_co.z, wc.z)

    for mod in disabled_mods:
        mod.show_viewport = True

    if not valid:
        zero = mathutils.Vector((0.0, 0.0, 0.0))
        one = mathutils.Vector((1.0, 1.0, 1.0))
        return zero, one, -one, one

    center = (min_co + max_co) / 2.0
    dims = max_co - min_co
    for i in range(3):
        if dims[i] < 1e-4:
            dims[i] = 1.0

    return center, dims, min_co, max_co


def fit_cutter(context, alignment='TRANSVERSE', scope='SCENE'):
    """Position and scale the cutter cube according to an anatomical plane or target.

    :arg context: Blender context.
    :type context: :class:`bpy.types.Context`
    :arg alignment: Plane alignment ('TRANSVERSE', 'SAGITTAL', 'CORONAL', 'ACTIVE', or 'FIT_ALL').
    :type alignment: str
    :arg scope: Target scope to measure bounds from if not 'ACTIVE'.
    :type scope: str
    """
    cutter = ensure_cutter(context)
    if alignment == 'ACTIVE':
        targets = get_target_objects(context, scope='ACTIVE')
        if not targets:
            targets = get_target_objects(context, scope=scope)
    else:
        targets = get_target_objects(context, scope=scope)

    center, dims, _min_co, _max_co = compute_bounds(targets)
    pad = 1.3

    cutter.rotation_euler = (0.0, 0.0, 0.0)

    if alignment == 'TRANSVERSE':
        cutter.scale = mathutils.Vector((dims.x * pad, dims.y * pad, dims.z * pad))
        cutter.location = mathutils.Vector((center.x, center.y, center.z + (dims.z * pad) / 2.0))
    elif alignment == 'SAGITTAL':
        cutter.scale = mathutils.Vector((dims.x * pad, dims.y * pad, dims.z * pad))
        cutter.location = mathutils.Vector((center.x + (dims.x * pad) / 2.0, center.y, center.z))
    elif alignment == 'CORONAL':
        cutter.scale = mathutils.Vector((dims.x * pad, dims.y * pad, dims.z * pad))
        cutter.location = mathutils.Vector((center.x, center.y + (dims.y * pad) / 2.0, center.z))
    else:
        cutter.scale = mathutils.Vector((dims.x * pad, dims.y * pad, dims.z * pad))
        cutter.location = mathutils.Vector((center.x, center.y, center.z))


def flip_cutter(context):
    """Invert the cutting side of the cutter cube relative to scene bounds.

    :arg context: Blender context.
    :type context: :class:`bpy.types.Context`
    """
    cutter = find_cutter(context)
    if not cutter:
        return
    props = context.scene.myogen
    targets = get_target_objects(context, scope=props.section_cut_scope)
    center, _dims, _min_co, _max_co = compute_bounds(targets)

    offset = cutter.location - center
    cutter.location = center - offset


def apply_cut(context):
    """Apply or update the non-destructive Boolean modifier on all target meshes.

    :arg context: Blender context.
    :type context: :class:`bpy.types.Context`
    :return: Number of objects affected.
    :rtype: int
    """
    props = context.scene.myogen
    cutter = ensure_cutter(context)
    targets = get_target_objects(context, scope=props.section_cut_scope)

    if cutter.scale == mathutils.Vector((1.0, 1.0, 1.0)) and cutter.location == mathutils.Vector((0.0, 0.0, 0.0)):
        fit_cutter(context, alignment='TRANSVERSE', scope=props.section_cut_scope)

    target_set = set(targets)
    count = 0

    for obj in targets:
        mod = obj.modifiers.get(MODIFIER_NAME)
        if not mod:
            mod = obj.modifiers.new(name=MODIFIER_NAME, type='BOOLEAN')
        mod.object = cutter
        mod.operation = props.section_cut_mode
        mod.solver = best_solver(obj, props.section_cut_solver)
        mod.show_viewport = True
        mod.show_render = True
        count += 1

    for obj in bpy.data.objects:
        if obj not in target_set and MODIFIER_NAME in obj.modifiers:
            obj.modifiers.remove(obj.modifiers[MODIFIER_NAME])

    try:
        from .modes import to_object_mode
        to_object_mode(context)
        for o in context.view_layer.objects:
            o.select_set(False)
        cutter.select_set(True)
        context.view_layer.objects.active = cutter
    except Exception:
        pass

    return count


def remove_cut(context):
    """Remove the cross-section Boolean modifier from all scene meshes and hide cutter.

    :arg context: Blender context.
    :type context: :class:`bpy.types.Context`
    :return: Number of modifiers removed.
    :rtype: int
    """
    removed = 0
    for obj in bpy.data.objects:
        mod = obj.modifiers.get(MODIFIER_NAME)
        if mod:
            obj.modifiers.remove(mod)
            removed += 1

    cutter = find_cutter(context)
    if cutter:
        cutter.hide_viewport = True
        try:
            cutter.hide_set(True)
        except RuntimeError:
            pass

    return removed


def on_cut_toggled(self, context):
    """Property update callback when ``section_cut_active`` is toggled.

    :arg self: Property group.
    :type self: :class:`bpy.types.PropertyGroup`
    :arg context: Blender context.
    :type context: :class:`bpy.types.Context`
    """
    if self.section_cut_active:
        apply_cut(context)
    else:
        remove_cut(context)


def on_cut_changed(self, context):
    """Property update callback when cutting parameters change.

    :arg self: Property group.
    :type self: :class:`bpy.types.PropertyGroup`
    :arg context: Blender context.
    :type context: :class:`bpy.types.Context`
    """
    if self.section_cut_active:
        apply_cut(context)


# --------------------------------------------------------------------------
# Operators
# --------------------------------------------------------------------------

class MYOGEN_OT_toggle_section_cut(bpy.types.Operator):
    """Enable or disable the non-destructive cross-section cut"""
    bl_idname = "myogen.toggle_section_cut"
    bl_label = "Toggle Cross-Section Cut"
    bl_description = "Enable or disable non-destructive cross-section clipping for visual inspection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.myogen
        props.section_cut_active = not props.section_cut_active
        action = "Enabled" if props.section_cut_active else "Disabled"
        self.report({'INFO'}, f"{action} cross-section cut")
        return {'FINISHED'}


class MYOGEN_OT_align_section_cut(bpy.types.Operator):
    """Align the cutter cube to an anatomical plane or fit to selection"""
    bl_idname = "myogen.align_section_cut"
    bl_label = "Align Section Cut"
    bl_description = "Align the cross-section plane to an anatomical orientation (transverse, sagittal, coronal) or fit"
    bl_options = {'REGISTER', 'UNDO'}

    plane: bpy.props.EnumProperty(
        name="Plane",
        items=[
            ('TRANSVERSE', "Transverse (XY / Z)", "Cut horizontally along the Z axis"),
            ('SAGITTAL', "Sagittal (YZ / X)", "Cut vertically along the X axis"),
            ('CORONAL', "Coronal (XZ / Y)", "Cut vertically along the Y axis"),
            ('ACTIVE', "Active Muscle", "Center and fit to the active muscle"),
            ('FIT_ALL', "Fit All", "Fit around all target objects"),
        ],
        default='TRANSVERSE',
        description="Anatomical plane to align the cutting box to",
    )

    def execute(self, context):
        props = context.scene.myogen
        if not props.section_cut_active:
            props.section_cut_active = True
        fit_cutter(context, alignment=self.plane, scope=props.section_cut_scope)
        apply_cut(context)
        self.report({'INFO'}, f"Aligned cut to {self.plane.lower()}")
        return {'FINISHED'}


class MYOGEN_OT_flip_section_cut(bpy.types.Operator):
    """Invert the side of the cut"""
    bl_idname = "myogen.flip_section_cut"
    bl_label = "Flip Cut Side"
    bl_description = "Invert the cutting side to view the opposite half of the anatomy"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.myogen
        if not props.section_cut_active:
            props.section_cut_active = True
        flip_cutter(context)
        apply_cut(context)
        self.report({'INFO'}, "Flipped cross-section cut side")
        return {'FINISHED'}


class MYOGEN_OT_refresh_section_cut(bpy.types.Operator):
    """Refresh cross-section cut on all current targets"""
    bl_idname = "myogen.refresh_section_cut"
    bl_label = "Refresh Cut Targets"
    bl_description = "Re-evaluate and update the cross-section cut on all current scene meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.myogen
        if not props.section_cut_active:
            props.section_cut_active = True
        count = apply_cut(context)
        self.report({'INFO'}, f"Updated cross-section cut across {count} objects")
        return {'FINISHED'}


class MYOGEN_OT_select_cutter(bpy.types.Operator):
    """Select the cross-section cutter cube in the 3D viewport"""
    bl_idname = "myogen.select_cutter"
    bl_label = "Select Cutter Cube"
    bl_description = "Select and activate the wireframe cutter cube to move, rotate or scale it in the 3D viewport"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        cutter = find_cutter(context)
        if not cutter:
            cutter = ensure_cutter(context)
        from .modes import to_object_mode
        to_object_mode(context)
        for o in context.view_layer.objects:
            o.select_set(False)
        cutter.hide_viewport = False
        try:
            cutter.hide_set(False)
        except RuntimeError:
            pass
        cutter.select_set(True)
        context.view_layer.objects.active = cutter
        self.report({'INFO'}, "Selected cutter cube. Use G/R/S to transform.")
        return {'FINISHED'}


# --------------------------------------------------------------------------
# UI Panel
# --------------------------------------------------------------------------

class MYOGENERATOR_PT_cross_section(bpy.types.Panel):
    """Panel for cross-section visual inspection of muscles and bones"""
    bl_idname = "MYOGENERATOR_PT_cross_section"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Cross-Section Cut"
    bl_category = "MyoGeneratorRemix"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.myogen
        active = props.section_cut_active

        row = layout.row()
        row.scale_y = 1.3
        row.operator(
            "myogen.toggle_section_cut",
            text="Deactivate Cut" if active else "Enable Cross-Section Cut",
            icon='CHECKMARK' if active else 'MOD_BOOLEAN',
            depress=active,
        )

        if not active:
            hint = layout.column(align=True)
            hint.scale_y = 0.75
            hint.label(text="Non-destructive slicing tool for visual inspection.", icon='INFO')
            hint.label(text="Cuts muscles and bones without altering meshes.", icon='BLANK1')
            return

        row = layout.row(align=True)
        row.operator("myogen.select_cutter", text="Select Cutter Cube", icon='RESTRICT_SELECT_OFF')
        row.operator("myogen.flip_section_cut", text="Flip Side", icon='ARROW_LEFTRIGHT')

        box = layout.box()
        box.label(text="Align Cut Plane", icon='AXIS_FRONT')
        grid = box.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
        op = grid.operator("myogen.align_section_cut", text="Transverse")
        op.plane = 'TRANSVERSE'
        op = grid.operator("myogen.align_section_cut", text="Sagittal")
        op.plane = 'SAGITTAL'
        op = grid.operator("myogen.align_section_cut", text="Coronal")
        op.plane = 'CORONAL'

        row = box.row(align=True)
        op = row.operator("myogen.align_section_cut", text="Fit Active", icon='BONE_DATA')
        op.plane = 'ACTIVE'
        op = row.operator("myogen.align_section_cut", text="Fit All", icon='FULLSCREEN_ENTER')
        op.plane = 'FIT_ALL'

        box = layout.box()
        box.label(text="Options", icon='PREFERENCES')
        col = box.column(align=True)
        col.prop(props, "section_cut_scope", text="Scope")
        col.prop(props, "section_cut_mode", text="Mode")
        col.prop(props, "section_cut_solver", text="Solver")
        box.operator("myogen.refresh_section_cut", text="Refresh Targets", icon='FILE_REFRESH')

        info = layout.column(align=True)
        info.scale_y = 0.75
        info.label(text="Move (G), rotate (R) or scale (S) the wireframe", icon='INFO')
        info.label(text="cutter cube in 3D view to inspect interior.", icon='BLANK1')
        info.label(text="Meshes are untouched. Deactivating restores all.", icon='BLANK1')


classes = (
    MYOGEN_OT_toggle_section_cut,
    MYOGEN_OT_align_section_cut,
    MYOGEN_OT_flip_section_cut,
    MYOGEN_OT_refresh_section_cut,
    MYOGEN_OT_select_cutter,
    MYOGENERATOR_PT_cross_section,
)
