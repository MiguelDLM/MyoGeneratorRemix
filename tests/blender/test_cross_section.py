"""Headless tests for cross-section visual clipping in Blender."""

import importlib.util
import os
import sys
import unittest

import bmesh
import bpy
import mathutils

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PACKAGE = os.path.join(REPO, "AddonFolder")
MODULE_NAME = "myogen_under_test"


def load_addon():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(
        MODULE_NAME, os.path.join(PACKAGE, "__init__.py"), submodule_search_locations=[PACKAGE]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    module.register()
    return module


class CrossSectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = load_addon()
        cls.cs = sys.modules[f"{MODULE_NAME}.cross_section"]

    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        # Create a test bone mesh
        bm_bone = bmesh.new()
        bmesh.ops.create_cube(bm_bone, size=50.0)
        m_bone = bpy.data.meshes.new("Cranium_Bone")
        bm_bone.to_mesh(m_bone)
        bm_bone.free()
        self.bone_obj = bpy.data.objects.new("Cranium_Bone", m_bone)
        bpy.context.scene.collection.objects.link(self.bone_obj)
        self.bone_obj.location = (0, 0, 0)

        # Create a test muscle belly mesh
        bm_muscle = bmesh.new()
        bmesh.ops.create_uvsphere(bm_muscle, u_segments=16, v_segments=8, radius=20.0)
        m_muscle = bpy.data.meshes.new("test_muscle")
        bm_muscle.to_mesh(m_muscle)
        bm_muscle.free()
        self.muscle_obj = bpy.data.objects.new("test_muscle", m_muscle)
        bpy.context.scene.collection.objects.link(self.muscle_obj)
        self.muscle_obj["myo_role"] = "belly"
        self.muscle_obj.location = (0, 0, 30)

        # Create a non-mesh curve (must NOT receive Boolean modifier)
        curve_data = bpy.data.curves.new("test_path", type='CURVE')
        curve_data.dimensions = '3D'
        self.curve_obj = bpy.data.objects.new("test_path", curve_data)
        bpy.context.scene.collection.objects.link(self.curve_obj)
        bpy.context.view_layer.update()

    def tearDown(self):
        props = bpy.context.scene.myogen
        if props.section_cut_active:
            props.section_cut_active = False

    def test_enable_and_disable_cut(self):
        """Activating the cut applies modifiers non-destructively; deactivating removes them cleanly."""
        props = bpy.context.scene.myogen
        self.assertFalse(props.section_cut_active)

        initial_bone_verts = len(self.bone_obj.data.vertices)
        initial_muscle_verts = len(self.muscle_obj.data.vertices)

        # 1. Enable cross-section cut
        self.assertEqual(bpy.ops.myogen.toggle_section_cut(), {'FINISHED'})
        self.assertTrue(props.section_cut_active)

        cutter = self.cs.find_cutter(bpy.context)
        self.assertIsNotNone(cutter)
        self.assertEqual(cutter.display_type, 'WIRE')
        self.assertTrue(cutter.show_in_front)
        self.assertTrue(cutter.hide_render)
        self.assertFalse(cutter.hide_viewport)

        # Target meshes receive modifier
        self.assertIn(self.cs.MODIFIER_NAME, self.bone_obj.modifiers)
        self.assertIn(self.cs.MODIFIER_NAME, self.muscle_obj.modifiers)
        # Non-mesh curve does NOT receive modifier
        self.assertNotIn(self.cs.MODIFIER_NAME, self.curve_obj.modifiers)

        # 2. Deactivate cut
        self.assertEqual(bpy.ops.myogen.toggle_section_cut(), {'FINISHED'})
        self.assertFalse(props.section_cut_active)

        # Modifiers are removed from all objects
        self.assertNotIn(self.cs.MODIFIER_NAME, self.bone_obj.modifiers)
        self.assertNotIn(self.cs.MODIFIER_NAME, self.muscle_obj.modifiers)
        self.assertTrue(cutter.hide_viewport)

        # Original mesh vertex count is 100% untouched
        self.assertEqual(len(self.bone_obj.data.vertices), initial_bone_verts)
        self.assertEqual(len(self.muscle_obj.data.vertices), initial_muscle_verts)

    def test_align_and_flip(self):
        """Aligning to planes positions the cutter correctly, and flip inverts its side."""
        props = bpy.context.scene.myogen
        bpy.ops.myogen.toggle_section_cut()

        cutter = self.cs.find_cutter(bpy.context)
        center, dims, _min, _max = self.cs.compute_bounds([self.bone_obj, self.muscle_obj])

        # Transverse (Z)
        self.assertEqual(bpy.ops.myogen.align_section_cut(plane='TRANSVERSE'), {'FINISHED'})
        self.assertGreater(cutter.location.z, center.z)

        # Flip side
        old_z = cutter.location.z
        self.assertEqual(bpy.ops.myogen.flip_section_cut(), {'FINISHED'})
        self.assertLess(cutter.location.z, center.z)
        self.assertAlmostEqual(cutter.location.z - center.z, -(old_z - center.z), delta=1e-3)

        # Sagittal (X)
        self.assertEqual(bpy.ops.myogen.align_section_cut(plane='SAGITTAL'), {'FINISHED'})
        self.assertGreater(cutter.location.x, center.x)

        # Coronal (Y)
        self.assertEqual(bpy.ops.myogen.align_section_cut(plane='CORONAL'), {'FINISHED'})
        self.assertGreater(cutter.location.y, center.y)

    def test_scope_and_modes(self):
        """Scope restricts targets to muscles only, and mode changes operation."""
        props = bpy.context.scene.myogen
        props.section_cut_active = True

        # Mode test
        props.section_cut_mode = 'INTERSECT'
        self.assertEqual(self.muscle_obj.modifiers[self.cs.MODIFIER_NAME].operation, 'INTERSECT')
        props.section_cut_mode = 'DIFFERENCE'
        self.assertEqual(self.muscle_obj.modifiers[self.cs.MODIFIER_NAME].operation, 'DIFFERENCE')

        # Scope test: MUSCLES only
        props.section_cut_scope = 'MUSCLES'
        self.assertIn(self.cs.MODIFIER_NAME, self.muscle_obj.modifiers)
        self.assertNotIn(self.cs.MODIFIER_NAME, self.bone_obj.modifiers)

        # Scope test: SCENE
        props.section_cut_scope = 'SCENE'
        self.assertIn(self.cs.MODIFIER_NAME, self.muscle_obj.modifiers)
        self.assertIn(self.cs.MODIFIER_NAME, self.bone_obj.modifiers)


if __name__ == "__main__":
    unittest.main()
