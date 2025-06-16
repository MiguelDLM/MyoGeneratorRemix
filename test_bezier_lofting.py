"""
Test script for Bezier-based muscle lofting system
This script tests the Bridge Edge Loops-like algorithm implementation
"""

import bpy
import bmesh
from mathutils import Vector

def test_bezier_lofting():
    """Test the new Bezier lofting system"""
    
    # Clear existing mesh objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Create a test Bezier curve
    bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0))
    curve_obj = bpy.context.active_object
    curve_obj.name = "test_curve"
    
    # Modify the curve to create a more pronounced curve
    bpy.ops.object.mode_set(mode='EDIT')
    spline = curve_obj.data.splines[0]
    
    # Set up curve points for testing
    spline.bezier_points[0].co = Vector((0, 0, 0))
    spline.bezier_points[0].handle_right = Vector((1, 0, 0))
    spline.bezier_points[0].radius = 0.8
    
    spline.bezier_points[1].co = Vector((3, 2, 1))
    spline.bezier_points[1].handle_left = Vector((2, 2, 1))
    spline.bezier_points[1].radius = 1.5
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Create test contour circles
    bpy.ops.mesh.primitive_circle_add(radius=1, location=(-1, -1, 0))
    origin_contour = bpy.context.active_object
    origin_contour.name = "origin_contour"
    
    bpy.ops.mesh.primitive_circle_add(radius=0.8, location=(4, 3, 1))
    insertion_contour = bpy.context.active_object
    insertion_contour.name = "insertion_contour"
    
    # Convert to curves for testing
    bpy.context.view_layer.objects.active = origin_contour
    bpy.ops.object.convert(target='CURVE')
    
    bpy.context.view_layer.objects.active = insertion_contour
    bpy.ops.object.convert(target='CURVE')
    
    print("Test setup completed. You can now test the Bridge Edge Loops-like algorithm.")
    print("Objects created:")
    print("- test_curve (Bezier curve with pronounced curvature)")
    print("- origin_contour (circle curve at origin)")
    print("- insertion_contour (circle curve at insertion)")
    print("")
    print("Expected behavior:")
    print("- No face inversion in curved sections")
    print("- Consistent mesh flow along curve")
    print("- Proper radius scaling based on Bezier point radius")

if __name__ == "__main__":
    test_bezier_lofting()
