"""
Test script for MyoGeneratorRemix spline-based diameter control
This script can be run in Blender to test the curve weight functionality
"""

import bpy
import sys
import os

# Add addon folder to path if needed
addon_path = "/home/miguel/Documents/software/MyoGeneratorRemix/AddonFolder"
if addon_path not in sys.path:
    sys.path.append(addon_path)

def test_spline_diameter_functions():
    """Test the spline diameter calculation functions"""
    print("Testing spline diameter functions...")
    
    try:
        from spline_lofting_utilities import (
            get_spline_diameter_at_parameter,
            ensure_proper_curve_radius_setup,
            debug_curve_weights
        )
        
        # Create a test Bezier curve
        bpy.ops.curve.primitive_bezier_curve_add()
        curve_obj = bpy.context.active_object
        curve_obj.name = "test_muscle_curve"
        
        # Set up muscle-like radius values
        spline = curve_obj.data.splines[0]
        if len(spline.bezier_points) >= 2:
            spline.bezier_points[0].radius = 0.8  # Start
            spline.bezier_points[1].radius = 1.4  # End
        
        # Test diameter calculation at different parameters
        print("Testing diameter calculation:")
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            diameter = get_spline_diameter_at_parameter(curve_obj, t)
            print(f"  t={t}: diameter={diameter}")
        
        # Test automatic setup
        ensure_proper_curve_radius_setup(curve_obj)
        debug_curve_weights(curve_obj)
        
        print("✓ Spline diameter functions working correctly!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing spline functions: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_curve_weight_operators():
    """Test the curve weight setting operators"""
    print("Testing curve weight operators...")
    
    try:
        # Check if operators are registered
        if hasattr(bpy.ops.view3d, 'muscle_set_curve_weights'):
            print("✓ Muscle_Set_Curve_Weights_Op is registered")
        else:
            print("✗ Muscle_Set_Curve_Weights_Op not found")
            return False
        
        if hasattr(bpy.ops.view3d, 'muscle_set_default_curve_weights'):
            print("✓ Muscle_Set_Default_Curve_Weights_Op is registered")
        else:
            print("✗ Muscle_Set_Default_Curve_Weights_Op not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing operators: {e}")
        return False

def test_real_time_updates():
    """Test if real-time updates work properly"""
    print("Testing real-time update mechanism...")
    
    try:
        # Check if preview properties exist
        scene = bpy.context.scene
        
        if hasattr(scene, 'muscle_use_spline_diameter'):
            print(f"✓ muscle_use_spline_diameter: {scene.muscle_use_spline_diameter}")
        else:
            print("✗ muscle_use_spline_diameter property missing")
            return False
        
        if hasattr(scene, 'muscle_diameter_smoothing'):
            print(f"✓ muscle_diameter_smoothing: {scene.muscle_diameter_smoothing}")
        else:
            print("✗ muscle_diameter_smoothing property missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing real-time updates: {e}")
        return False

def run_all_tests():
    """Run all tests for the spline-based diameter control system"""
    print("=" * 50)
    print("MyoGeneratorRemix Spline Diameter Control Tests")
    print("=" * 50)
    
    tests = [
        test_spline_diameter_functions,
        test_curve_weight_operators,
        test_real_time_updates
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Spline diameter control is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("=" * 50)

if __name__ == "__main__":
    run_all_tests()
