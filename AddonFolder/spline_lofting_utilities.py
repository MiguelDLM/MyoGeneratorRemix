"""
Curve and Lofting Utilities with Spline-based Diameter Control
Enhanced utilities for curve manipulation and lofting operations using curve point properties
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
import mathutils
import math

def get_bezier_point_at_parameter(curve_obj, t):
    """
    Get position and tangent from Bezier curve at parameter t using proper interpolation
    This ensures we follow the actual curve path, not just control points
    
    Args:
        curve_obj: Bezier curve object
        t: Parameter along curve (0.0 to 1.0)
    
    Returns:
        tuple: (position Vector, tangent Vector, radius float)
    """
    if not curve_obj or curve_obj.type != 'CURVE' or not curve_obj.data.splines:
        return Vector((0, 0, 0)), Vector((1, 0, 0)), 1.0
    
    spline = curve_obj.data.splines[0]
    
    if spline.type == 'BEZIER':
        points = spline.bezier_points
        if len(points) < 2:
            return Vector((0, 0, 0)), Vector((1, 0, 0)), 1.0
        
        # Find the segment and local parameter
        segment_length = 1.0 / (len(points) - 1)
        segment_index = min(int(t / segment_length), len(points) - 2)
        local_t = (t - segment_index * segment_length) / segment_length if segment_length > 0 else 0.0
        
        # Get Bezier control points for this segment (in local coordinates)
        p0 = points[segment_index].co
        p1 = points[segment_index].handle_right
        p2 = points[segment_index + 1].handle_left
        p3 = points[segment_index + 1].co
        
        # Get radius values
        r0 = points[segment_index].radius
        r1 = points[segment_index + 1].radius
        
        # Cubic Bezier position interpolation (in local coordinates)
        t_inv = 1.0 - local_t
        t2 = local_t * local_t
        t3 = t2 * local_t
        t_inv2 = t_inv * t_inv
        t_inv3 = t_inv2 * t_inv
        
        local_position = (t_inv3 * p0 + 
                         3.0 * t_inv2 * local_t * p1 + 
                         3.0 * t_inv * t2 * p2 + 
                         t3 * p3)
        
        # Transform from local curve coordinates to world coordinates
        world_position = curve_obj.matrix_world @ local_position
        
        # Cubic Bezier tangent (derivative) in local coordinates
        local_tangent = (3.0 * t_inv2 * (p1 - p0) + 
                        6.0 * t_inv * local_t * (p2 - p1) + 
                        3.0 * t2 * (p3 - p2))
        
        # Transform tangent to world coordinates (no translation, only rotation/scale)
        world_tangent = curve_obj.matrix_world.to_3x3() @ local_tangent
        
        if world_tangent.length > 0:
            world_tangent = world_tangent.normalized()
        else:
            # Fallback tangent
            fallback_tangent = curve_obj.matrix_world.to_3x3() @ (p3 - p0)
            world_tangent = fallback_tangent.normalized() if fallback_tangent.length > 0 else Vector((1, 0, 0))
        
        # Interpolate radius using control point radius values
        # Interpolate radius using control point radius values
        radius = r0 * (1.0 - local_t) + r1 * local_t

        # Additional scaling based on handle length to allow "inflating" the
        # mesh by simply adjusting handle size in the UI.  Longer handles will
        # create a thicker cross section while shorter ones constrict it.
        seg_len = (p3 - p0).length
        if seg_len > 0:
            h0 = (p1 - p0).length / seg_len
            h1 = (p3 - p2).length / seg_len
            handle_ratio = (h0 * (1.0 - local_t) + h1 * local_t)
        else:
            handle_ratio = 0.0

        # Limit influence to avoid excessively large diameters
        handle_ratio = max(0.0, min(handle_ratio, 2.0))
        radius *= 1.0 + handle_ratio * 0.5

        return world_position, world_tangent, max(0.1, radius)
    
    return Vector((0, 0, 0)), Vector((1, 0, 0)), 1.0
    """
    Get the tangent vector from Bezier curve at parameter t using handle information
    This provides proper orientation control for lofting
    
    Args:
        curve_obj: Bezier curve object
        t: Parameter along curve (0.0 to 1.0)
    
    Returns:
        Vector: Normalized tangent vector based on Bezier handles
    """
    if not curve_obj or curve_obj.type != 'CURVE' or not curve_obj.data.splines:
        return Vector((1, 0, 0))
    
    spline = curve_obj.data.splines[0]
    
    if spline.type == 'BEZIER':
        points = spline.bezier_points
        if len(points) < 2:
            return Vector((1, 0, 0))
        
        # Find the segment and local parameter
        segment_length = 1.0 / (len(points) - 1)
        segment_index = min(int(t / segment_length), len(points) - 2)
        local_t = (t - segment_index * segment_length) / segment_length if segment_length > 0 else 0.0
        
        # Get Bezier control points for this segment
        p0 = points[segment_index].co
        p1 = points[segment_index].handle_right
        p2 = points[segment_index + 1].handle_left
        p3 = points[segment_index + 1].co
        
        # Calculate tangent using Bezier curve derivative
        # Derivative of cubic Bezier: 3(1-t)²(P1-P0) + 6(1-t)t(P2-P1) + 3t²(P3-P2)
        t_inv = 1.0 - local_t
        
        tangent = (3.0 * t_inv * t_inv * (p1 - p0) + 
                  6.0 * t_inv * local_t * (p2 - p1) + 
                  3.0 * local_t * local_t * (p3 - p2))
        
        if tangent.length > 0:
            return tangent.normalized()
        else:
            # Fallback to simple direction
            return (p3 - p0).normalized()
    
    return Vector((1, 0, 0))

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

def calculate_consistent_orientation_frame(curve_obj, t):
    """
    Calculate consistent orientation frame using parallel transport
    This prevents mesh inversion in sharp curves (>180°) by maintaining
    consistent normal orientation throughout the entire curve
    
    Args:
        curve_obj: Bezier curve object
        t: Parameter along curve (0.0 to 1.0)
    
    Returns:
        tuple: (tangent, normal, binormal, radius) vectors
    """
    # Get position and tangent from Bezier curve
    position, tangent, radius = get_bezier_point_at_parameter(curve_obj, t)
    
    # Initialize parallel transport frame on first call
    if not hasattr(calculate_consistent_orientation_frame, 'transport_frame'):
        # Initialize reference frame using most stable approach
        # Find the axis most perpendicular to initial tangent for better stability
        
        candidate_axes = [
            Vector((1, 0, 0)),  # X axis
            Vector((0, 1, 0)),  # Y axis  
            Vector((0, 0, 1))   # Z axis
        ]
        
        # Choose the axis most perpendicular to tangent
        best_axis = None
        min_dot = float('inf')
        
        for axis in candidate_axes:
            dot_val = abs(tangent.dot(axis))
            if dot_val < min_dot:
                min_dot = dot_val
                best_axis = axis
        
        # Create initial normal by projecting chosen axis onto plane perpendicular to tangent
        initial_normal = best_axis - best_axis.dot(tangent) * tangent
        if initial_normal.length > 1e-6:
            initial_normal = initial_normal.normalized()
        else:
            # Emergency fallback - create arbitrary perpendicular vector
            if abs(tangent.z) < 0.9:
                initial_normal = Vector((0, 0, 1)) - Vector((0, 0, 1)).dot(tangent) * tangent
            else:
                initial_normal = Vector((1, 0, 0)) - Vector((1, 0, 0)).dot(tangent) * tangent
            initial_normal = initial_normal.normalized()
        
        # Create initial binormal using right-handed coordinate system
        initial_binormal = tangent.cross(initial_normal).normalized()
        
        # Store initial frame
        calculate_consistent_orientation_frame.transport_frame = {
            'normal': initial_normal,
            'binormal': initial_binormal,
            'prev_tangent': tangent
        }
        
        normal = initial_normal
        binormal = initial_binormal
    else:
        # Apply parallel transport algorithm
        frame = calculate_consistent_orientation_frame.transport_frame
        prev_tangent = frame['prev_tangent']
        prev_normal = frame['normal']
        prev_binormal = frame['binormal']
        
        # Calculate parallel transport of the frame
        normal, binormal = parallel_transport_frame(
            prev_tangent, tangent, prev_normal, prev_binormal
        )
        
        # Verify frame consistency and correct any inversions
        normal, binormal = verify_frame_consistency(
            tangent, normal, binormal, prev_normal, prev_binormal
        )
        
        # Update stored frame
        frame['normal'] = normal
        frame['binormal'] = binormal
        frame['prev_tangent'] = tangent
    
    return tangent, normal, binormal, radius


def parallel_transport_frame(prev_tangent, curr_tangent, prev_normal, prev_binormal):
    """
    Improved parallel transport using rotation minimizing frame (Bishop frame)
    This method is more robust for sharp curves and prevents face inversion
    
    Args:
        prev_tangent: Previous tangent vector
        curr_tangent: Current tangent vector  
        prev_normal: Previous normal vector
        prev_binormal: Previous binormal vector
    
    Returns:
        tuple: (normal, binormal) vectors transported to current position
    """
    # Normalize input vectors
    prev_tangent = prev_tangent.normalized()
    curr_tangent = curr_tangent.normalized()
    prev_normal = prev_normal.normalized()
    prev_binormal = prev_binormal.normalized()
    
    # Use quaternion rotation based on tangent difference for a robust
    # rotation-minimizing frame. This handles very sharp bends without
    # introducing flips or concave artifacts.

    # Rotation that aligns previous tangent with current tangent
    rot_quat = prev_tangent.rotation_difference(curr_tangent)
    new_normal = (rot_quat @ prev_normal).normalized()
    new_binormal = (rot_quat @ prev_binormal).normalized()
    # Use quaternion rotation based on tangent difference for a robust
    # rotation-minimizing frame. This handles very sharp bends without
    # introducing flips or concave artifacts.

    # Rotation that aligns previous tangent with current tangent
    rot_quat = prev_tangent.rotation_difference(curr_tangent)
    new_normal = (rot_quat @ prev_normal).normalized()
    new_binormal = (rot_quat @ prev_binormal).normalized()
    
    # Ensure the frame is orthogonal to current tangent using Gram-Schmidt
    # Project out any component along the current tangent
    new_normal = new_normal - new_normal.dot(curr_tangent) * curr_tangent
    new_binormal = new_binormal - new_binormal.dot(curr_tangent) * curr_tangent
    
    # Normalize the vectors
    if new_normal.length > 1e-6:
        new_normal = new_normal.normalized()
    else:
        # Emergency fallback: create new normal perpendicular to tangent
        if abs(curr_tangent.z) < 0.9:
            new_normal = Vector((0, 0, 1))
        else:
            new_normal = Vector((1, 0, 0))
        new_normal = new_normal - new_normal.dot(curr_tangent) * curr_tangent
        new_normal = new_normal.normalized()
    
    if new_binormal.length > 1e-6:
        new_binormal = new_binormal.normalized()
    else:
        # Regenerate binormal as tangent × normal
        new_binormal = curr_tangent.cross(new_normal).normalized()
    
    # Final orthogonalization: ensure normal ⊥ tangent and binormal = tangent × normal
    new_normal = new_normal - new_normal.dot(curr_tangent) * curr_tangent
    new_normal = new_normal.normalized()
    new_binormal = curr_tangent.cross(new_normal).normalized()
    
    # Verify the frame is right-handed
    if new_binormal.dot(prev_binormal) < 0:
        new_binormal = -new_binormal
    
    return new_normal, new_binormal


def reset_orientation_frame():
    """
    Reset the parallel transport frame state for new lofting operations
    Call this before starting a new mesh generation to ensure clean frame state
    """
    if hasattr(calculate_consistent_orientation_frame, 'transport_frame'):
        delattr(calculate_consistent_orientation_frame, 'transport_frame')


def calculate_frenet_frame_from_bezier(curve_obj, t, smoothing=0.5):
    # Get tangent from Bezier handles
    tangent = get_bezier_tangent_at_parameter(curve_obj, t)
    
    # Calculate normal using minimal rotation frame
    # This method prevents flipping in curved sections
    if not hasattr(calculate_frenet_frame_from_bezier, 'reference_normal'):
        # Initialize reference normal
        up = Vector((0, 0, 1))
        if abs(tangent.dot(up)) > 0.9:
            up = Vector((1, 0, 0))
        normal = (up - up.dot(tangent) * tangent).normalized()
        calculate_frenet_frame_from_bezier.reference_normal = normal
    else:
        # Use previous normal as reference to maintain consistency
        prev_normal = calculate_frenet_frame_from_bezier.reference_normal
        
        # Project previous normal onto plane perpendicular to tangent
        normal = (prev_normal - prev_normal.dot(tangent) * tangent)
        
        if normal.length < 0.1:
            # Fallback if normal becomes too small
            up = Vector((0, 0, 1))
            if abs(tangent.dot(up)) > 0.9:
                up = Vector((1, 0, 0))
            normal = (up - up.dot(tangent) * tangent).normalized()
        else:
            normal = normal.normalized()
    
    # Calculate binormal
    binormal = tangent.cross(normal).normalized()
    
    # Apply smoothing to reduce sudden orientation changes
    if smoothing > 0.0 and hasattr(calculate_frenet_frame_from_bezier, 'prev_frame'):
        prev_tangent, prev_normal, prev_binormal = calculate_frenet_frame_from_bezier.prev_frame
        
        # Smooth interpolation
        blend = smoothing * 0.3
        normal = (normal * (1.0 - blend) + prev_normal * blend).normalized()
        binormal = tangent.cross(normal).normalized()
    
    # Store for next iteration
    calculate_frenet_frame_from_bezier.reference_normal = normal
    calculate_frenet_frame_from_bezier.prev_frame = (tangent, normal, binormal)
    
    return tangent, normal, binormal

def calculate_frenet_frame(curve_points, index, smoothing=0.5):
    """
    Calculate Frenet frame for a point along a curve (fallback method)
    
    Args:
        curve_points: List of curve points
        index: Index of current point
        smoothing: Smoothing factor
    
    Returns:
        tuple: (tangent, normal, binormal)
    """
    if len(curve_points) < 2:
        return Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    
    # Calculate tangent
    if index == 0:
        tangent = (curve_points[1] - curve_points[0]).normalized()
    elif index == len(curve_points) - 1:
        tangent = (curve_points[-1] - curve_points[-2]).normalized()
    else:
        forward_diff = curve_points[index + 1] - curve_points[index]
        backward_diff = curve_points[index] - curve_points[index - 1]
        tangent = (forward_diff + backward_diff).normalized()
    
    # Calculate normal using up vector method
    up = Vector((0, 0, 1))
    if abs(tangent.dot(up)) > 0.9:
        up = Vector((1, 0, 0))
    normal = (up - up.dot(tangent) * tangent).normalized()
    
    # Calculate binormal
    binormal = tangent.cross(normal).normalized()
    
    return tangent, normal, binormal

def create_oriented_loop_like_bridge(contour_vertices, center_point, tangent, normal, binormal, radius_scale):
    """
    Create oriented loop similar to Blender's Bridge Edge Loops algorithm
    This ensures consistent face orientation and proper scaling
    
    Args:
        contour_vertices: Original contour vertices
        center_point: Center point for this cross-section
        tangent: Tangent vector along curve
        normal: Normal vector (consistent orientation)
        binormal: Binormal vector
        radius_scale: Scale factor for radius
    
    Returns:
        List of transformed vertices
    """
    if not contour_vertices or radius_scale <= 0:
        return contour_vertices
    
    transformed_vertices = []
    
    # Calculate center of original contour
    original_center = sum(contour_vertices, Vector()) / len(contour_vertices)
    
    for vertex in contour_vertices:
        # Get vector from original center to vertex
        local_offset = vertex - original_center
        
        # Project this offset onto the normal plane (remove tangent component)
        tangent_component = local_offset.dot(tangent)
        radial_offset = local_offset - tangent_component * tangent
        
        # Scale the radial component based on radius
        scaled_radial = radial_offset * radius_scale
        
        # Transform to new coordinate system using the orientation frame
        # This ensures the loop maintains proper orientation
        new_position = center_point + scaled_radial
        
        transformed_vertices.append(new_position)
    
    return transformed_vertices
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
    
    for spline_idx, spline in enumerate(curve_obj.data.splines):
        print(f"  Spline {spline_idx} (type: {spline.type}):")
        
        if spline.type == 'BEZIER':
            for i, point in enumerate(spline.bezier_points):
                print(f"    Point {i}: pos={point.co}, radius={point.radius}")
        elif spline.type in ['NURBS', 'POLY']:
            for i, point in enumerate(spline.points):
                weight = point.co[3] if len(point.co) > 3 else 1.0
                print(f"    Point {i}: pos={point.co[:3]}, weight={weight}")

def get_bezier_tangent_at_parameter(curve_obj, t):
    """Get tangent vector from Bezier curve at parameter t (compatibility function)"""
    position, tangent, radius = get_bezier_point_at_parameter(curve_obj, t)
    return tangent

def verify_frame_consistency(tangent, normal, binormal, prev_normal=None, prev_binormal=None):
    """
    Verify that the frame is consistent and correct any inversions
    
    Args:
        tangent: Current tangent vector
        normal: Current normal vector
        binormal: Current binormal vector
        prev_normal: Previous normal for consistency check
        prev_binormal: Previous binormal for consistency check
    
    Returns:
        tuple: (corrected_normal, corrected_binormal)
    """
    # Ensure orthogonality
    normal = normal - normal.dot(tangent) * tangent
    if normal.length > 1e-6:
        normal = normal.normalized()
    else:
        # Regenerate normal if degenerate
        if abs(tangent.z) < 0.9:
            normal = Vector((0, 0, 1))
        else:
            normal = Vector((1, 0, 0))
        normal = normal - normal.dot(tangent) * tangent
        normal = normal.normalized()
    
    # Recalculate binormal to ensure right-handed system
    binormal = tangent.cross(normal).normalized()
    
    # Check consistency with previous frame if available
    if prev_normal is not None and prev_binormal is not None:
        normal_consistency = normal.dot(prev_normal)
        binormal_consistency = binormal.dot(prev_binormal)
        
        # If both have flipped, the frame has inverted
        if normal_consistency < 0 and binormal_consistency < 0:
            # Frame has flipped, correct it
            normal = -normal
            binormal = -binormal
            print("Frame inversion detected and corrected")
    
    return normal, binormal

def detect_global_inversions(curve_obj, num_samples=20):
    """
    Sample the curve at multiple points to detect global frame inversions
    and determine if special handling is needed for the curve shape
    
    Args:
        curve_obj: Bezier curve object
        num_samples: Number of points to sample for analysis
    
    Returns:
        bool: True if the curve needs special inversion handling
    """
    if not curve_obj or curve_obj.type != 'CURVE' or not curve_obj.data.splines:
        return False
    
    # Reset frame state for clean sampling
    reset_orientation_frame()
    
    # Sample tangent changes along the curve
    total_rotation = 0.0
    prev_tangent = None
    
    for i in range(num_samples):
        t = i / (num_samples - 1) if num_samples > 1 else 0.0
        
        try:
            tangent, _, _, _ = calculate_consistent_orientation_frame(curve_obj, t)
            
            if prev_tangent is not None:
                # Calculate the rotation angle between consecutive tangents
                dot_product = max(-1.0, min(1.0, prev_tangent.dot(tangent)))
                angle = math.acos(abs(dot_product))
                total_rotation += angle
            
            prev_tangent = tangent
            
        except Exception as e:
            print(f"Error sampling curve at t={t}: {e}")
            continue
    
    # Reset frame state after sampling
    reset_orientation_frame()
    
    # If total rotation is very high, the curve may need special handling
    threshold = math.pi * 1.5  # 270 degrees
    needs_special_handling = total_rotation > threshold
    

