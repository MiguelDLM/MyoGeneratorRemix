"""
Curve and Lofting Utilities with Spline-based Diameter Control
Enhanced utilities for curve manipulation and lofting operations using curve point properties
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
import mathutils
import math

def get_spline_diameter_at_parameter(curve_obj, t):
    """
    Get diameter scale based on curve point radius at parameter t (optimized for Bezier)
    
    Args:
        curve_obj: Curve object with control points
        t: Parameter along curve (0.0 to 1.0)
    
    Returns:
        Float: Diameter scale factor based on curve point radius
    """
    if not curve_obj or curve_obj.type != 'CURVE' or not curve_obj.data.splines:
        return 1.0
    
    spline = curve_obj.data.splines[0]
    
    if spline.type == 'BEZIER':
        # For Bezier curves, use the radius property
        points = spline.bezier_points
        if len(points) < 2:
            return 1.0
        
        # Find the segment and local parameter
        segment_length = 1.0 / (len(points) - 1)
        segment_index = min(int(t / segment_length), len(points) - 2)
        local_t = (t - segment_index * segment_length) / segment_length if segment_length > 0 else 0.0
        
        # Get radius values from Bezier points
        radius1 = points[segment_index].radius
        radius2 = points[segment_index + 1].radius
        
        # Smooth interpolation between radii
        interpolated_radius = radius1 * (1.0 - local_t) + radius2 * local_t
        
        return max(0.1, interpolated_radius)
        
    elif spline.type in ['NURBS', 'POLY']:
        points = spline.points
        if len(points) < 2:
            return 1.0
        
        # Find the segment and local parameter
        segment_length = 1.0 / (len(points) - 1)
        segment_index = min(int(t / segment_length), len(points) - 2)
        local_t = (t - segment_index * segment_length) / segment_length if segment_length > 0 else 0.0
        
        # Get weights from the curve points (4th component is weight)
        weight1 = points[segment_index].co[3] if len(points[segment_index].co) > 3 else 1.0
        weight2 = points[segment_index + 1].co[3] if len(points[segment_index + 1].co) > 3 else 1.0
        
        # Interpolate between weights
        interpolated_weight = weight1 * (1.0 - local_t) + weight2 * local_t
        
        # Convert weight to diameter scale
        return max(0.1, interpolated_weight)
    
    return 1.0

def calculate_frenet_frame(curve_points, index, smoothing=0.5):
    """
    Calculate Frenet frame (tangent, normal, binormal) at curve point
    This provides proper orientation for lofting without twisting
    
    Args:
        curve_points: List of curve points
        index: Current point index
        smoothing: Smoothing factor for frame calculation
    
    Returns:
        tuple: (tangent, normal, binormal) vectors
    """
    if len(curve_points) < 2:
        return Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    
    # Calculate tangent vector
    if index == 0:
        tangent = (curve_points[1] - curve_points[0]).normalized()
    elif index == len(curve_points) - 1:
        tangent = (curve_points[-1] - curve_points[-2]).normalized()
    else:
        # Use smoothed central difference
        forward_diff = curve_points[index + 1] - curve_points[index]
        backward_diff = curve_points[index] - curve_points[index - 1]
        tangent = (forward_diff + backward_diff).normalized()
    
    # Calculate curvature vector for better normal calculation
    if len(curve_points) >= 3:
        if index == 0:
            p0, p1, p2 = curve_points[0], curve_points[1], curve_points[2]
        elif index == len(curve_points) - 1:
            p0, p1, p2 = curve_points[-3], curve_points[-2], curve_points[-1]
        else:
            p0, p1, p2 = curve_points[index-1], curve_points[index], curve_points[index+1]
        
        # Calculate second derivative (curvature direction)
        second_deriv = p2 - 2*p1 + p0
        
        if second_deriv.length > 1e-6:
            # Use curvature direction as normal
            normal_direction = second_deriv.normalized()
            # Make sure it's perpendicular to tangent
            normal = (normal_direction - normal_direction.dot(tangent) * tangent).normalized()
        else:
            # Fallback for straight sections
            normal = get_fallback_normal(tangent)
    else:
        # Simple case for short curves
        normal = get_fallback_normal(tangent)
    
    # Calculate binormal
    binormal = tangent.cross(normal).normalized()
    
    # Apply smoothing if requested
    if smoothing > 0.0 and index > 0 and hasattr(calculate_frenet_frame, 'prev_normal'):
        # Smooth normal transition to reduce twisting
        prev_normal = calculate_frenet_frame.prev_normal
        dot_product = normal.dot(prev_normal)
        
        # If normals are pointing in very different directions, apply smoothing
        if dot_product < 0.5:
            normal = (normal * (1.0 - smoothing) + prev_normal * smoothing).normalized()
            binormal = tangent.cross(normal).normalized()
    
    # Store for next iteration
    calculate_frenet_frame.prev_normal = normal
    
    return tangent, normal, binormal

def apply_spline_based_scaling(contour_vertices, center_point, diameter_scale, tangent, normal, binormal):
    """
    Apply spline-based diameter scaling to contour vertices
    
    Args:
        contour_vertices: Original contour vertices
        center_point: Center point of the cross-section
        diameter_scale: Scale factor from spline
        tangent: Tangent vector at this position
        normal: Normal vector for frame
        binormal: Binormal vector for frame
    
    Returns:
        List of scaled and oriented vertices
    """
    if not contour_vertices or diameter_scale <= 0:
        return contour_vertices
    
    scaled_vertices = []
    
    for vertex in contour_vertices:
        # Vector from center to vertex
        offset = vertex - center_point
        
        # Project offset onto the normal plane (remove tangent component)
        tangent_component = offset.dot(tangent) * tangent
        radial_offset = offset - tangent_component
        
        # Scale the radial component
        scaled_radial = radial_offset * diameter_scale
        
        # Reconstruct position
        new_vertex = center_point + scaled_radial + tangent_component
        scaled_vertices.append(new_vertex)
    
    return scaled_vertices

def smooth_diameter_transitions(diameter_values, smoothing_factor=0.5):
    """
    Smooth diameter transitions to avoid abrupt changes
    
    Args:
        diameter_values: List of diameter scale values
        smoothing_factor: Amount of smoothing (0.0 = none, 1.0 = maximum)
    
    Returns:
        List of smoothed diameter values
    """
    if len(diameter_values) <= 2 or smoothing_factor <= 0:
        return diameter_values
    
    smoothed = diameter_values.copy()
    
    # Apply smoothing passes
    passes = max(1, int(smoothing_factor * 5))
    
    for _ in range(passes):
        new_smoothed = smoothed.copy()
        for i in range(1, len(smoothed) - 1):
            # Average with neighbors
            neighbor_avg = (smoothed[i-1] + smoothed[i+1]) / 2.0
            blend_factor = smoothing_factor * 0.3  # Gentle blending
            new_smoothed[i] = smoothed[i] * (1.0 - blend_factor) + neighbor_avg * blend_factor
        smoothed = new_smoothed
    
    return smoothed

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

def get_fallback_normal(tangent):
    """Get a fallback normal vector when curvature calculation fails"""
    # Choose the most perpendicular world axis
    abs_tangent = Vector((abs(tangent.x), abs(tangent.y), abs(tangent.z)))
    
    if abs_tangent.z < abs_tangent.x and abs_tangent.z < abs_tangent.y:
        up = Vector((0, 0, 1))
    elif abs_tangent.y < abs_tangent.x:
        up = Vector((0, 1, 0))
    else:
        up = Vector((1, 0, 0))
    
    # Make perpendicular to tangent
    normal = (up - up.dot(tangent) * tangent)
    if normal.length > 1e-6:
        return normal.normalized()
    else:
        # Ultimate fallback
        return Vector((0, 1, 0)) if abs(tangent.y) < 0.9 else Vector((1, 0, 0))

def ensure_proper_curve_radius_setup(curve_obj):
    """Ensure the curve has proper radius setup for muscle-like diameter control"""
    if not curve_obj or curve_obj.type != 'CURVE':
        return False
    
    spline_data = curve_obj.data.splines
    if not spline_data:
        return False
    
    for spline in spline_data:
        if spline.type == 'BEZIER':
            points = spline.bezier_points
            num_points = len(points)
            
            if num_points < 2:
                continue
            
            # Only set default values if all radii are 1.0 (default)
            all_default = all(abs(point.radius - 1.0) < 0.01 for point in points)
            
            if all_default:
                for i, point in enumerate(points):
                    # Set muscle-like radius distribution
                    if i == 0 or i == num_points - 1:
                        point.radius = 0.8  # Tapered ends
                    elif i == num_points // 2:
                        point.radius = 1.4  # Thick middle
                    else:
                        # Gradual transition
                        distance_from_center = abs(i - num_points // 2)
                        max_distance = num_points // 2
                        point.radius = 1.4 - (distance_from_center / max_distance) * 0.6
    
    # Update curve data
    curve_obj.data.update_tag()
    return True

def debug_curve_weights(curve_obj):
    """Debug function to print curve point weights/radius values"""
    if not curve_obj or curve_obj.type != 'CURVE':
        print("Invalid curve object")
        return
    
    print(f"Debug curve weights for: {curve_obj.name}")
    
    for spline_idx, spline in enumerate(curve_obj.data.splines):
        print(f"  Spline {spline_idx} (type: {spline.type}):")
        
        if spline.type == 'BEZIER':
            for i, point in enumerate(spline.bezier_points):
                print(f"    Point {i}: pos={point.co}, radius={point.radius}")
        elif spline.type in ['NURBS', 'POLY']:
            for i, point in enumerate(spline.points):
                weight = point.co[3] if len(point.co) > 3 else 1.0
                print(f"    Point {i}: pos={point.co[:3]}, weight={weight}")
