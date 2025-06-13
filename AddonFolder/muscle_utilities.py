import bpy
import bmesh
from mathutils import Vector

def select_and_edit_object(obj):
    """
    Set up an object for face selection in edit mode
    """
    # Ensure the object is selected
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

    # Use a temporary override context to ensure the mode set operation is valid
    with bpy.context.temp_override(active_object=obj):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.wm.tool_set_by_id(name="builtin.select_lasso", space_type='VIEW_3D')
        bpy.ops.mesh.select_all(action='DESELECT')

def with_temp_object_active(context, obj, action):
    """
    Helper function to:
      1. Store the current active object and mode
      2. Set 'obj' as active, switch to OBJECT mode
      3. Run 'action' callback
      4. Restore original active object and mode
    """
    original_active_obj = context.view_layer.objects.active
    original_mode = original_active_obj.mode if original_active_obj else 'OBJECT'

    # Switch to object mode and select our target
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj

    # Perform the custom action
    action()

    # Restore original selection and mode
    bpy.ops.object.select_all(action='DESELECT')
    if original_active_obj:
        original_active_obj.select_set(True)
        context.view_layer.objects.active = original_active_obj
        try:
            bpy.ops.object.mode_set(mode=original_mode)
        except RuntimeError:
            print("Couldn't restore previous mode (possibly invalid).")

def create_mesh_from_selected_faces(self, mesh_name):
    """
    Create a new mesh object from selected faces
    """
    # Get the selected object based on mesh_name
    if mesh_name == "origin":
        selected_object = bpy.context.scene.origin_object
    elif mesh_name == "insertion":
        selected_object = bpy.context.scene.insertion_object
    else:
        self.report({'ERROR'}, f"Invalid object type '{mesh_name}'")
        return {'CANCELLED'}
    
    objName = bpy.context.scene.muscle_Name

    # Check if the object already exists in the collection
    muscles_collection = bpy.data.collections.get("muscles")
    if muscles_collection and objName in muscles_collection.children:
        target_collection = muscles_collection.children[objName]
        if mesh_name in target_collection.objects:
            self.report({'WARNING'}, f"Object '{mesh_name}' already exists in collection '{objName}'")
            return {'CANCELLED'}
    else:
        self.report({'ERROR'}, f"Collection '{objName}' not found in 'muscles'")
        return {'CANCELLED'}
    
    # Ensure the selected object is in edit mode
    if bpy.context.object != selected_object or bpy.context.object.mode != 'EDIT':
        self.report({'ERROR'}, f"The active object is not in edit mode or is not the correct object for '{mesh_name}'")
        return {'CANCELLED'}
    # Get the BMesh representation
    bm = bmesh.from_edit_mesh(selected_object.data)

    # Find the selected faces
    selected_faces = [face for face in bm.faces if face.select]

    if not selected_faces:
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'WARNING'}, "No faces selected")
        return {'CANCELLED'}

    # Create a new mesh and object
    new_mesh = bpy.data.meshes.new(mesh_name)
    new_object = bpy.data.objects.new(mesh_name, new_mesh)
    bpy.context.collection.objects.link(new_object)

    # Create a new BMesh for the new object
    new_bm = bmesh.new()

    # Copy selected faces to the new BMesh
    for face in selected_faces:
        new_face = new_bm.faces.new([new_bm.verts.new(v.co) for v in face.verts])
        new_face.normal_update()

    # Finish up the new BMesh
    new_bm.to_mesh(new_mesh)
    new_bm.free()

    # Add the new object to the collection with objName inside "muscles"
    target_collection.objects.link(new_object)
    bpy.context.collection.objects.unlink(new_object)

    # Set the new object as active
    bpy.context.view_layer.objects.active = new_object
    new_object.select_set(True)

    # Switch to edit mode to remove doubles
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.region_to_loop()
    # Separate the selected edges
    bpy.ops.mesh.separate(type='SELECTED')

    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # Rename the object 
    # Get the last object created
    contour_object = bpy.context.selected_objects[-1]
    mesh_name = objName + "_" + mesh_name
    new_object.name = mesh_name
    contour_object.name = mesh_name + "_contour"

    # Deselect everything and select the contour object
    bpy.ops.object.select_all(action='DESELECT')
    contour_object.select_set(True)
    bpy.context.view_layer.objects.active = contour_object
    # Convert the contour object to a curve
    bpy.ops.object.convert(target='CURVE')

    # Check the number of splines in the curve
    if len(contour_object.data.splines) > 1:
        # Get the curve with the most points
        max_points = 0
        max_spline = None
        for spline in contour_object.data.splines:
            if len(spline.points) > max_points:
                max_points = len(spline.points)
                max_spline = spline
        # Remove the other splines
        for spline in contour_object.data.splines:
            if spline != max_spline:
                contour_object.data.splines.remove(spline)
                print("Spline removed")
            else:
                print("Spline not removed")

    self.report({'INFO'}, f"New mesh '{mesh_name}' with selected faces created and added to collection '{objName}' inside 'muscles'")
    return {'FINISHED'}

def update_muscle_subdivision(self, context):
    muscle_name = context.scene.muscle_Name
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection or (muscle_name not in muscles_collection.children):
        print(f"Muscle collection '{muscle_name}' not found.")
        return
    muscle_obj = muscles_collection.children[muscle_name].objects.get(muscle_name + "_muscle")
    if not muscle_obj:
        print(f"Muscle object '{muscle_name}_muscle' not found.")
        return

    subdivision = context.scene.muscle_subdivisions

    def subdiv_action():
        if "Geometry Nodes" in muscle_obj.modifiers:
            muscle_obj.modifiers["Geometry Nodes"]["Socket_3"] = subdivision
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("Geometry Nodes modifier not found on muscle object")

    with_temp_object_active(context, muscle_obj, subdiv_action)

