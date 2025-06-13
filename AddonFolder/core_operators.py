"""
Core operators for the MyoGeneratorRemix addon.
Contains essential operators that support the old workflow interface.
"""

import bpy
import bmesh
import csv
import os
from mathutils import Vector
from .muscle_utilities import select_and_edit_object, with_temp_object_active


class Muscle_Name_Submition(bpy.types.Operator):
    """Submit muscle name and create collection"""
    bl_idname = "view3d.submit_button"
    bl_label = "Submit Muscle Name"
    bl_description = "Submit Muscle Name"

    def execute(self, context):
        objName = bpy.context.scene.muscle_Name

        # Check if the "muscles" collection exists
        if "muscles" not in bpy.data.collections:
            # Create the "muscles" collection
            muscles_collection = bpy.data.collections.new("muscles")
            bpy.context.scene.collection.children.link(muscles_collection)
        else:
            muscles_collection = bpy.data.collections["muscles"]

        # Check if a collection with the name objName already exists inside "muscles"
        if objName in muscles_collection.children:
            self.report({'WARNING'}, f"Muscle '{objName}' already exists, choose a different name.")            
            return {'CANCELLED'}
        else:
            # Create a new collection inside "muscles" with the name objName
            new_collection = bpy.data.collections.new(objName)
            muscles_collection.children.link(new_collection)

        return {'FINISHED'}


class Select_Origin_Op(bpy.types.Operator):
    """Select origin faces"""
    bl_idname = "view3d.select_origin"
    bl_label = "Select Origin"
    bl_description = "Select Origin of the muscle"

    def execute(self, context):
        # Get the selected object in origin object
        origin_object = bpy.context.scene.origin_object
        select_and_edit_object(origin_object)
        return {'FINISHED'}


class Select_Insertion_Op(bpy.types.Operator):
    """Select insertion faces"""
    bl_idname = "view3d.select_insertion"
    bl_label = "Select Insertion"
    bl_description = "Select Insertion of the muscle"

    def execute(self, context):
        # Get the selected object in insertion object
        insertion_object = bpy.context.scene.insertion_object
        select_and_edit_object(insertion_object)
        return {'FINISHED'}


def create_mesh_from_selected_faces(operator, mesh_name):
    """Create a mesh from selected faces"""
    # Get active object
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        operator.report({'ERROR'}, "No active mesh object")
        return
    
    muscle_name = bpy.context.scene.muscle_Name
    
    # Get or create muscle collection
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection:
        operator.report({'ERROR'}, "Muscles collection not found")
        return
    
    if muscle_name not in muscles_collection.children:
        operator.report({'ERROR'}, f"Muscle collection '{muscle_name}' not found")
        return
    
    target_collection = muscles_collection.children[muscle_name]
    
    # Duplicate selected faces
    bpy.ops.mesh.duplicate()
    bpy.ops.mesh.separate(type='SELECTED')
    
    # Get the new object (should be the last selected)
    new_obj = None
    for selected_obj in bpy.context.selected_objects:
        if selected_obj != obj:
            new_obj = selected_obj
            break
    
    if new_obj:
        new_obj.name = f"{muscle_name}_{mesh_name}"
        
        # Move to target collection
        for collection in new_obj.users_collection:
            collection.objects.unlink(new_obj)
        target_collection.objects.link(new_obj)


class Submit_Origin_Op(bpy.types.Operator):
    """Submit origin selection"""
    bl_idname = "view3d.submit_origin"
    bl_label = "Submit Origin"
    bl_description = "Submit Origin of the muscle"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'EDIT'

    def execute(self, context):
        create_mesh_from_selected_faces(self, "origin")
        return {'FINISHED'}


class Submit_Insertion_Op(bpy.types.Operator):
    """Submit insertion selection"""
    bl_idname = "view3d.submit_insertion"
    bl_label = "Submit Insertion"
    bl_description = "Submit Insertion of the muscle"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'EDIT'

    def execute(self, context):
        create_mesh_from_selected_faces(self, "insertion")
        return {'FINISHED'}


class Next_Muscle_Op(bpy.types.Operator):
    """Move to next muscle"""
    bl_idname = "view3d.next_muscle"
    bl_label = "Next Muscle"
    bl_description = "Start the creation of the next muscle"

    def execute(self, context):
        # Clean the muscle name from the muscle panel
        bpy.context.scene.muscle_Name = "Insert muscle name"
        # Change to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}


class Calculate_Muscle_Parameters_Op(bpy.types.Operator):
    """Calculate muscle parameters and save to CSV"""
    bl_idname = "view3d.calculate_muscle_parameters"
    bl_label = "Calculate Muscle Parameters"
    bl_description = "Calculate muscle parameters and save to CSV file"

    def execute(self, context):
        # Get file path and name
        folder_path = context.scene.conf_path
        file_name = context.scene.file_name
        
        if not folder_path or not file_name:
            self.report({'ERROR'}, "Please specify folder path and file name")
            return {'CANCELLED'}
        
        csv_path = os.path.join(folder_path, file_name + ".csv")
        
        # Get muscles collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            self.report({'ERROR'}, "No muscles collection found")
            return {'CANCELLED'}
        
        # Calculate parameters for each muscle
        muscle_data = []
        for muscle_collection in muscles_collection.children:
            muscle_name = muscle_collection.name
            muscle_obj = muscle_collection.objects.get(f"{muscle_name}_muscle")
            
            if muscle_obj and muscle_obj.type == 'MESH':
                # Calculate volume
                bm = bmesh.new()
                bm.from_mesh(muscle_obj.data)
                bm.transform(muscle_obj.matrix_world)
                volume = bm.calc_volume()
                bm.free()
                
                muscle_data.append({
                    'name': muscle_name,
                    'volume': volume
                })
        
        # Write to CSV
        try:
            with open(csv_path, 'w', newline='') as csvfile:
                fieldnames = ['name', 'volume']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in muscle_data:
                    writer.writerow(row)
            
            self.report({'INFO'}, f"Muscle parameters saved to {csv_path}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save CSV: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
