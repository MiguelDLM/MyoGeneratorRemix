"""Path-curve helpers for the muscle loft: validation, smoothing, Bezier
sampling and twist-free orientation frames along the path.
"""

import math

import bpy
from mathutils import Vector


def validate_curve_object(curve_obj):
    """Check that an object can be used as a muscle path.

    :arg curve_obj: Candidate object.
    :type curve_obj: :class:`bpy.types.Object`
    :return: ``(is_valid, message)``.
    :rtype: tuple of (bool, str)
    """
    if not curve_obj or curve_obj.type != 'CURVE':
        return False, "Object is not a curve"
    
    if not curve_obj.data.splines:
        return False, "Curve has no splines"
    
    spline = curve_obj.data.splines[0]
    if len(spline.points) < 2 and len(spline.bezier_points) < 2:
        return False, "Curve needs at least 2 points"
    
    return True, "Valid curve"

def smooth_curve_transitions(curve_obj, smoothing_factor=0.5):
    """Smooth the control points of a path curve (moves interior points towards
    the average of their neighbours).

    :arg curve_obj: Muscle path curve (modified in place).
    :type curve_obj: :class:`bpy.types.Object`
    :arg smoothing_factor: Blend towards the neighbour average (0-1).
    :type smoothing_factor: float
    :return: True if the curve was smoothed.
    :rtype: bool
    """
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

def get_bezier_point_at_parameter(curve_obj, t):
    """Position, tangent and radius on the evaluated Bezier path (not on the
    straight lines between control points).

    :arg curve_obj: Muscle path curve (first spline, Bezier).
    :type curve_obj: :class:`bpy.types.Object`
    :arg t: Parameter along the curve, 0 (origin) to 1 (insertion).
    :type t: float

    :return: ``(position, tangent, radius)`` in world space; a default frame for
       invalid curves.
    :rtype: tuple of (:class:`mathutils.Vector`, :class:`mathutils.Vector`, float)
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

def calculate_consistent_orientation_frame(curve_obj, t):
    """Twist-free frame along the path by parallel transport.

    Keeps the normal orientation consistent along the whole curve, which
    prevents mesh inversion in sharp bends. The transported frame is cached on
    the function between calls; call :func:`reset_orientation_frame` before each
    new loft.

    :arg curve_obj: Muscle path curve (first spline, Bezier).
    :type curve_obj: :class:`bpy.types.Object`
    :arg t: Parameter along the curve, 0 (origin) to 1 (insertion).
    :type t: float

    :return: ``(tangent, normal, binormal, radius)``.
    :rtype: tuple
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
    """Transport a normal/binormal pair from one tangent to the next
    (rotation-minimising "Bishop" frame).

    :arg prev_tangent: Tangent at the previous sample.
    :type prev_tangent: :class:`mathutils.Vector`
    :arg curr_tangent: Tangent at the current sample.
    :type curr_tangent: :class:`mathutils.Vector`
    :arg prev_normal: Normal at the previous sample.
    :type prev_normal: :class:`mathutils.Vector`
    :arg prev_binormal: Binormal at the previous sample.
    :type prev_binormal: :class:`mathutils.Vector`
    :return: ``(normal, binormal)`` at the current sample.
    :rtype: tuple of :class:`mathutils.Vector`
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
    """Clear the cached frame of :func:`calculate_consistent_orientation_frame` (call before each new loft)."""
    if hasattr(calculate_consistent_orientation_frame, 'transport_frame'):
        delattr(calculate_consistent_orientation_frame, 'transport_frame')

def calculate_frenet_frame_from_bezier(curve_obj, t, smoothing=0.5):
    # Get tangent from Bezier handles
    """Frenet-like frame from the Bezier tangent, used to seed the parallel transport.

    :arg curve_obj: Muscle path curve (first spline, Bezier).
    :type curve_obj: :class:`bpy.types.Object`
    :arg t: Parameter along the curve, 0 (origin) to 1 (insertion).
    :type t: float
    :arg smoothing: Blend factor for the normal estimate.
    :type smoothing: float
    :return: ``(tangent, normal, binormal)``.
    :rtype: tuple of :class:`mathutils.Vector`
    """
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

def get_bezier_tangent_at_parameter(curve_obj, t):
    """Unit tangent of the Bezier path (see :func:`get_bezier_point_at_parameter`).

    :arg curve_obj: Muscle path curve (first spline, Bezier).
    :type curve_obj: :class:`bpy.types.Object`
    :arg t: Parameter along the curve, 0 (origin) to 1 (insertion).
    :type t: float
    :rtype: :class:`mathutils.Vector`
    """
    position, tangent, radius = get_bezier_point_at_parameter(curve_obj, t)
    return tangent

def verify_frame_consistency(tangent, normal, binormal, prev_normal=None, prev_binormal=None):
    """Re-orthogonalise a frame and flip it if it inverted relative to the previous one.

    :arg tangent: Current tangent.
    :type tangent: :class:`mathutils.Vector`
    :arg normal: Current normal.
    :type normal: :class:`mathutils.Vector`
    :arg binormal: Current binormal.
    :type binormal: :class:`mathutils.Vector`
    :arg prev_normal: Previous normal, or None.
    :type prev_normal: :class:`mathutils.Vector`
    :arg prev_binormal: Previous binormal, or None.
    :type prev_binormal: :class:`mathutils.Vector`
    :return: ``(normal, binormal)`` corrected.
    :rtype: tuple of :class:`mathutils.Vector`
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
    """Sample the path and report frame inversions to the console (diagnostic).

    :arg curve_obj: Muscle path curve.
    :type curve_obj: :class:`bpy.types.Object`
    :arg num_samples: Number of samples along the curve.
    :type num_samples: int
    :return: Whether the curve needs special inversion handling (currently always False).
    :rtype: bool
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
