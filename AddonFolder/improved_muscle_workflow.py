"""Operators of the muscle creation workflow: preview, path and final mesh.

The work is done in :mod:`volume_builder` (belly, live preview) and
:mod:`preview` (loft, path geometry); these operators only call it and
report.
"""

import bpy

from . import myo_record
from . import preview
from . import rings
from . import volume_builder
from .muscle_texture import apply_muscle_material


def _muscle_collection(operator, context):
    coll, _objs = preview.muscle_objects(context)
    if coll is None:
        operator.report({'ERROR'}, f"Collection '{context.scene.myogen.muscle_name}' not found in 'muscles'")
    return coll


def _object_mode(context):
    if context.active_object is not None and context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


class Muscle_Preview_Update_Op(bpy.types.Operator):
    """Start the live preview of the muscle belly"""
    bl_idname = "myogen.muscle_preview_update"
    bl_label = "Start Preview"
    bl_description = ("Build the belly as it will be generated, at draft resolution, along the muscle path, "
                      "and keep it updated while you edit the path, the rings or the settings")

    def execute(self, context):
        if _muscle_collection(self, context) is None:
            return {'CANCELLED'}
        _object_mode(context)
        try:
            volume_builder.start_live(context)
        except ValueError as error:
            self.report({'ERROR'}, f"Preview failed: {error}")
            return {'CANCELLED'}
        self.report({'INFO'}, context.scene.myogen.preview_status)
        return {'FINISHED'}


class Muscle_Preview_Stop_Op(bpy.types.Operator):
    """Stop updating the preview"""
    bl_idname = "myogen.muscle_preview_stop"
    bl_label = "Stop Preview"
    bl_description = "Stop rebuilding the preview on changes; the preview mesh is kept"

    def execute(self, context):
        volume_builder.stop_live(context)
        return {'FINISHED'}


def _select_only(context, objs, active):
    for obj in context.view_layer.objects:
        obj.select_set(False)
    for obj in objs:
        obj.hide_set(False)
        obj.select_set(True)
    context.view_layer.objects.active = active


class Muscle_Edit_Path_Op(bpy.types.Operator):
    """Edit the muscle path in Edit Mode"""
    bl_idname = "myogen.edit_path"
    bl_label = "Edit Path"
    bl_description = ("Select the muscle path and enter Edit Mode: move its points and handles to set the "
                      "course of the belly. The preview and the rings follow")

    def execute(self, context):
        coll, objs = preview.muscle_objects(context)
        if coll is None:
            self.report({'ERROR'}, "No muscle collection")
            return {'CANCELLED'}
        _object_mode(context)
        try:
            path = volume_builder.ensure_path(context, context.scene.myogen.muscle_name, coll, objs)
        except (KeyError, AttributeError):
            self.report({'ERROR'}, "Origin and insertion surfaces are required")
            return {'CANCELLED'}
        path.show_in_front = True
        path.hide_select = False
        _select_only(context, [path], path)
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class Muscle_Reset_Path_Op(bpy.types.Operator):
    """Replace the path with the default one"""
    bl_idname = "myogen.reset_path"
    bl_label = "Reset Path"
    bl_description = ("Replace the muscle path with the default one: from each attachment along its outward "
                      "normal, outside the bone")

    def execute(self, context):
        coll, objs = preview.muscle_objects(context)
        if coll is None or objs.get("origin") is None or objs.get("insertion") is None:
            self.report({'ERROR'}, "Origin and insertion surfaces are required")
            return {'CANCELLED'}
        _object_mode(context)
        name = context.scene.myogen.muscle_name
        preview.write_path(coll, name, preview.default_path_points(context.scene.myogen, objs["origin"],
                                                                   objs["insertion"]))
        volume_builder.schedule_rebuild(context)
        return {'FINISHED'}


class Muscle_Select_Rings_Op(bpy.types.Operator):
    """Select the section rings"""
    bl_idname = "myogen.select_rings"
    bl_label = "Select Rings"
    bl_description = ("Select the rings on the path. Click one: G slides it along the path, S sizes the "
                      "section (S X X width, S Y Y thickness), R turns it")

    @classmethod
    def poll(cls, context):
        return context.scene.myogen.use_controls

    def execute(self, context):
        coll, _objs = preview.muscle_objects(context)
        name = context.scene.myogen.muscle_name
        ring_list = rings.ring_objects(coll, name) if coll else []
        if not ring_list:
            self.report({'ERROR'}, "Start the preview first (it creates the rings)")
            return {'CANCELLED'}
        _object_mode(context)
        _select_only(context, ring_list, ring_list[len(ring_list) // 2])
        return {'FINISHED'}


class Muscle_Reset_Rings_Op(bpy.types.Operator):
    """Replace the rings with evenly spaced default ones"""
    bl_idname = "myogen.reset_rings"
    bl_label = "Reset Rings"
    bl_description = ("Replace the rings with the number set below, evenly spaced along the path and showing "
                      "the muscle's natural shape (no change)")

    @classmethod
    def poll(cls, context):
        return context.scene.myogen.use_controls

    def execute(self, context):
        _object_mode(context)
        try:
            volume_builder.reset_rings(context, context.scene.myogen.muscle_name)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        volume_builder.schedule_rebuild(context)
        return {'FINISHED'}


class Muscle_Mesh_Generation_Op(bpy.types.Operator):
    """Generate the final muscle mesh"""
    bl_idname = "myogen.muscle_mesh_generation"
    bl_label = "Generate Final Mesh"
    bl_description = ("Build <muscle>_muscle at full resolution with the current path, rings and settings, and "
                      "remove the construction helpers (preview, wire tube, rings); the path is kept for the "
                      "measurements. Replaces an earlier final mesh")

    def execute(self, context):
        if _muscle_collection(self, context) is None:
            return {'CANCELLED'}
        _object_mode(context)
        name = context.scene.myogen.muscle_name
        try:
            belly, report = volume_builder.generate_final(context, name)
        except ValueError as error:
            self.report({'ERROR'}, f"Final mesh failed: {error}")
            return {'CANCELLED'}
        apply_muscle_material(belly)
        for obj in context.view_layer.objects:
            obj.select_set(False)
        belly.select_set(True)
        context.view_layer.objects.active = belly
        mm = report["voxel"] * myo_record.metres_per_unit(context.scene) * 1000
        self.report({'INFO'}, f"'{belly.name}': {len(belly.data.vertices)} vertices, voxel {mm:.2f} mm, "
                              f"{report['seconds']:.1f} s, {report['anchored_count']} anchored vertices")
        if report.get("pieces", 1) > 1:
            self.report({'WARNING'}, f"The belly has {report['pieces']} separate pieces: widen the rings between them")
        return {'FINISHED'}
