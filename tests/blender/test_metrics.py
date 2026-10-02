"""Headless tests of MyoGeneratorRemix measurements on a synthetic muscle.

The muscle is a closed cylinder (radius 10 mm, length 50 mm, 1 BU = 1 mm)
with a straight path curve, so its PCSA must equal its cross-section.
"""

import importlib.util
import math
import os
import sys
import tempfile
import unittest

import bmesh
import bpy
from mathutils import Matrix

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PACKAGE = os.path.join(REPO, "AddonFolder")
MODULE_NAME = "myogen_under_test"
RADIUS, LENGTH, SEGMENTS = 10.0, 50.0, 64


def load_addon():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(MODULE_NAME, os.path.join(PACKAGE, "__init__.py"),
                                                  submodule_search_locations=[PACKAGE])
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    module.register()
    return module


def link(obj, coll):
    coll.objects.link(obj)
    return obj


def build_muscle(name, x=30.0):
    """muscles/<name> with origin, insertion, path and a closed cylinder belly along +Z."""
    mr = sys.modules[f"{MODULE_NAME}.myo_record"]
    root = mr.get_root(create=True, scene=bpy.context.scene)
    coll = bpy.data.collections.new(name)
    root.children.link(coll)

    def disc(suffix, z):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=RADIUS)
        bm.transform(Matrix.Translation((x, 0, z)))
        mesh = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(mesh)
        bm.free()
        return link(bpy.data.objects.new(name + suffix, mesh), coll)

    disc("_origin", LENGTH)
    disc("_insertion", 0.0)

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=SEGMENTS, radius1=RADIUS, radius2=RADIUS, depth=LENGTH)
    bm.transform(Matrix.Translation((x, 0, LENGTH / 2)))
    mesh = bpy.data.meshes.new(name + "_muscle")
    bm.to_mesh(mesh)
    bm.free()
    link(bpy.data.objects.new(name + "_muscle", mesh), coll)

    curve = bpy.data.curves.new(name + "_curve", type='CURVE')
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(1)
    for point, z in zip(spline.bezier_points, (LENGTH, 0.0)):
        point.co = (x, 0, z)
        point.handle_left_type = point.handle_right_type = 'VECTOR'
    link(bpy.data.objects.new(name + "_curve", curve), coll)
    return coll


class MetricsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_addon()
        cls.mr = sys.modules[f"{MODULE_NAME}.myo_record"]
        cls.metrics = sys.modules[f"{MODULE_NAME}.muscle_metrics"]

    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for coll in list(bpy.data.collections):
            bpy.data.collections.remove(coll)
        bpy.context.scene.unit_settings.scale_length = 0.001
        self.coll = build_muscle("temp_left")

    def test_cylinder_pcsa_equals_cross_section(self):
        rows, findings = self.metrics.compute_muscles(bpy.context, write=True)
        row = rows[0]
        polygon_area = 0.5 * SEGMENTS * RADIUS ** 2 * math.sin(2 * math.pi / SEGMENTS)  # mm2
        # Relative tolerance: Blender stores the unit scale as float32 (0.0010000000475).
        self.assertAlmostEqual(row["myo_path_length_m"], LENGTH * 1e-3, delta=LENGTH * 1e-3 * 1e-6)
        self.assertAlmostEqual(row["myo_pcsa_m2"], polygon_area * 1e-6, delta=polygon_area * 1e-6 * 1e-6)
        self.assertAlmostEqual(row["myo_force_n"], polygon_area * 1e-2 * 30.0, delta=polygon_area * 1e-2 * 30.0 * 1e-6)
        self.assertNotIn(self.mr.QA_ERROR, [lvl for lvl, _ in findings])
        self.assertEqual([lvl for lvl, _ in row["qa"] if lvl != self.mr.QA_INFO], [])

    def test_record_is_written_and_readable(self):
        self.metrics.compute_muscles(bpy.context, write=True)
        rec = self.mr.read_record(self.coll)
        self.assertEqual(rec["myo_schema"], self.mr.SCHEMA_VERSION)
        self.assertEqual(rec["myo_side"], "L")
        self.assertTrue(rec["has_pcsa"])
        self.assertEqual(rec["objects"]["belly"].name, "temp_left_muscle")
        self.assertEqual(rec["objects"]["belly"].get(self.mr.ROLE_KEY), "belly")

    def test_wrong_unit_scale_is_an_error(self):
        bpy.context.scene.unit_settings.scale_length = 1.0  # 1 BU = 1 m
        _rows, findings = self.metrics.compute_muscles(bpy.context, write=False)
        self.assertIn(self.mr.QA_ERROR, [lvl for lvl, _ in findings])
        self.assertTrue(any("Unit Scale to 0.001" in msg for _lvl, msg in findings))

    def test_foreign_collections_are_ignored(self):
        other = bpy.data.collections.new("not_a_muscle")
        self.mr.get_root().children.link(other)
        rows, _ = self.metrics.compute_muscles(bpy.context, write=False)
        self.assertEqual([r["collection"] for r in rows], ["temp_left"])

    def test_csv_export(self):
        bpy.context.scene.myogen.conf_path = tempfile.mkdtemp()
        bpy.context.scene.myogen.file_name = "muscles"
        self.assertEqual(bpy.ops.myogen.calculate_muscle_parameters(), {'FINISHED'})
        with open(os.path.join(bpy.context.scene.myogen.conf_path, "muscles.csv"), encoding="utf-8") as fh:
            header = fh.readline().strip().split(",")
        self.assertIn("pcsa_cm2", header)
        self.assertIn("qa", header)

    def test_self_overlapping_belly_uses_enclosed_volume(self):
        """Two interpenetrating cylinders in one belly: the signed sum counts the
        overlap twice; the record must use the enclosed (union) volume."""
        belly = bpy.data.objects["temp_left_muscle"]
        bm = bmesh.new()
        bm.from_mesh(belly.data)
        bmesh.ops.create_cone(bm, cap_ends=True, segments=SEGMENTS, radius1=RADIUS, radius2=RADIUS, depth=LENGTH,
                              matrix=Matrix.Translation((30 + RADIUS, 0, LENGTH / 2)))
        bm.to_mesh(belly.data)
        bm.free()
        rows, _ = self.metrics.compute_muscles(bpy.context, write=True)
        row = rows[0]
        single = 0.5 * SEGMENTS * RADIUS ** 2 * math.sin(2 * math.pi / SEGMENTS) * LENGTH * 1e-9   # m3
        # Union of two circles of radius r whose centres are r apart, times the length.
        r, d = RADIUS, RADIUS
        overlap = 2 * r ** 2 * math.acos(d / (2 * r)) - d / 2 * math.sqrt(4 * r ** 2 - d ** 2)
        union = (2 * math.pi * r ** 2 - overlap) * LENGTH * 1e-9   # m3
        self.assertAlmostEqual(row["myo_volume_raw_m3"], 2 * single, delta=2 * single * 1e-3)
        self.assertEqual(row["myo_volume_method"], "voxel union (defective mesh)")
        self.assertAlmostEqual(row["myo_volume_m3"], union, delta=union * 0.015)
        self.assertTrue(any("defective" in msg for _lvl, msg in row["qa"]))
        # PCSA follows the corrected volume
        self.assertAlmostEqual(row["myo_pcsa_m2"], row["myo_volume_m3"] / row["myo_fiber_length_m"], places=12)

    def test_mirror_creates_right_side(self):
        for obj in bpy.data.objects:
            obj.select_set(obj.name.startswith("temp_left"))
        self.assertEqual(bpy.ops.myogen.mirror_duplicate(axis='X'), {'FINISHED'})
        right = self.mr.get_root().children.get("temp_right")
        self.assertIsNotNone(right)
        objs = self.mr.resolve_objects(right)
        self.assertEqual(set(objs), {"origin", "insertion", "path", "belly"})
        point = objs["path"].data.splines[0].bezier_points[0].co
        self.assertAlmostEqual(point.x, -30.0)
        rows, _ = self.metrics.compute_muscles(bpy.context, write=False)
        volumes = {r["collection"]: r["myo_volume_m3"] for r in rows}
        self.assertAlmostEqual(volumes["temp_left"], volumes["temp_right"], places=12)


if __name__ == "__main__":
    unittest.main()
