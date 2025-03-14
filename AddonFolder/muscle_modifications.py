import bpy
from .muscle_utilities import with_temp_object_active


class Swap_Origin_Insertion_Op(bpy.types.Operator):
    bl_idname = "view3d.swap_origin_insertion"
    bl_label = "Swap Origin and Insertion"

    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            print("Muscles collection not found")
            return {'CANCELLED'}
        if muscle_name not in muscles_collection.children:
            print(f"Muscle collection '{muscle_name}' not found in muscles collection")
            return {'CANCELLED'}
        target_collection = muscles_collection.children[muscle_name]

        muscle_obj = target_collection.objects.get(muscle_name + "_muscle")
        if not muscle_obj:
            print(f"Muscle object '{muscle_name}_muscle' not found in collection '{muscle_name}'")
            return {'CANCELLED'}

        def swap_action():
            if "Geometry Nodes" in muscle_obj.modifiers:
                socket_val = muscle_obj.modifiers["Geometry Nodes"]["Socket_12"]
                muscle_obj.modifiers["Geometry Nodes"]["Socket_12"] = not socket_val
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                print("Geometry Nodes modifier not found on muscle object")

        with_temp_object_active(context, muscle_obj, swap_action)
        return {'FINISHED'}


class Switch_Origin_Vertex_Order_Op(bpy.types.Operator):
    bl_idname = "view3d.switch_vertex_order_origin"
    bl_label = "Switch Origin Vertex Order"

    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            print("Muscles collection not found")
            return {'CANCELLED'}
        if muscle_name not in muscles_collection.children:
            print(f"Muscle collection '{muscle_name}' not found in muscles collection")
            return {'CANCELLED'}
        target_collection = muscles_collection.children[muscle_name]

        muscle_obj = target_collection.objects.get(muscle_name + "_muscle")
        if not muscle_obj:
            print(f"Muscle object '{muscle_name}_muscle' not found in collection '{muscle_name}'")
            return {'CANCELLED'}

        def switch_origin_action():
            if "Geometry Nodes" in muscle_obj.modifiers:
                socket_val = muscle_obj.modifiers["Geometry Nodes"]["Socket_13"]
                muscle_obj.modifiers["Geometry Nodes"]["Socket_13"] = not socket_val
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                print("Geometry Nodes modifier not found on muscle object")

        with_temp_object_active(context, muscle_obj, switch_origin_action)
        return {'FINISHED'}


class Switch_Insertion_Vertex_Order_Op(bpy.types.Operator):
    bl_idname = "view3d.switch_vertex_order_insertion"
    bl_label = "Switch Insertion Vertex Order"

    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            print("Muscles collection not found")
            return {'CANCELLED'}
        if muscle_name not in muscles_collection.children:
            print(f"Muscle collection '{muscle_name}' not found in muscles collection")
            return {'CANCELLED'}
        target_collection = muscles_collection.children[muscle_name]

        muscle_obj = target_collection.objects.get(muscle_name + "_muscle")
        if not muscle_obj:
            print(f"Muscle object '{muscle_name}_muscle' not found in collection '{muscle_name}'")
            return {'CANCELLED'}

        def switch_insertion_action():
            if "Geometry Nodes" in muscle_obj.modifiers:
                socket_val = muscle_obj.modifiers["Geometry Nodes"]["Socket_14"]
                muscle_obj.modifiers["Geometry Nodes"]["Socket_14"] = not socket_val
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                print("Geometry Nodes modifier not found on muscle object")

        with_temp_object_active(context, muscle_obj, switch_insertion_action)
        return {'FINISHED'}
