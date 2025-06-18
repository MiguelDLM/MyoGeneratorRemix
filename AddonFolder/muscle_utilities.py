import bpy
import bmesh
from mathutils import Vector

def select_and_edit_object(obj):
    """
    Set up an object for face selection in edit mode
    """
    # Ensure we have a valid context for operations
    if not obj or obj.type != 'MESH':
        return
    
    # Deselect all objects manually (safer than using operator)
    for scene_obj in bpy.context.scene.objects:
        scene_obj.select_set(False)
    
    # Set the object as active and selected
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Ensure we're in object mode before doing mode operations
    if bpy.context.mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError:
            pass

    # Use a temporary override context to ensure the mode set operation is valid
    try:
        # Find a 3D viewport for proper context
        view_3d_area = None
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    view_3d_area = area
                    break
            if view_3d_area:
                break
        
        if view_3d_area:
            with bpy.context.temp_override(window=window, area=view_3d_area, active_object=obj):
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_mode(type='FACE')
                try:
                    bpy.ops.wm.tool_set_by_id(name="builtin.select_lasso", space_type='VIEW_3D')
                except RuntimeError:
                    pass  # Tool setting might fail, but that's OK
                bpy.ops.mesh.select_all(action='DESELECT')
        else:
            # Fallback without operators
            bpy.ops.object.mode_set(mode='EDIT')
            
    except RuntimeError as e:
        print(f"Warning: Could not set up edit mode properly: {e}")
        # Fallback: at least try to get into edit mode
        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except RuntimeError:
            pass

def with_temp_object_active(context, obj, action):
    """
    Helper function to:
      1. Store the current active object and mode
      2. Set 'obj' as active, switch to OBJECT mode
      3. Run 'action' callback
      4. Restore original active object and mode
    """
    if not obj:
        return
        
    original_active_obj = context.view_layer.objects.active
    original_mode = original_active_obj.mode if original_active_obj else 'OBJECT'

    try:
        # Switch to object mode and select our target
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Deselect all and select target
        for scene_obj in context.scene.objects:
            scene_obj.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Perform the custom action
        action()

    except Exception as e:
        print(f"Error in with_temp_object_active: {e}")
    finally:
        # Restore original selection and mode
        try:
            for scene_obj in context.scene.objects:
                scene_obj.select_set(False)
            if original_active_obj:
                original_active_obj.select_set(True)
                context.view_layer.objects.active = original_active_obj
                if original_mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode=original_mode)
        except RuntimeError:
            print("Couldn't restore previous mode (possibly invalid).")


def update_mesh_density(self, context):
    """Update mesh density in real-time if preview is active"""
    # Trigger update during preview mode
    if hasattr(context.scene, 'muscle_preview_active') and context.scene.muscle_preview_active:
        # Force immediate update by triggering redraw for all 3D viewports
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        
        # Force scene update
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


