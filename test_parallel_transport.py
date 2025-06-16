#!/usr/bin/env python3
"""
Test script for Parallel Transport Bezier Lofting

This script tests the new parallel transport frame system that prevents
mesh inversion in sharp curves (>180°) by maintaining consistent orientation.

Run this script in Blender to test the parallel transport lofting system.
"""

import bpy
import bmesh
from mathutils import Vector
import math

def create_sharp_curve_test():
    """Create a test curve with sharp bends (>180°) to test parallel transport"""
    
    # Clear existing mesh objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Create a Bezier curve with a sharp S-curve (>180° turns)
    bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0))
    curve_obj = bpy.context.active_object
    curve_obj.name = "SharpCurve_Test"
    
    # Configure the curve for sharp bends
    curve_data = curve_obj.data
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 12
    
    # Get the spline and set up extreme curve points
    spline = curve_data.splines[0]
    
    # Add more points for a complex S-curve
    spline.bezier_points.add(2)  # Now we have 3 points total
    
    # Set up points for an extreme S-curve with >180° bends
    points_data = [
        # Point 0 - Start
        {
            'co': Vector((0, 0, 0)),
            'handle_left': Vector((-1, 0, 0)),
            'handle_right': Vector((1, 0, 0)),
            'radius': 0.5
        },
        # Point 1 - Sharp bend >180°
        {
            'co': Vector((3, 3, 1)),
            'handle_left': Vector((2, 0, 1)),
            'handle_right': Vector((4, 6, 1)),
            'radius': 1.2
        },
        # Point 2 - Another sharp bend >180°
        {
            'co': Vector((0, 6, 2)),
            'handle_left': Vector((-3, 3, 2)),
            'handle_right': Vector((1, 6, 2)),
            'radius': 0.8
        }
    ]
    
    # Apply the point data
    for i, point_data in enumerate(points_data):
        point = spline.bezier_points[i]
        point.co = point_data['co']
        point.handle_left = point_data['handle_left']
        point.handle_right = point_data['handle_right']
        point.radius = point_data['radius']
        point.handle_left_type = 'FREE'
        point.handle_right_type = 'FREE'
    
    return curve_obj

def create_test_contours():
    """Create origin and insertion contours for testing"""
    
    # Create origin contour (circle)
    bpy.ops.mesh.primitive_circle_add(
        vertices=8, 
        radius=0.8, 
        location=(0, 0, -0.5)
    )
    origin_contour = bpy.context.active_object
    origin_contour.name = "Origin_Contour_Test"
    
    # Create insertion contour (ellipse)
    bpy.ops.mesh.primitive_circle_add(
        vertices=8, 
        radius=0.6, 
        location=(0, 6, 2.5)
    )
    insertion_contour = bpy.context.active_object
    insertion_contour.name = "Insertion_Contour_Test"
    
    # Scale insertion contour to make it elliptical
    bpy.ops.transform.resize(value=(1.5, 0.7, 1))
    
    return origin_contour, insertion_contour

def test_parallel_transport_lofting():
    """Test the parallel transport lofting system"""
    
    print("=== Testing Parallel Transport Bezier Lofting ===")
    
    # Create test objects
    curve_obj = create_sharp_curve_test()
    origin_contour, insertion_contour = create_test_contours()
    
    print(f"Created test curve: {curve_obj.name}")
    print(f"Created origin contour: {origin_contour.name}")
    print(f"Created insertion contour: {insertion_contour.name}")
    
    # Test the parallel transport frame calculation
    try:
        from AddonFolder.spline_lofting_utilities import (
            reset_orientation_frame,
            calculate_consistent_orientation_frame,
            get_bezier_point_at_parameter
        )
        
        print("\nTesting parallel transport frame calculation...")
        
        # Reset frame for clean test
        reset_orientation_frame()
        
        # Test frame calculation at different curve parameters
        test_parameters = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for t in test_parameters:
            try:
                tangent, normal, binormal, radius = calculate_consistent_orientation_frame(curve_obj, t)
                position, _, _ = get_bezier_point_at_parameter(curve_obj, t)
                
                print(f"t={t:.2f}: pos={position}, radius={radius:.3f}")
                print(f"  tangent={tangent}")
                print(f"  normal={normal}")
                print(f"  binormal={binormal}")
                
                # Verify orthogonality
                dot_tn = abs(tangent.dot(normal))
                dot_tb = abs(tangent.dot(binormal))
                dot_nb = abs(normal.dot(binormal))
                
                if dot_tn > 0.01 or dot_tb > 0.01 or dot_nb > 0.01:
                    print(f"  WARNING: Frame not orthogonal! dots: {dot_tn:.3f}, {dot_tb:.3f}, {dot_nb:.3f}")
                else:
                    print(f"  ✓ Frame is orthogonal")
                    
            except Exception as e:
                print(f"  ERROR at t={t}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n✓ Parallel transport frame test completed")
        
    except ImportError as e:
        print(f"✗ Cannot import lofting utilities: {e}")
        print("Make sure the addon is properly installed and enabled")
        return False
    
    # Test mesh generation if muscle workflow is available
    try:
        from AddonFolder.improved_muscle_workflow import Muscle_Preview_Op
        
        print("\nTesting mesh generation with parallel transport...")
        
        # Set up scene properties for testing
        scene = bpy.context.scene
        if not hasattr(scene, 'muscle_contour_resolution'):
            # Create custom properties for testing
            scene.muscle_contour_resolution = 12
            scene.muscle_curve_subdivisions = 16
            
        # Create a temporary collection for testing
        test_collection = bpy.data.collections.new("ParallelTransport_Test")
        bpy.context.scene.collection.children.link(test_collection)
        
        # Link objects to test collection
        test_collection.objects.link(curve_obj)
        test_collection.objects.link(origin_contour)
        test_collection.objects.link(insertion_contour)
        
        print("✓ Test objects prepared for mesh generation")
        print("NOTE: Use the MyoGenerator addon interface to generate the mesh")
        print("The new parallel transport system should prevent mesh inversion in sharp curves")
        
    except ImportError:
        print("✗ Muscle workflow not available - testing frame calculation only")
    
    print("\n=== Test Complete ===")
    print("Check the 3D viewport for the test curve with sharp bends")
    print("The curve should demonstrate >180° angles that would cause mesh inversion")
    print("with the old system but should work correctly with parallel transport")
    
    return True

if __name__ == "__main__":
    test_parallel_transport_lofting()
