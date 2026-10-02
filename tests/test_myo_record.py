"""Unit tests of the pure part of myo_record.py (no Blender needed).

myo_record.py is the contract shared with MUFIS; these tests pin its formulas,
side parsing and plausibility thresholds. Run from the repository root::

    python -m unittest discover -s tests -p "test_*.py"
"""

import importlib.util
import math
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("myo_record", os.path.join(ROOT, "AddonFolder", "myo_record.py"))
mr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mr)


def levels(findings):
    return [lvl for lvl, _msg in findings]


class Formulas(unittest.TestCase):
    def test_cylinder_pcsa_is_its_cross_section(self):
        r, length = 0.01, 0.05
        pcsa, fiber = mr.pcsa_from_volume(math.pi * r ** 2 * length, length)
        self.assertAlmostEqual(pcsa, math.pi * r ** 2)
        self.assertAlmostEqual(fiber, length)

    def test_fiber_ratio_and_pennation(self):
        pcsa, fiber = mr.pcsa_from_volume(1e-4, 0.1, fiber_length_ratio=0.5, pennation_deg=60)
        self.assertAlmostEqual(fiber, 0.05)
        self.assertAlmostEqual(pcsa, 1e-4 * 0.5 / 0.05)

    def test_zero_length(self):
        self.assertEqual(mr.pcsa_from_volume(1e-4, 0.0)[0], 0.0)

    def test_pcsa_from_fibres(self):
        # equal fibres: both models give V / L
        pcsa, fiber = mr.pcsa_from_fibres(1e-4, [0.1] * 5, [0.2] * 5)
        self.assertAlmostEqual(fiber, 0.1)
        self.assertAlmostEqual(pcsa, 1e-3)
        self.assertAlmostEqual(mr.pcsa_from_fibres(1e-4, [0.1] * 5, [0.2] * 5, model="WEIGHTED")[0], 1e-3)
        # half the volume in fibres of 0.05, half in 0.15: sum V_i/L_i = 5e-5/0.05 + 5e-5/0.15
        lengths, shares = [0.05, 0.15], [0.5, 0.5]
        pcsa_w, fiber = mr.pcsa_from_fibres(1e-4, lengths, shares, model="WEIGHTED")
        self.assertAlmostEqual(fiber, 0.1)
        self.assertAlmostEqual(pcsa_w, 5e-5 / 0.05 + 5e-5 / 0.15)
        self.assertGreater(pcsa_w, mr.pcsa_from_fibres(1e-4, lengths, shares)[0])     # short fibres count more
        # ratio and pennation as for the path
        pcsa, fiber = mr.pcsa_from_fibres(1e-4, [0.1], [1.0], fiber_length_ratio=0.5, pennation_deg=60)
        self.assertAlmostEqual(fiber, 0.05)
        self.assertAlmostEqual(pcsa, 1e-4 * 0.5 / 0.05)
        self.assertEqual(mr.pcsa_from_fibres(1e-4, [], [])[0], 0.0)
        # weights: mean length weighted
        pcsa, fiber = mr.pcsa_from_fibres(1e-4, [0.1, 0.2], [0.5, 0.5], weights=[3.0, 1.0])
        self.assertAlmostEqual(fiber, 0.125)
        self.assertAlmostEqual(pcsa, 1e-4 / 0.125)

    def test_force(self):
        # 10 cm2 at 30 N/cm2 = 300 N
        self.assertAlmostEqual(mr.force_from_pcsa(10e-4, 30), 300.0)


class Sides(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(mr.parse_side("temp_sup_left"), "L")
        self.assertEqual(mr.parse_side("Masseter_R"), "R")
        self.assertEqual(mr.parse_side("digastric"), "")

    def test_strip(self):
        self.assertEqual(mr.strip_side("temp_sup_right"), "temp_sup")


class Checks(unittest.TestCase):
    def good(self, **over):
        values = {"myo_volume_m3": 2e-5, "myo_path_length_m": 0.06, "myo_linear_length_m": 0.055,
                  "myo_fiber_length_m": 0.06}
        values.update(over)
        return values

    def test_plausible_muscle_has_no_warnings(self):
        self.assertEqual(mr.check_muscle(self.good(), 0.2), [])

    def test_same_ratios_hold_at_any_size(self):
        # A muscle 10x larger in a 10x larger skull is as plausible.
        big = self.good(myo_volume_m3=2e-2, myo_path_length_m=0.6, myo_linear_length_m=0.55,
                        myo_fiber_length_m=0.6)
        self.assertEqual(mr.check_muscle(big, 2.0), [])

    def test_missing_volume_is_an_error(self):
        self.assertIn(mr.QA_ERROR, levels(mr.check_muscle(self.good(myo_volume_m3=0.0), 0.2)))

    def test_holes(self):
        self.assertIn(mr.QA_WARNING, levels(mr.check_muscle(self.good(), 0.2, belly_hole_error=0.05)))
        self.assertEqual(levels(mr.check_muscle(self.good(), 0.2, belly_hole_error=0.001)), [mr.QA_INFO])

    def test_wrong_scale_is_caught_by_size_ratio(self):
        # Volume of a whole skull for a 'muscle': size ratio out of range.
        self.assertIn(mr.QA_WARNING, levels(mr.check_muscle(self.good(myo_volume_m3=0.5), 0.2)))

    def test_parameters(self):
        self.assertEqual(mr.check_parameters(1.06, 30, 1.0), [])
        self.assertEqual(len(mr.check_parameters(2.0, 300, 0.1)), 3)

    def test_bilateral(self):
        out = mr.check_bilateral({"m_left": 1.0, "m_right": 2.0, "x_left": 1.0, "x_right": 1.1})
        self.assertIn("m_left", out)
        self.assertNotIn("x_left", out)

    def test_worst_level(self):
        self.assertEqual(mr.worst_level([(mr.QA_INFO, ""), (mr.QA_ERROR, ""), (mr.QA_WARNING, "")]),
                         mr.QA_ERROR)
        self.assertEqual(mr.worst_level([]), mr.QA_OK)


class WindingVolume(unittest.TestCase):
    def cube(self, offset=(0, 0, 0), size=10.0):
        import itertools
        o = [offset[i] for i in range(3)]
        v = [[o[0] + x * size, o[1] + y * size, o[2] + z * size] for x, y, z in itertools.product((0, 1), repeat=3)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        tris = []
        for a, b, c, d in faces:
            tris += [[v[a], v[b], v[c]], [v[a], v[c], v[d]]]
        return tris

    def test_cube(self):
        vol, se, double = mr.winding_volume(self.cube(), samples=4000)
        self.assertAlmostEqual(vol, 1000.0, delta=3 * se + 1e-9)
        self.assertEqual(double, 0.0)

    def test_overlapping_cubes_give_the_union(self):
        tris = self.cube() + self.cube(offset=(5, 0, 0))     # overlap 500, union 1500
        vol, se, double = mr.winding_volume(tris, samples=6000)
        self.assertAlmostEqual(vol, 1500.0, delta=4 * se)
        self.assertAlmostEqual(double, 500.0, delta=60)

    def test_open_mesh_is_tolerated(self):
        tris = self.cube()[:-2]                               # one face missing
        vol, se, _ = mr.winding_volume(tris, samples=4000)
        self.assertAlmostEqual(vol, 1000.0, delta=150)


if __name__ == "__main__":
    unittest.main()
