"""
Curve and Lofting Utilities
Enhanced utilities for curve manipulation and lofting operations
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
import mathutils
import math

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

def calculate_diameter_scale_factor(t, base_diameter, variation, curve_type='smooth'):
    """
    Calculate diameter scale factor along the curve
    
    Args:
        t: Parameter along curve (0.0 to 1.0)
        base_diameter: Base diameter scale
        variation: Amount of variation (0.0 to 1.0)
        curve_type: Type of variation curve ('smooth', 'muscle', 'tapering')
    
    Returns:
        Scale factor for diameter at position t
    """
    if variation <= 0.0:
        return base_diameter
    
    if curve_type == 'smooth':
        # Smooth sinusoidal variation - fuller in the middle
        scale_factor = 1.0 + variation * math.sin(math.pi * t)
        
    elif curve_type == 'muscle':
        # Muscle-like profile - wider in middle, tapering at ends
        # Uses a combination of quadratic and sine functions
        middle_boost = 1.0 + variation * (1.0 - 4.0 * (t - 0.5)**2)
        taper_factor = 1.0 - 0.3 * variation * (abs(t - 0.5) * 2.0)**2
        scale_factor = middle_boost * taper_factor
        
    elif curve_type == 'tapering':
        # Linear tapering from origin to insertion
        scale_factor = 1.0 + variation * (1.0 - t)
        
    else:  # default to smooth
        scale_factor = 1.0 + variation * math.sin(math.pi * t)
    
    return base_diameter * max(0.1, scale_factor)  # Prevent negative or zero scaling

def calculate_curve_frame(curve_points, index):
    """
    Calculate a proper coordinate frame at a point along the curve
    This helps maintain proper orientation and prevents twisting
    
    Args:
        curve_points: List of Vector points along the curve
        index: Index of current point
    
    Returns:
        tuple: (tangent, normal, binormal) vectors forming an orthonormal frame
    """
    if len(curve_points) < 2:
        return Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    
    # Calculate tangent vector
    if index == 0:
        # At start, use forward difference
        tangent = (curve_points[1] - curve_points[0]).normalized()
    elif index == len(curve_points) - 1:
        # At end, use backward difference
        tangent = (curve_points[-1] - curve_points[-2]).normalized()
    else:
        # In middle, use central difference for smoother results
        tangent = (curve_points[index + 1] - curve_points[index - 1]).normalized()
    
    # Choose an arbitrary up vector that's not parallel to tangent
    up = Vector((0, 0, 1))
    if abs(tangent.dot(up)) > 0.9:  # If tangent is nearly vertical
        up = Vector((1, 0, 0))
    
    # Calculate normal and binormal using Gram-Schmidt orthogonalization
    normal = (up - up.dot(tangent) * tangent).normalized()
    binormal = tangent.cross(normal).normalized()
    
    return tangent, normal, binormal

def apply_diameter_scaling_to_contour(contour_vertices, scale_factor, center_point, tangent, normal, binormal):
    """
    Apply diameter scaling to a contour loop with proper orientation
    
    Args:
        contour_vertices: List of vertex positions
        scale_factor: Diameter scale factor
        center_point: Center point of the contour
        tangent: Tangent vector at this position
        normal: Normal vector for the frame
        binormal: Binormal vector for the frame
    
    Returns:
        List of scaled vertex positions
    """
    if not contour_vertices or scale_factor <= 0:
        return contour_vertices
    
    scaled_vertices = []
    
    for vertex in contour_vertices:
        # Vector from center to vertex
        offset_vector = vertex - center_point
        
        # Project offset onto the normal plane (perpendicular to tangent)
        # This removes any component along the curve direction
        projected_offset = offset_vector - offset_vector.dot(tangent) * tangent
        
        # Scale the projected offset
        scaled_offset = projected_offset * scale_factor
        
        # Add back to center point
        scaled_vertex = center_point + scaled_offset
        scaled_vertices.append(scaled_vertex)
    
    return scaled_vertices

def create_oriented_contour_loop(base_contour, target_center, tangent, normal, binormal, scale_factor=1.0):
    """
    Create a properly oriented contour loop at a specific position along the curve
    
    Args:
        base_contour: Original contour vertices
        target_center: Target center position
        tangent: Tangent vector at target position
        normal: Normal vector for orientation
        binormal: Binormal vector for orientation
        scale_factor: Diameter scale factor
    
    Returns:
        List of positioned and scaled vertices
    """
    if not base_contour:
        return []
    
    # Calculate the centroid of the base contour
    base_center = sum(base_contour, Vector()) / len(base_contour)
    
    oriented_vertices = []
    
    for vertex in base_contour:
        # Get offset from original center
        offset = vertex - base_center
        
        # We assume the original contour is roughly in the XY plane
        # Transform it to be oriented according to our frame
        
        # Scale the offset
        scaled_offset = offset * scale_factor
        
        # For proper orientation, we'd need to know the original contour's
        # orientation, but for simplicity, we'll scale it uniformly
        # and position it at the target center
        
        new_vertex = target_center + scaled_offset
        oriented_vertices.append(new_vertex)
    
    return oriented_vertices

def smooth_diameter_transition(curve_points, base_diameter, variation, curve_type='muscle'):
    """
    Calculate smooth diameter values along a curve path
    
    Args:
        curve_points: List of points along the curve
        base_diameter: Base diameter scale
        variation: Amount of diameter variation
        curve_type: Type of variation profile
    
    Returns:
        List of diameter scale factors for each point
    """
    diameter_scales = []
    
    for i, point in enumerate(curve_points):
        t = i / (len(curve_points) - 1) if len(curve_points) > 1 else 0.0
        scale = calculate_diameter_scale_factor(t, base_diameter, variation, curve_type)
        diameter_scales.append(scale)
    
    return diameter_scales

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