def update_muscle_resampling(self, context):
    muscle_name = context.scene.muscle_Name
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection or (muscle_name not in muscles_collection.children):
        print(f"Muscle collection '{muscle_name}' not found.")
        return
    muscle_obj = muscles_collection.children[muscle_name].objects.get(muscle_name + "_muscle")
    if not muscle_obj:
        print(f"Muscle object '{muscle_name}_muscle' not found.")
        return

    resampling = context.scene.muscle_resampling

    def resample_action():
        if "Geometry Nodes" in muscle_obj.modifiers:
            muscle_obj.modifiers["Geometry Nodes"]["Socket_2"] = resampling
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("Geometry Nodes modifier not found on muscle object")

    with_temp_object_active(context, muscle_obj, resample_action)

def update_origin_rotation(self, context):
    muscle_name = context.scene.muscle_Name
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection or (muscle_name not in muscles_collection.children):
        print(f"Muscle collection '{muscle_name}' not found.")
        return
    muscle_obj = muscles_collection.children[muscle_name].objects.get(muscle_name + "_muscle")
    if not muscle_obj:
        print(f"Muscle object '{muscle_name}_muscle' not found.")
        return

    origin_rotation = context.scene.origin_rotation

    def origin_rot_action():
        if "Geometry Nodes" in muscle_obj.modifiers:
            muscle_obj.modifiers["Geometry Nodes"]["Socket_8"] = origin_rotation
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("Geometry Nodes modifier not found on muscle object")

    with_temp_object_active(context, muscle_obj, origin_rot_action)

def update_insertion_rotation(self, context):
    muscle_name = context.scene.muscle_Name
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection or (muscle_name not in muscles_collection.children):
        print(f"Muscle collection '{muscle_name}' not found.")
        return
    muscle_obj = muscles_collection.children[muscle_name].objects.get(muscle_name + "_muscle")
    if not muscle_obj:
        print(f"Muscle object '{muscle_name}_muscle' not found.")
        return

    insertion_rotation = context.scene.insertion_rotation

    def insertion_rot_action():
        if "Geometry Nodes" in muscle_obj.modifiers:
            muscle_obj.modifiers["Geometry Nodes"]["Socket_9"] = insertion_rotation
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("Geometry Nodes modifier not found on muscle object")

    with_temp_object_active(context, muscle_obj, insertion_rot_action)

def update_mesh_density(self, context):
    """Update mesh density in real-time if preview is active"""
    # Always trigger update during preview - no need for realtime_update toggle
    if hasattr(context.scene, 'muscle_preview_active') and context.scene.muscle_preview_active:
        # Force immediate update by triggering redraw for all 3D viewports
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        
        # Also force scene update
        context.view_layer.update()


def calculate_mesh_area(mesh_obj):
    """Calculate the surface area of a mesh object"""
    if not mesh_obj or mesh_obj.type != 'MESH':
        return 0.0
    
    # Create bmesh instance from mesh
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    
    # Apply object's world transform
    bm.transform(mesh_obj.matrix_world)
    
    # Calculate total area
    total_area = 0.0
    for face in bm.faces:
        total_area += face.calc_area()
    
    bm.free()
    return total_area


def calculate_mesh_centroid(mesh_obj):
    """Calculate the centroid (center of mass) of a mesh object"""
    if not mesh_obj or mesh_obj.type != 'MESH':
        return Vector((0, 0, 0))
    
    # Get vertices in world coordinates
    vertices = []
    for vertex in mesh_obj.data.vertices:
        world_vertex = mesh_obj.matrix_world @ vertex.co
        vertices.append(world_vertex)
    
    if not vertices:
        return Vector((0, 0, 0))
    
    # Calculate centroid as average of all vertices
    centroid = sum(vertices, Vector()) / len(vertices)
    return centroid


def calculate_curve_length(curve_obj):
    """Calculate the total length of a curve object"""
    if not curve_obj or curve_obj.type != 'CURVE':
        return 0.0
    
    total_length = 0.0
    
    for spline in curve_obj.data.splines:
        if spline.type in ['NURBS', 'POLY']:
            # For NURBS and POLY splines, calculate distance between consecutive points
            points = [curve_obj.matrix_world @ Vector(point.co[:3]) for point in spline.points]
        elif spline.type == 'BEZIER':
            # For Bezier splines, use bezier points
            points = [curve_obj.matrix_world @ point.co for point in spline.bezier_points]
        else:
            continue
        
        # Calculate length by summing distances between consecutive points
        for i in range(1, len(points)):
            segment_length = (points[i] - points[i-1]).length
            total_length += segment_length
    
    return total_length


def calculate_muscle_volume(muscle_obj):
    """Calculate the volume of a muscle mesh object"""
    if not muscle_obj or muscle_obj.type != 'MESH':
        return 0.0
    
    # Create bmesh instance from mesh
    bm = bmesh.new()
    bm.from_mesh(muscle_obj.data)
    
    # Apply object's world transform
    bm.transform(muscle_obj.matrix_world)
    
    # Calculate volume
    volume = bm.calc_volume()
    bm.free()
    
    return abs(volume)  # Use absolute value in case of inverted normals