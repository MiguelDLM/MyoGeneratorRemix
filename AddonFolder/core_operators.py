"""
Core operators for the MyoGeneratorRemix addon.
Contains essential operators that support the old workflow interface.
"""

import bpy
import bmesh
import csv
import os
from mathutils import Vector
from .muscle_utilities import (select_and_edit_object, with_temp_object_active,
                             calculate_mesh_area, calculate_mesh_centroid,
                             calculate_curve_length, calculate_muscle_volume)


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
    """Create a mesh from selected faces and generate contour curve"""
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
    
    # Check if objects already exist
    existing_mesh = target_collection.objects.get(f"{muscle_name}_{mesh_name}")
    existing_contour = target_collection.objects.get(f"{muscle_name}_{mesh_name}_contour")
    
    if existing_mesh or existing_contour:
        operator.report({'WARNING'}, f"Object '{mesh_name}' already exists in collection '{muscle_name}'")
        return
    
    # Get the BMesh representation
    bm = bmesh.from_edit_mesh(obj.data)
    
    # Find the selected faces
    selected_faces = [face for face in bm.faces if face.select]
    
    if not selected_faces:
        operator.report({'WARNING'}, "No faces selected")
        return
    
    # Create a new mesh and object for the surface
    new_mesh = bpy.data.meshes.new(f"{muscle_name}_{mesh_name}")
    new_object = bpy.data.objects.new(f"{muscle_name}_{mesh_name}", new_mesh)
    
    # Create a new BMesh for the new object
    new_bm = bmesh.new()
    
    # Copy selected faces to the new BMesh with world coordinates
    for face in selected_faces:
        # Transform vertices to world coordinates
        world_verts = []
        for vert in face.verts:
            world_co = obj.matrix_world @ vert.co
            world_verts.append(new_bm.verts.new(world_co))
        
        new_face = new_bm.faces.new(world_verts)
        new_face.normal_update()
    
    # Finish up the new BMesh
    new_bm.to_mesh(new_mesh)
    new_bm.free()
    
    # Add the new object to the target collection
    target_collection.objects.link(new_object)
    
    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Set the new object as active and selected
    bpy.ops.object.select_all(action='DESELECT')
    new_object.select_set(True)
    bpy.context.view_layer.objects.active = new_object
    
    # Now duplicate this object to create the contour
    bpy.ops.object.duplicate()
    
    # Get the duplicated object (should be the active object now)
    contour_object = bpy.context.active_object
    contour_object.name = f"{muscle_name}_{mesh_name}_contour"
    
    # Move contour to target collection
    for collection in contour_object.users_collection:
        collection.objects.unlink(contour_object)
    target_collection.objects.link(contour_object)
    
    # Switch to edit mode to extract boundary loop
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.region_to_loop()
    
    # Separate the selected edges (boundary loop)
    bpy.ops.mesh.separate(type='SELECTED')
    
    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # After separate, we have two objects:
    # 1. contour_object (the original faces, now without boundary)  
    # 2. boundary_object (just the boundary loop)
    # We want to keep only the boundary_object and remove the faces
    
    # Find the boundary object (the newly created one with boundary loop)
    boundary_object = None
    for selected_obj in bpy.context.selected_objects:
        if selected_obj != contour_object:
            boundary_object = selected_obj
            break
    
    if boundary_object:
        # Remove the original contour object (the solid faces - we don't need them)
        bpy.data.objects.remove(contour_object, do_unlink=True)
        
        # The boundary object becomes our contour
        contour_object = boundary_object
        contour_object.name = f"{muscle_name}_{mesh_name}_contour"
        
        # Move to target collection
        for collection in contour_object.users_collection:
            collection.objects.unlink(contour_object)
        target_collection.objects.link(contour_object)
        
        # Select only the contour object and convert to curve
        bpy.ops.object.select_all(action='DESELECT')
        contour_object.select_set(True)
        bpy.context.view_layer.objects.active = contour_object
        
        # Convert to curve
        bpy.ops.object.convert(target='CURVE')
        
        # Now that it's a curve, clean up splines - keep only the largest spline if multiple exist
        if hasattr(contour_object.data, 'splines') and len(contour_object.data.splines) > 1:
            max_points = 0
            max_spline = None
            for spline in contour_object.data.splines:
                points_count = len(spline.points) if spline.type in ['NURBS', 'POLY'] else len(spline.bezier_points)
                if points_count > max_points:
                    max_points = points_count
                    max_spline = spline
            
            # Remove other splines
            splines_to_remove = [spline for spline in contour_object.data.splines if spline != max_spline]
            for spline in splines_to_remove:
                contour_object.data.splines.remove(spline)
        
        # Make sure the curve is cyclic (closed)
        if hasattr(contour_object.data, 'splines') and len(contour_object.data.splines) > 0:
            contour_object.data.splines[0].use_cyclic_u = True
    else:
        # If no boundary object found, something went wrong
        operator.report({'WARNING'}, "Could not extract boundary loop properly")
    
    operator.report({'INFO'}, f"Created mesh '{muscle_name}_{mesh_name}' and contour curve")
    
    # Return to object mode and deselect all
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


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
        
        # Handle Blender's relative path notation
        if folder_path.startswith("//"):
            # Convert Blender relative path to absolute path
            folder_path = bpy.path.abspath(folder_path)
        
        # Ensure the directory exists, create if it doesn't
        try:
            os.makedirs(folder_path, exist_ok=True)
        except OSError as e:
            self.report({'ERROR'}, f"Cannot create directory '{folder_path}': {str(e)}")
            return {'CANCELLED'}
        
        csv_path = os.path.join(folder_path, file_name + ".csv")
        
        # Get muscles collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            self.report({'ERROR'}, "No muscles collection found")
            return {'CANCELLED'}
        
        # Calculate parameters for each muscle
        muscle_data = []
        muscle_constant = context.scene.muscle_constant  # Get user-defined muscle constant
        
        for muscle_collection in muscles_collection.children:
            muscle_name = muscle_collection.name
            
            # Get muscle objects
            muscle_obj = muscle_collection.objects.get(f"{muscle_name}_muscle")
            origin_obj = muscle_collection.objects.get(f"{muscle_name}_origin") 
            insertion_obj = muscle_collection.objects.get(f"{muscle_name}_insertion")
            curve_obj = muscle_collection.objects.get(f"{muscle_name}_curve")
            
            if muscle_obj and muscle_obj.type == 'MESH':
                # Calculate muscle volume
                volume = calculate_muscle_volume(muscle_obj)
                
                # Calculate fiber length (curve length)
                fiber_length = 0.0
                if curve_obj:
                    fiber_length = calculate_curve_length(curve_obj)
                
                # Calculate origin area and centroid
                origin_area = 0.0
                origin_centroid = Vector((0, 0, 0))
                if origin_obj:
                    origin_area = calculate_mesh_area(origin_obj)
                    origin_centroid = calculate_mesh_centroid(origin_obj)
                
                # Calculate insertion area and centroid
                insertion_area = 0.0
                insertion_centroid = Vector((0, 0, 0))
                if insertion_obj:
                    insertion_area = calculate_mesh_area(insertion_obj)
                    insertion_centroid = calculate_mesh_centroid(insertion_obj)
                
                # Calculate PCSA (Physiological Cross-Sectional Area)
                pcsa = 0.0
                if fiber_length > 0:
                    pcsa = volume / fiber_length

                # Store PCSA in the objects for reference
                if muscle_obj:
                    muscle_obj["PCSA"] = pcsa
                if origin_obj:
                    origin_obj["PCSA"] = pcsa
                if insertion_obj:
                    insertion_obj["PCSA"] = pcsa

                # Calculate muscle force
                force = pcsa * muscle_constant
                
                # Calculate linear length (distance between centroids)
                linear_length = (insertion_centroid - origin_centroid).length
                
                muscle_data.append({
                    'name': muscle_name,
                    'volume': volume,
                    'fiber_length': fiber_length,
                    'origin_area': origin_area,
                    'insertion_area': insertion_area,
                    'origin_centroid': f"({origin_centroid.x:.4f}, {origin_centroid.y:.4f}, {origin_centroid.z:.4f})",
                    'insertion_centroid': f"({insertion_centroid.x:.4f}, {insertion_centroid.y:.4f}, {insertion_centroid.z:.4f})",
                    'linear_length': linear_length,
                    'pcsa': pcsa,
                    'force': force
                })
        
        # Write to CSV (create new file or overwrite existing)
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'name', 'volume', 'fiber_length', 'origin_area', 'insertion_area',
                    'origin_centroid', 'insertion_centroid', 'linear_length', 
                    'pcsa', 'force'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in muscle_data:
                    writer.writerow(row)
            
            self.report({'INFO'}, f"Muscle parameters saved to {csv_path}")
        except PermissionError:
            self.report({'ERROR'}, f"Permission denied. Cannot write to '{csv_path}'. Check file permissions.")
            return {'CANCELLED'}
        except FileNotFoundError:
            self.report({'ERROR'}, f"Directory not found: '{folder_path}'. Please select a valid directory.")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save CSV: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
