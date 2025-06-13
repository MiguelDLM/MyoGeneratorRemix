"""
Curve and Lofting Utilities
Enhanced utilities for curve manipulation and lofting operations
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
import mathutils

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
