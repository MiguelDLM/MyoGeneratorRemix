"""Headless tests of the loft (built in memory: the raw material of along-the-path bellies).

The insertion contour has a different vertex count, starts half a turn away
and runs the other way. Joined by index the loft twists into an hourglass;
with automatic matching it must not.
"""

import math
import sys
import unittest

import bpy
from mathutils import Vector

import test_metrics

M = "loft_left"


def contour(name, n, z, start=0.0, reverse=False, rx=12.0, ry=5.0, collection=None):
    curve = bpy.data.curves.new(name, type='CURVE')
    spline = curve.splines.new('POLY')
    spline.points.add(n - 1)
    for k, p in enumerate(spline.points):
        t = start + (-1 if reverse else 1) * 2 * math.pi * k / n
        p.co = (rx * math.cos(t), ry * math.sin(t), z, 1.0)
    spline.use_cyclic_u = True
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    return obj


def straight_path(name, start, end, collection):
    curve = bpy.data.curves.new(name, type='CURVE')
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(1)
    for point, co in zip(spline.bezier_points, (start, end)):
        point.co = co
        point.handle_left_type = point.handle_right_type = 'VECTOR'
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    return obj


def dome(name, z, height, collection, rx=12.0, ry=5.0, rings=6, sectors=40):
    """Attachment surface bounded by the contour ellipse, bulging by ``height``."""
    import bmesh
    bm = bmesh.new()
    grid = []
    for k in range(1, rings + 1):
        r = k / rings
        grid.append([bm.verts.new((rx * r * math.cos(a), ry * r * math.sin(a), z + height * (1 - r * r)))
                     for a in (2 * math.pi * j / sectors for j in range(sectors))])
    centre = bm.verts.new((0, 0, z + height))
    for j in range(sectors):
        bm.faces.new([centre, grid[0][j], grid[0][(j + 1) % sectors]])
    for a, b in zip(grid[:-1], grid[1:]):
        for j in range(sectors):
            bm.faces.new([a[j], b[j], b[(j + 1) % sectors], a[(j + 1) % sectors]])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def section_waist(construction):
    """RMS radius of the middle loft section / mean RMS radius of the end sections."""
    def radius(pts):
        c = sum(pts, Vector()) / len(pts)
        return math.sqrt(sum((p - c).length_squared for p in pts) / len(pts))
    sections = construction["sections"]
    return radius(sections[len(sections) // 2]) / ((radius(sections[0]) + radius(sections[-1])) / 2)


def mid_waist(verts, z_ends=(0.0, 50.0)):
    """RMS radius of the ring nearest mid-height / mean RMS radius of the end rings."""
    rings = {}
    for co in verts:
        rings.setdefault(round(co.z, 1), []).append(co.copy())
    rings = {z: pts for z, pts in rings.items() if len(pts) >= 6}

    def radius(z0):
        pts = rings[min(rings, key=lambda z: abs(z - z0))]
        c = sum(pts, Vector()) / len(pts)
        return math.sqrt(sum((p - c).length_squared for p in pts) / len(pts))
    return radius(sum(z_ends) / 2) / ((radius(z_ends[0]) + radius(z_ends[1])) / 2)


class LoftTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_metrics.load_addon()
        cls.preview = sys.modules[f"{test_metrics.MODULE_NAME}.preview"]
        cls.mr = sys.modules[f"{test_metrics.MODULE_NAME}.myo_record"]

    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for coll in list(bpy.data.collections):
            bpy.data.collections.remove(coll)
        props = bpy.context.scene.myogen
        root = self.mr.get_root(create=True, scene=bpy.context.scene)
        self.coll = bpy.data.collections.new(M)
        root.children.link(self.coll)
        contour(M + "_origin_contour", 40, 50.0, collection=self.coll)
        contour(M + "_insertion_contour", 17, 0.0, start=math.pi, reverse=True, collection=self.coll)
        self.path = straight_path(M + "_curve", (0, 0, 50), (0, 0, 0), self.coll)
        for point in self.path.data.splines[0].bezier_points:
            point.radius = 0.8                       # as in the reconstructed specimens
        self.origin_surface = dome(M + "_origin", 50.0, 3.0, self.coll)
        self.insertion_surface = dome(M + "_insertion", 0.0, -3.0, self.coll)
        props.muscle_name = M
        props.muscle_contour_resolution = 32
        props.muscle_curve_subdivisions = 12
        props.origin_contour_offset = props.insertion_contour_offset = 0
        props.origin_reverse_orientation = props.insertion_reverse_orientation = False
        props.contour_matching = 'AUTO'
        props.muscle_connection_mode = 'FOLLOW_PATH'
        props.anchor_falloff = 0.15
        props.muscle_shape = 'FUSIFORM'
        self.shape = 'NATURAL'

    def build(self):
        props = bpy.context.scene.myogen
        bm, construction = self.preview.build_loft(props, self.path, self.coll.objects[M + "_origin_contour"],
                                                   self.coll.objects[M + "_insertion_contour"],
                                                   self.origin_surface, self.insertion_surface, shape=self.shape)
        verts = [v.co.copy() for v in bm.verts]
        bm.free()
        return verts, construction

    def test_automatic_matching_has_no_hourglass(self):
        for mode in ('FOLLOW_PATH', 'DIRECT_CONNECTION'):
            bpy.context.scene.myogen.muscle_connection_mode = mode
            _verts, construction = self.build()
            self.assertGreater(section_waist(construction), 0.9, mode)
            self.assertFalse(self.preview.is_twisted(construction["info"]))

    def test_index_matching_twists(self):
        props = bpy.context.scene.myogen
        props.contour_matching = 'INDEX'
        props.muscle_connection_mode = 'DIRECT_CONNECTION'
        _verts, construction = self.build()
        self.assertLess(section_waist(construction), 0.5)
        self.assertTrue(self.preview.is_twisted(construction["info"]))

    def test_manual_offset_still_fine_tunes(self):
        bpy.context.scene.myogen.insertion_contour_offset = 3
        _verts, construction = self.build()
        self.assertGreater(section_waist(construction), 0.8)

    def assert_anchored(self, verts, construction, tolerance=1e-4):
        """Every matched contour point is a vertex; every cap vertex lies on its surface."""
        from mathutils.bvhtree import BVHTree
        for p in construction["origin"] + construction["insertion"]:
            self.assertLess(min((p - v).length for v in verts), tolerance)
        trees = [BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
                 for o in (self.origin_surface, self.insertion_surface)]
        contour = construction["origin"] + construction["insertion"]
        anchored = [v for v, w in zip(verts, construction["weights"]) if w == 0.0]
        self.assertGreater(len(anchored), 2 * len(construction["origin"]))   # rings + draped caps
        cap = [v for v in anchored if min((v - p).length for p in contour) > tolerance]
        self.assertTrue(cap)
        for v in cap:                                   # draped caps lie on the attachment surfaces
            self.assertLess(min(t.find_nearest(v)[3] for t in trees), 1e-3)

    def test_ends_stay_on_the_attachments(self):
        """Path radius 0.8 at the ends and smoothing must not move the attachment vertices."""
        for shape in ('NATURAL', 'FUSIFORM', 'PARALLEL'):
            with self.subTest(shape=shape):
                self.shape = shape
                verts, construction = self.build()
                self.assert_anchored(verts, construction)
        self.shape = 'NATURAL'

    def test_belly_profile_changes_the_middle_only(self):
        props = bpy.context.scene.myogen
        props.muscle_shape = 'FUSIFORM'
        self.shape = 'NATURAL'
        _v, plain = self.build()
        self.shape = 'FUSIFORM'
        props.belly_bulge = 0.5
        _v, bulged = self.build()
        props.belly_bulge = -0.4
        _v, waisted = self.build()
        props.muscle_shape = 'FUSIFORM'
        self.shape = 'NATURAL'

        def size(c, k):
            pts = c["sections"][k]
            centre = sum(pts, Vector()) / len(pts)
            return max((p - centre).length for p in pts)
        mid = len(plain["sections"]) // 2
        self.assertGreater(size(bulged, mid), size(plain, mid) * 1.2)
        self.assertLess(size(waisted, mid), size(plain, mid) * 0.9)
        for k in (0, -1):                                    # anchored ends unchanged
            self.assertAlmostEqual(size(bulged, k), size(plain, k), 5)

    def test_points_inside_a_bone_are_pushed_out(self):
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=10.0)
        mesh = bpy.data.meshes.new("bone")
        bm.to_mesh(mesh)
        bm.free()
        bone = bpy.data.objects.new("bone", mesh)
        self.coll.objects.link(bone)
        points = [Vector((1.0, 2.0, 4.0)), Vector((20.0, 0.0, 0.0))]
        moved = self.preview.push_out_of_bones(points, [bone], 0.5)
        self.assertEqual(moved, 1)
        self.assertAlmostEqual(points[0].z, 5.5, places=4)  # nearest face + clearance
        self.assertEqual(points[1], Vector((20.0, 0.0, 0.0)))
        deep = [Vector((0.2, 0.1, 0.3))]                     # 4.7 below the nearest face
        self.assertEqual(self.preview.push_out_of_bones(deep, [bone], 0.5, max_depth=2.0), 0)
        self.assertEqual(deep[0], Vector((0.2, 0.1, 0.3)))  # too deep to have slipped in: left alone

    def test_inside_bone_survives_rays_through_edges(self):
        """A ray through an edge counts it twice; the 3-ray majority must still be right."""
        import bmesh
        from mathutils.bvhtree import BVHTree
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=10.0)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tree = BVHTree.FromBMesh(bm)
        bm.free()
        ray = self.preview._RAYS[0]
        # points placed so that the first ray passes through cube edges/vertices
        for p in (Vector((5, 5, 5)) - ray * 3.0, Vector((-5, 5, 5)) - ray * 2.0, Vector((0, 0, 0))):
            truth = all(abs(c) < 5.0 for c in p)
            self.assertEqual(self.preview.inside_bone(tree, p), truth, p)
        self.assertFalse(self.preview.inside_bone(tree, Vector((5, 5, 5)) + ray * 3.0))


if __name__ == "__main__":
    unittest.main()
