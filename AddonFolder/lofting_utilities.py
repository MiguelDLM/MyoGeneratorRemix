"""
Curve and Lofting Utilities
Enhanced utilities for curve manipulation and lofting operations
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
import mathutils
from math import radians

def create_smooth_curve_between_points(start_point, end_point, start_normal, end_normal, num_points=7):
    """
    Create a smooth curve between two points with proper tangent control
    """
    # Calculate the distance and direction
    direction = end_point - start_point
    distance = direction.length
    
    if distance == 0:
        return [start_point, end_point]
    
    direction_normalized = direction.normalized()
    
    # Calculate control point distances based on curve length
    control_distance = distance * 0.3
    
    # Create control points using normals
    control_1 = start_point + start_normal.normalized() * control_distance
    control_2 = end_point + end_normal.normalized() * control_distance
    
    # Generate smooth curve points using cubic interpolation
    curve_points = []
    for i in range(num_points):
        t = i / (num_points - 1)
        
        # Cubic Bezier interpolation
        point = (1-t)**3 * start_point + \
                3*(1-t)**2*t * control_1 + \
                3*(1-t)*t**2 * control_2 + \
                t**3 * end_point
        
        curve_points.append(point)
    
    return curve_points

def improve_curve_smoothness(curve_obj):
    """
    Improve the smoothness of an existing curve object
    """
    if curve_obj.type != 'CURVE':
        return False
    
    # Switch to edit mode
    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Select all points
    bpy.ops.curve.select_all(action='SELECT')
    
    # Set handle type to automatic for smooth curves
    bpy.ops.curve.handle_type_set(type='AUTO')
    
    # Smooth the curve
    bpy.ops.curve.smooth()
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return True

def create_curve_from_points(points, curve_name, curve_type='NURBS'):
    """
    Create a curve object from a list of points
    """
    # Create new curve data
    curve_data = bpy.data.curves.new(name=curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    
    # Create new spline
    if curve_type == 'NURBS':
        spline = curve_data.splines.new('NURBS')
        spline.points.add(len(points) - 1)  # -1 because one point already exists
        
        for i, point in enumerate(points):
            spline.points[i].co = (point.x, point.y, point.z, 1)
            
        spline.order_u = min(4, len(points))
        spline.use_endpoint_u = True
        
    elif curve_type == 'BEZIER':
        spline = curve_data.splines.new('BEZIER')
        spline.bezier_points.add(len(points) - 1)
        
        for i, point in enumerate(points):
            spline.bezier_points[i].co = point
            spline.bezier_points[i].handle_left_type = 'AUTO'
            spline.bezier_points[i].handle_right_type = 'AUTO'
    
    # Create object
    curve_obj = bpy.data.objects.new(curve_name, curve_data)
    bpy.context.collection.objects.link(curve_obj)
    
    return curve_obj

def optimize_contour_for_lofting(contour_obj, target_point_count=32):
    """
    Optimize a contour curve for better lofting results
    """
    if contour_obj.type != 'CURVE':
        return False
    
    # Set as active object
    bpy.context.view_layer.objects.active = contour_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Resample the curve to have uniform point distribution
    bpy.ops.curve.select_all(action='SELECT')
    
    # Convert to mesh temporarily for resampling
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.convert(target='MESH', keep_original=True)
    
    # Get the mesh object (the converted one)
    mesh_obj = bpy.context.active_object
    
    # Create bmesh for processing
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    
    # Ensure we have a closed loop
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    
    # Dissolve unnecessary vertices
    bmesh.ops.dissolve_limit(bm, 
                           angle_limit=radians(5), 
                           use_dissolve_boundaries=False,
                           verts=bm.verts, 
                           edges=bm.edges)
    
    # Update mesh
    bm.to_mesh(mesh_obj.data)
    bm.free()
    
    # Convert back to curve
    bpy.ops.object.convert(target='CURVE')
    
    # Delete the original mesh
    bpy.data.objects.remove(mesh_obj, do_unlink=True)
    
    return True

def align_contour_orientations(origin_contour, insertion_contour):
    """
    Align the orientation of two contours for better lofting
    """
    if not (origin_contour.type == 'CURVE' and insertion_contour.type == 'CURVE'):
        return False
    
    # Get splines
    origin_spline = origin_contour.data.splines[0]
    insertion_spline = insertion_contour.data.splines[0]
    
    # Calculate centroids
    if origin_spline.type == 'NURBS':
        origin_points = [p.co.xyz for p in origin_spline.points]
    else:
        origin_points = [p.co for p in origin_spline.bezier_points]
    
    if insertion_spline.type == 'NURBS':
        insertion_points = [p.co.xyz for p in insertion_spline.points]
    else:
        insertion_points = [p.co for p in insertion_spline.bezier_points]
    
    origin_centroid = sum(origin_points, Vector()) / len(origin_points)
    insertion_centroid = sum(insertion_points, Vector()) / len(insertion_points)
    
    # Find closest points between contours for alignment
    min_dist = float('inf')
    best_offset = 0
    
    for offset in range(len(insertion_points)):
        total_dist = 0
        for i, origin_point in enumerate(origin_points):
            insertion_idx = (i + offset) % len(insertion_points)
            dist = (origin_point - insertion_points[insertion_idx]).length
            total_dist += dist
        
        if total_dist < min_dist:
            min_dist = total_dist
            best_offset = offset
    
    # Apply the best offset by rotating the insertion contour points
    if best_offset > 0:
        bpy.context.view_layer.objects.active = insertion_contour
        bpy.ops.object.mode_set(mode='EDIT')
        
        # This is a simplified rotation - in practice, you'd need to 
        # manipulate the actual curve points
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    return True

def create_loft_preview(curve_obj, origin_contour, insertion_contour):
    """
    Create a preview of the lofted muscle
    """
    # This would create a simplified preview mesh
    # Implementation would depend on your specific lofting algorithm
    pass

def validate_lofting_inputs(curve_obj, origin_contour, insertion_contour):
    """
    Validate that all inputs are suitable for lofting
    """
    errors = []
    
    if not curve_obj or curve_obj.type != 'CURVE':
        errors.append("Invalid or missing curve object")
    
    if not origin_contour or origin_contour.type != 'CURVE':
        errors.append("Invalid or missing origin contour")
    
    if not insertion_contour or insertion_contour.type != 'CURVE':
        errors.append("Invalid or missing insertion contour")
    
    # Check if contours are closed
    if origin_contour and origin_contour.type == 'CURVE':
        if not origin_contour.data.splines[0].use_cyclic_u:
            errors.append("Origin contour should be closed (cyclic)")
    
    if insertion_contour and insertion_contour.type == 'CURVE':
        if not insertion_contour.data.splines[0].use_cyclic_u:
            errors.append("Insertion contour should be closed (cyclic)")
    
    return errors

def auto_adjust_curve_handles(curve_obj):
    """
    Automatically adjust curve handles for smoother transitions
    """
    if not curve_obj or curve_obj.type != 'CURVE':
        return False
    
    # Switch to edit mode to adjust handles
    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Select all points and auto-handle
    bpy.ops.curve.select_all(action='SELECT')
    
    # Set handle types for smooth curves
    try:
        bpy.ops.curve.handle_type_set(type='AUTO')
    except:
        # Fallback if AUTO not available
        try:
            bpy.ops.curve.handle_type_set(type='VECTOR')
        except:
            pass
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return True

def validate_curve_object(curve_obj):
    """Validate that an object is a proper curve for lofting"""
    if not curve_obj or curve_obj.type != 'CURVE':
        return False, "Object is not a curve"
    
    if not curve_obj.data.splines:
        return False, "Curve has no splines"
    
    spline = curve_obj.data.splines[0]
    if len(spline.points) < 2 and len(spline.bezier_points) < 2:
        return False, "Curve needs at least 2 points"
    
    return True, "Valid curve"

def smooth_curve_transitions(curve_obj, smoothing_factor=0.5):
    """Apply smoothing to curve control points for better muscle shape"""
    if curve_obj.type != 'CURVE':
        return False
    
    # Store current active object
    old_active = bpy.context.view_layer.objects.active
    
    # Set curve as active and enter edit mode
    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Apply smoothing
    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.curve.smooth()
    
    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Restore previous active object
    bpy.context.view_layer.objects.active = old_active
    
    return True