def get_contour_direction_vector(contour_obj, reference_point):
    """
    Calculate the direction vector of a contour relative to a reference point
    Returns a vector indicating the general direction of vertex flow
    """
    if not contour_obj or contour_obj.type != 'CURVE':
        return Vector((0, 0, 0))
    
    if not contour_obj.data.splines:
        return Vector((0, 0, 0))
    
    spline = contour_obj.data.splines[0]
    
    # Get contour points in world coordinates
    if spline.type in ['NURBS', 'POLY']:
        points = [contour_obj.matrix_world @ Vector(point.co[:3]) for point in spline.points]
    elif spline.type == 'BEZIER':
        points = [contour_obj.matrix_world @ point.co for point in spline.bezier_points]
    else:
        return Vector((0, 0, 0))
    
    if len(points) < 3:
        return Vector((0, 0, 0))
    
    # Calculate the centroid of the contour
    contour_centroid = sum(points, Vector()) / len(points)
    
    # Calculate direction vector from contour centroid to reference point
    direction_to_ref = (reference_point - contour_centroid).normalized()
    
    # Calculate the "flow" direction of vertices by sampling a few segments
    flow_vector = Vector((0, 0, 0))
    sample_count = min(8, len(points) // 2)  # Sample several segments
    
    for i in range(sample_count):
        idx1 = i * len(points) // sample_count
        idx2 = (idx1 + 1) % len(points)
        
        # Vector from current point to next point
        segment_vector = points[idx2] - points[idx1]
        
        # Vector from contour center to current point
        radial_vector = points[idx1] - contour_centroid
        
        # Cross product gives us the "circulation" direction
        circulation = radial_vector.cross(segment_vector)
        flow_vector += circulation
    
    flow_vector = flow_vector.normalized()
    
    # Project flow onto the direction toward reference point
    flow_alignment = flow_vector.dot(direction_to_ref)
    
    return flow_vector, flow_alignment


def align_contour_directions(origin_contour, insertion_contour):
    """
    Align the direction of contours so they both circulate in compatible directions
    for proper lofting without twisted geometry
    """
    if not (origin_contour and insertion_contour):
        return False
    
    if not (origin_contour.type == 'CURVE' and insertion_contour.type == 'CURVE'):
        return False
    
    # Calculate centroids
    origin_centroid = calculate_curve_centroid(origin_contour)
    insertion_centroid = calculate_curve_centroid(insertion_contour)
    
    # Get direction information for both contours
    origin_flow, origin_alignment = get_contour_direction_vector(origin_contour, insertion_centroid)
    insertion_flow, insertion_alignment = get_contour_direction_vector(insertion_contour, origin_centroid)
    
    # If the alignments have opposite signs, the contours are circulating in opposite directions
    if origin_alignment * insertion_alignment < 0:
        print(f"Contour directions are misaligned (origin: {origin_alignment:.3f}, insertion: {insertion_alignment:.3f})")
        print("Reversing insertion contour direction...")
        
        # Reverse the insertion contour
        return reverse_contour_direction(insertion_contour)
    else:
        print(f"Contour directions are aligned (origin: {origin_alignment:.3f}, insertion: {insertion_alignment:.3f})")
        return True


def calculate_curve_centroid(curve_obj):
    """Calculate the centroid of a curve object"""
    if not curve_obj or curve_obj.type != 'CURVE':
        return Vector((0, 0, 0))
    
    if not curve_obj.data.splines:
        return Vector((0, 0, 0))
    
    spline = curve_obj.data.splines[0]
    points = []
    
    if spline.type in ['NURBS', 'POLY']:
        points = [curve_obj.matrix_world @ Vector(point.co[:3]) for point in spline.points]
    elif spline.type == 'BEZIER':
        points = [curve_obj.matrix_world @ point.co for point in spline.bezier_points]
    
    if not points:
        return Vector((0, 0, 0))
    
    return sum(points, Vector()) / len(points)


def reverse_contour_direction(contour_obj):
    """
    Reverse the direction of vertices in a contour curve
    """
    if not contour_obj or contour_obj.type != 'CURVE':
        return False
    
    if not contour_obj.data.splines:
        return False
    
    spline = contour_obj.data.splines[0]
    
    try:
        if spline.type in ['NURBS', 'POLY']:
            # Get all point coordinates
            coords = [Vector(point.co) for point in spline.points]
            # Reverse the order
            coords.reverse()
            # Apply back to spline
            for i, coord in enumerate(coords):
                spline.points[i].co = coord
                
        elif spline.type == 'BEZIER':
            # Get all bezier point data
            bezier_data = []
            for point in spline.bezier_points:
                bezier_data.append({
                    'co': Vector(point.co),
                    'handle_left': Vector(point.handle_left),
                    'handle_right': Vector(point.handle_right),
                    'handle_left_type': point.handle_left_type,
                    'handle_right_type': point.handle_right_type
                })
            
            # Reverse the order and swap handles
            bezier_data.reverse()
            
            # Apply back to spline with swapped handles
            for i, data in enumerate(bezier_data):
                point = spline.bezier_points[i]
                point.co = data['co']
                # Swap left and right handles when reversing
                point.handle_left = data['handle_right']
                point.handle_right = data['handle_left']
                point.handle_left_type = data['handle_right_type']
                point.handle_right_type = data['handle_left_type']
        
        # Update the curve properly
        contour_obj.data.update_tag()
        return True
        
    except Exception as e:
        print(f"Error reversing contour direction: {e}")
        return False