"""Unit tests of contour_matching.py (no Blender needed)."""

import importlib.util
import math
import os
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("contour_matching",
                                               os.path.join(ROOT, "AddonFolder", "contour_matching.py"))
cm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cm)

X, Y, Z = np.eye(3)


def ellipse(n, centre, rx=10.0, ry=4.0, start=0.0, reverse=False, uneven=False, tilt=0.0):
    """Points of an ellipse in the XY plane (optionally tilted about X)."""
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    if uneven:  # dense on one side, sparse on the other
        t = 2 * math.pi * (np.linspace(0, 1, n, endpoint=False) ** 2)
    t = t + start
    if reverse:
        t = -t
    pts = np.column_stack([rx * np.cos(t), ry * np.sin(t), np.zeros(n)])
    c, s = math.cos(tilt), math.sin(tilt)
    pts = pts @ np.array([[1, 0, 0], [0, c, s], [0, -s, c]])
    return pts + np.asarray(centre)


class Resample(unittest.TestCase):
    def test_even_spacing(self):
        out = cm.resample_closed_loop(ellipse(200, (0, 0, 0), uneven=True), 32)
        seg = np.linalg.norm(np.diff(np.vstack([out, out[:1]]), axis=0), axis=1)
        self.assertLess(seg.std() / seg.mean(), 0.05)

    def test_upsampling_works(self):
        self.assertEqual(cm.resample_closed_loop(ellipse(5, (0, 0, 0)), 40).shape, (40, 3))

    def test_too_few_points(self):
        with self.assertRaises(ValueError):
            cm.resample_closed_loop([(0, 0, 0), (1, 0, 0)], 8)


class Matching(unittest.TestCase):
    frame = (X, Y)  # path along Z: normal X, binormal Y at both ends

    def loft(self, insertion, n=24):
        origin = ellipse(37, (0, 0, 0))
        return cm.match_contours(origin, insertion, n, self.frame, self.frame)

    def test_identical_shapes_give_parallel_fibres(self):
        o, i, info = self.loft(ellipse(37, (0, 0, 50)))
        np.testing.assert_allclose(i - o, np.tile((0, 0, 50), (len(o), 1)), atol=1e-6)
        self.assertAlmostEqual(info["waist"], 1.0, places=6)

    def test_independent_of_start_direction_and_count(self):
        """Different start vertex, direction, vertex count and density: same loft."""
        reference = self.loft(ellipse(37, (0, 0, 50)))[1]
        for insertion in (ellipse(91, (0, 0, 50), start=2.0),
                          ellipse(13, (0, 0, 50), reverse=True),
                          ellipse(150, (0, 0, 50), start=4.0, reverse=True, uneven=True)):
            o, i, info = self.loft(insertion)
            self.assertGreater(info["waist"], 0.97)
            # matched points sit above their origin counterparts (no twist)
            self.assertLess(np.abs((i - o)[:, :2]).max(), 1.5)

    def test_index_matching_would_twist(self):
        o = cm.resample_closed_loop(ellipse(37, (0, 0, 0)), 24)
        i = cm.resample_closed_loop(ellipse(37, (0, 0, 50), start=math.pi), 24)  # half-turn start
        self.assertLess(cm.waist_index(o, i), 0.2)        # naive index matching: hourglass
        _o, _i, info = self.loft(ellipse(37, (0, 0, 50), start=math.pi))
        self.assertGreater(info["waist"], 0.99)           # matched: none

    def test_translation_and_scale_do_not_change_the_match(self):
        a = cm.local_coordinates(cm.resample_closed_loop(ellipse(40, (0, 0, 0)), 20), X, Y)
        b = cm.local_coordinates(cm.resample_closed_loop(ellipse(40, (0, 0, 0), start=1.0), 20), X, Y)
        shift = cm.best_cyclic_match(a, b)[:2]
        self.assertEqual(cm.best_cyclic_match(a, 3.0 * b + 7.0)[:2], shift)

    def test_frames_follow_the_path(self):
        """Insertion contour tilted 90 deg with the path: matched in the path frames."""
        origin = ellipse(30, (0, 0, 0))
        insertion = ellipse(30, (0, 50, 50), tilt=math.pi / 2, start=1.3)   # lies in the XZ plane
        o, i, info = cm.match_contours(origin, insertion, 24, (X, Y), (X, Z))
        self.assertGreater(info["waist"], 0.7)  # in world space the planes differ; no twist in x
        np.testing.assert_allclose(i[:, 0], o[:, 0], atol=1.0)

    def test_3d_match_has_the_widest_waist(self):
        """Non-planar contours: no cyclic shift/direction gives a wider mid section."""
        rng = np.random.default_rng(3)
        t = np.linspace(0, 2 * math.pi, 30, endpoint=False)
        origin = np.column_stack([15 * np.cos(t), 6 * np.sin(t), 5 * np.sin(2 * t)])       # saddle-shaped
        insertion = np.column_stack([4 * np.cos(t + 1), 9 * np.sin(t + 1), 60 + 3 * np.cos(3 * t)])[::-1]
        o, i, info = cm.match_contours(origin, insertion + rng.normal(0, 0.1, insertion.shape), 30)
        directions = cm.circulation_directions(o, i)
        best = max(cm.waist_index(o, cm.apply_match(i, s, r)) for s in range(30) for r in (False,))
        self.assertAlmostEqual(info["waist"], best, places=9)   # widest waist among same-circulation matches
        self.assertEqual(directions, (False,))

    def test_elongated_contour_is_not_folded(self):
        """A thin ellipse matches almost as well backwards; the loft must not fold."""
        origin = ellipse(40, (0, 0, 0), rx=20.0, ry=1.0)
        insertion = ellipse(40, (0, 0, 50), rx=20.0, ry=1.0, reverse=True, start=0.3)
        o, i, info = cm.match_contours(origin, insertion, 32)
        self.assertGreater(info["section_area"], 0.9)
        # same circulation as the origin after matching
        self.assertGreater(cm.vector_area(o) @ cm.vector_area(i), 0)

    def test_section_area_detects_folding(self):
        o = cm.resample_closed_loop(ellipse(40, (0, 0, 0), rx=20.0, ry=1.0), 32)
        i = cm.resample_closed_loop(ellipse(40, (0, 0, 50), rx=20.0, ry=1.0, reverse=True), 32)
        self.assertGreater(cm.waist_index(o, i), 0.9)          # RMS size looks fine...
        self.assertLess(cm.section_area_ratio(o, i), 0.1)      # ...but the middle is folded flat

    def test_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cm.best_cyclic_match(np.zeros((4, 2)), np.zeros((5, 2)))


if __name__ == "__main__":
    unittest.main()
