"""Solid final belly (volume_builder) and muscle-shape profiles.

Synthetic scene: the origin is a flat patch under a box "skull"; the
insertion wraps the top of a thin post (a coronoid process) like a sleeve,
the case where a loft closes over bone.
"""

import math
import sys
import unittest

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import test_metrics

M = "solid_left"


def link(name, bm, collection):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def box(lo, hi, cuts=6):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    for v in bm.verts:
        v.co = Vector(lo[a] + (v.co[a] + 0.5) * (hi[a] - lo[a]) for a in range(3))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def crested_skull():
    """One closed surface: a block (z 40-55) with two crests below it (x ±11-15, down to z 32)."""
    profile = [(-15, 55), (15, 55), (15, 40), (15, 32), (11, 32), (11, 40), (-11, 40), (-11, 32), (-15, 32),
               (-15, 40)]
    pieces = [(9, 6, 5, 2, 1, 0), (9, 8, 7, 6), (5, 4, 3, 2)]      # convex parts of the end caps
    bm = bmesh.new()
    front = [bm.verts.new((x, -10, z)) for x, z in profile]
    back = [bm.verts.new((x, 10, z)) for x, z in profile]
    for piece in pieces:
        bm.faces.new([front[i] for i in piece])
        bm.faces.new([back[i] for i in reversed(piece)])
    n = len(profile)
    for k in range(n):
        bm.faces.new([front[k], front[(k + 1) % n], back[(k + 1) % n], back[k]])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for _ in range(4):
        bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if e.calc_length() > 2.5], cuts=1)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sleeve(lo, hi, z_from):
    """Faces of a box above ``z_from``: sides and top (normals outwards)."""
    bm = box(lo, hi, cuts=7)
    bm.normal_update()
    below = [f for f in bm.faces if f.calc_center_median().z < z_from]
    bmesh.ops.delete(bm, geom=below, context='FACES')
    return bm


def flat_patch(x, y, z, normal_down):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=10, y_segments=10, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * x, v.co.y * y, z))
    if normal_down:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def boundary_curve(name, surface, collection):
    bm = bmesh.new()
    bm.from_mesh(surface.data)
    nbr = {}
    for e in bm.edges:
        if e.is_boundary:
            a, b = e.verts
            nbr.setdefault(a, []).append(b)
            nbr.setdefault(b, []).append(a)
    start = next(iter(nbr))
    loop, prev, cur = [start], None, start
    while True:
        nxt = next((v for v in nbr[cur] if v is not prev and v not in loop), None)
        if nxt is None:
            break
        loop.append(nxt)
        prev, cur = cur, nxt
    curve = bpy.data.curves.new(name, type='CURVE')
    spline = curve.splines.new('POLY')
    spline.points.add(len(loop) - 1)
    for p, v in zip(spline.points, loop):
        p.co = (*(surface.matrix_world @ v.co), 1.0)
    spline.use_cyclic_u = True
    bm.free()
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    return obj


def _bm(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


def inside(tree, p):
    direction = Vector((0.31, 0.57, 0.76)).normalized()
    hits, o = 0, p.copy()
    for _ in range(64):
        h = tree.ray_cast(o, direction)
        if h[0] is None:
            break
        hits += 1
        o = h[0] + direction * 1e-4
    return hits % 2 == 1


def world_tree(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


class SolidTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_metrics.load_addon()
        cls.preview = sys.modules[f"{test_metrics.MODULE_NAME}.preview"]
        cls.vb = sys.modules[f"{test_metrics.MODULE_NAME}.volume_builder"]
        cls.rings = sys.modules[f"{test_metrics.MODULE_NAME}.rings"]
        cls.tube = sys.modules[f"{test_metrics.MODULE_NAME}.tube"]
        cls.mr = sys.modules[f"{test_metrics.MODULE_NAME}.myo_record"]

    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for coll in list(bpy.data.collections):
            bpy.data.collections.remove(coll)
        self.preview._bone_trees.clear()
        scene = bpy.context.scene
        scene.unit_settings.scale_length = 0.001                 # 1 BU = 1 mm
        root = self.mr.get_root(create=True, scene=scene)
        self.coll = bpy.data.collections.new(M)
        root.children.link(self.coll)
        bones = bpy.data.collections.new("bones")
        scene.collection.children.link(bones)
        skull = crested_skull()
        self.skull = link("skull", skull, bones)
        self.post = link("post", box((-1.5, -1.5, -20), (1.5, 1.5, 8)), bones)
        self.origin = link(M + "_origin", flat_patch(10, 6, 40.0, normal_down=True), self.coll)
        self.insertion = link(M + "_insertion", sleeve((-1.5, -1.5, -20), (1.5, 1.5, 8), 2.0), self.coll)
        boundary_curve(M + "_origin_contour", self.origin, self.coll)
        boundary_curve(M + "_insertion_contour", self.insertion, self.coll)
        props = scene.myogen
        props.muscle_name = M
        props.origin_object, props.insertion_object = self.skull, self.post
        props.muscle_shape = 'FUSIFORM'
        props.use_controls = False
        props.ring_count = 3
        props.voxel_size_mm = 0.6
        props.attachment_thickness_mm = 0.0
        props.muscle_contour_resolution = 32
        props.muscle_curve_subdivisions = 12
        props.contour_matching = 'AUTO'
        props.muscle_connection_mode = 'FOLLOW_PATH'
        props.anchor_falloff = 0.15

    def tearDown(self):
        self.vb.stop_live(bpy.context)
        bpy.context.scene.unit_settings.scale_length = 1.0

    def generate(self):
        self.assertEqual(bpy.ops.myogen.muscle_mesh_generation(), {'FINISHED'})
        return self.coll.objects[M + "_muscle"]

    def path_points(self):
        path = self.coll.objects[M + "_curve"]
        return [path.matrix_world @ p.co for p in path.data.splines[0].bezier_points]

    # ---------------------------------------------------------------- pieces

    def test_surface_nets_sphere_is_closed_and_outward(self):
        import numpy as np
        n, r, voxel = 40, 8.0, 0.5
        axis = (np.arange(n) - n / 2) * voxel
        x, y, z = np.meshgrid(axis, axis, axis, indexing='ij')
        field = r - np.sqrt(x * x + y * y + z * z)
        verts, quads = self.vb.surface_nets(field, 0.0, (axis[0], axis[0], axis[0]), voxel)
        bm = bmesh.new()
        bv = [bm.verts.new(Vector(p)) for p in verts.tolist()]
        for q in quads.tolist():
            bm.faces.new([bv[i] for i in q])
        self.assertTrue(all(e.is_manifold for e in bm.edges))
        volume = bm.calc_volume(signed=True)
        self.assertAlmostEqual(volume / (4 / 3 * math.pi * r ** 3), 1.0, delta=0.03)
        bm.free()

    def test_outward_sign_follows_the_bone(self):
        self.assertEqual(self.preview.outward_sign(self.origin, self.skull), 1)
        self.assertEqual(self.preview.outward_sign(self.insertion, self.post), 1)
        flipped = link("flipped", flat_patch(10, 6, 40.0, normal_down=False), self.coll)
        self.assertEqual(self.preview.outward_sign(flipped, self.skull), -1)

    def test_path_starts_outside_the_bone(self):
        """The centroid of a sleeve lies inside the process; the default course must not."""
        skull, post = world_tree(self.skull), world_tree(self.post)
        for p in self.preview.default_path_points(bpy.context.scene.myogen, self.origin, self.insertion):
            self.assertFalse(inside(skull, p) or inside(post, p), p)

    def test_shape_section(self):
        pts = [Vector((6 * math.cos(a), 2 * math.sin(a), 0)) for a in (2 * math.pi * k / 24 for k in range(24))]
        T, pos = Vector((0, 0, 1)), Vector((1, 2, 3))
        same = self.preview.shape_section(pts, pos, T, 1.0)
        for a, b in zip(pts, same):
            self.assertLess((a + pos - b).length, 1e-5)
        flat = self.preview.shape_section(pts, pos, T, 1.0, flatness=0.2)
        self.assertAlmostEqual(max(abs((p - pos).y) for p in flat) / max(abs((p - pos).x) for p in flat), 0.2, 2)
        turned = self.preview.shape_section(pts, pos, T, 1.0, tilt=math.pi / 2)
        self.assertAlmostEqual(max(abs((p - pos).y) for p in turned), 6.0, 4)

    # ------------------------------------------------------------- the belly

    def assert_solid(self, belly):
        bm = bmesh.new()
        bm.from_mesh(belly.data)
        self.assertTrue(all(e.is_manifold for e in bm.edges), "belly is not closed/manifold")
        self.assertGreater(bm.calc_volume(signed=True), 0.0)
        bm.free()
        group = belly.vertex_groups.get(self.preview.ANCHORED_GROUP)
        anchored = {v.index for v in belly.data.vertices if any(g.group == group.index for g in v.groups)}
        self.assertTrue(anchored)
        for bone in (self.skull, self.post):
            tree = world_tree(bone)
            inside_free = [v.index for v in belly.data.vertices      # contact is not penetration
                           if v.index not in anchored and inside(tree, belly.matrix_world @ v.co)
                           and tree.find_nearest(belly.matrix_world @ v.co)[3] > 0.05]
            self.assertEqual(inside_free, [], f"free vertices inside {bone.name}")
        belly_tree = world_tree(belly)
        for surface in (self.origin, self.insertion):         # the attachments are covered
            far = max(belly_tree.find_nearest(surface.matrix_world @ v.co)[3] for v in surface.data.vertices)
            self.assertLess(far, 1.5)
        return belly_tree

    def test_solid_along_the_path(self):
        belly = self.generate()                                  # the default path is created
        self.assertFalse(self.coll.objects[M + "_curve"].get(self.preview.AUTO_PATH_KEY))
        tree = self.assert_solid(belly)
        self.assertTrue(inside(tree, Vector((0, 0, 20))))       # belly between the attachments
        self.assertFalse(inside(tree, Vector((0, 0, 6))))       # the process stays bone

    def fan_extent(self, obj, z, axis):
        """Extent of ``obj`` along world ``axis`` (0 = X, 1 = Y) within a slab around height ``z``."""
        co = [obj.matrix_world @ v.co for v in obj.data.vertices]
        vals = [p[axis] for p in co if abs(p.z - z) < 1.0]
        return max(vals) - min(vals) if vals else 0.0

    def test_fan_converges_from_the_whole_origin(self):
        props = bpy.context.scene.myogen
        props.muscle_shape = 'FAN'
        self.assertTrue(self.vb.is_fan(props))
        self.assertEqual(bpy.ops.myogen.muscle_preview_update(), {'FINISHED'})
        wire = self.coll.objects[M + self.vb.TUBE_SUFFIX]
        self.assertTrue(len(wire.data.edges) > 0 and len(wire.data.polygons) == 0)   # fibre courses
        self.assertEqual(bpy.ops.myogen.muscle_preview_stop(), {'FINISHED'})
        belly = self.generate()
        tree = self.assert_solid(belly)
        islands = self.vb._islands(_bm(belly))
        self.assertEqual(len(islands), 1)
        for corner in (Vector((8.0, 4.0, 38.0)), Vector((-8.0, -4.0, 38.0))):    # spreads over the origin
            self.assertTrue(inside(tree, corner), corner)
        self.assertTrue(inside(tree, Vector((0, 0, 20))))                         # joins the insertion
        self.assertFalse(inside(tree, Vector((0, 0, 6))))                         # the process stays bone
        self.assertFalse(inside(tree, Vector((13, 0, 36))))                       # the crest stays bone
        wide, narrow = self.fan_extent(belly, 34.0, 0), self.fan_extent(belly, 10.0, 0)
        self.assertGreater(wide, narrow * 1.3)                                    # converges

    def test_fan_rings_set_width_and_thickness(self):
        props = bpy.context.scene.myogen
        props.muscle_shape = 'FAN'
        props.ring_count = 3
        props.use_controls = True
        self.assertEqual(bpy.ops.myogen.muscle_preview_update(), {'FINISHED'})
        preview_obj = self.coll.objects[M + self.vb.PREVIEW_SUFFIX]
        ring_list = self.rings.ring_objects(self.coll, M)
        self.assertEqual(len(ring_list), 3)
        z_mid = ring_list[1].matrix_world.translation.z
        width0 = self.fan_extent(preview_obj, z_mid, 0)
        middle = ring_list[1]
        middle.scale = (middle.scale.x * 1.6, middle.scale.y, 1.0)              # wider fan
        bpy.context.view_layer.update()
        self.assertTrue(self.vb.flush_live(bpy.context))
        width1 = self.fan_extent(preview_obj, z_mid, 0)
        self.assertGreater(width1, width0 * 1.2)
        self.assertEqual(bpy.ops.myogen.muscle_preview_stop(), {'FINISHED'})

    @staticmethod
    def move_to(obj, location):
        m = obj.matrix_world.copy()
        m.translation = location
        obj.matrix_world = m

    def size_near(self, obj, path, u):
        """Largest distance of ``obj``'s vertices from the path point at ``u``, within a thin slab."""
        pts = self.tube.sample_path(path)
        tangents, _n = self.tube.frames(pts)
        k = round(u * (len(pts) - 1))
        c, t = pts[k], tangents[k]
        return max(((obj.matrix_world @ v.co) - c).length for v in obj.data.vertices
                   if abs(((obj.matrix_world @ v.co) - c).dot(t)) < 1.0)

    def test_rings_shape_the_belly_along_the_path(self):
        props = bpy.context.scene.myogen
        props.muscle_shape = 'PARALLEL'
        props.ring_count = 3
        self.assertEqual(bpy.ops.myogen.muscle_preview_update(), {'FINISHED'})
        path = self.coll.objects[M + "_curve"]
        self.assertIsNotNone(self.coll.objects.get(M + self.vb.TUBE_SUFFIX))      # instant wire tube
        self.assertEqual(self.rings.ring_objects(self.coll, M), [])                # rings are optional
        props.use_controls = True
        self.assertTrue(self.vb.flush_live(bpy.context))
        ring_list = self.rings.ring_objects(self.coll, M)
        self.assertEqual(len(ring_list), 3)
        self.assertTrue(all(ring_list[0].lock_location))                            # ends fixed
        self.assertFalse(any(ring_list[1].lock_location))                           # middle slides
        preview_obj = self.coll.objects[M + self.vb.PREVIEW_SUFFIX]

        middle = ring_list[1]
        middle.scale = (middle.scale.x * 2.0, middle.scale.y * 2.0, 1.0)   # a bulge in the middle
        bpy.context.view_layer.update()
        self.assertTrue(self.vb.flush_live(bpy.context))
        self.assertGreater(self.size_near(preview_obj, path, 0.5), self.size_near(preview_obj, path, 0.85) * 1.3)

        pts = self.tube.sample_path(path)                            # slide it towards the origin
        self.move_to(middle, pts[round(0.25 * (len(pts) - 1))])
        bpy.context.view_layer.update()
        self.assertTrue(self.vb.flush_live(bpy.context))
        u = self.rings.ring_sections(self.rings.ring_objects(self.coll, M), pts)[1][0]
        self.assertAlmostEqual(u, 0.25, delta=0.05)
        self.assertGreater(self.size_near(preview_obj, path, 0.25), self.size_near(preview_obj, path, 0.7) * 1.3)

        self.move_to(middle, middle.matrix_world.translation + Vector((15.0, 0.0, 0.0)))   # pulled off the path
        bpy.context.view_layer.update()
        self.assertTrue(self.vb.flush_live(bpy.context))           # snapped back onto it, same place
        on_path = min((middle.matrix_world.translation - p).length for p in pts)
        self.assertLess(on_path, 1.0)
        u = self.rings.ring_sections(self.rings.ring_objects(self.coll, M), pts)[1][0]
        self.assertAlmostEqual(u, 0.25, delta=0.05)

        for bp in path.data.splines[0].bezier_points:                 # bend the path: the belly follows
            bp.handle_left_type = bp.handle_right_type = 'FREE'
            bp.handle_left.x += 12.0
            bp.handle_right.x += 12.0
        bpy.context.view_layer.update()
        self.assertTrue(self.vb.flush_live(bpy.context))
        bent = self.tube.sample_path(path)
        self.assertLess(min((self.rings.ring_objects(self.coll, M)[1].matrix_world.translation - p).length
                            for p in bent), 1.0)                     # rings stay on the new path

        props.use_controls = False                                   # off: rings hidden, default profile
        self.assertTrue(self.vb.flush_live(bpy.context))
        self.assertTrue(all(r.hide_get() for r in self.rings.ring_objects(self.coll, M)))
        props.use_controls = True
        self.assertTrue(self.vb.flush_live(bpy.context))
        self.assertEqual(bpy.ops.myogen.muscle_preview_stop(), {'FINISHED'})
        belly = self.generate()
        self.assertIsNone(self.coll.objects.get(M + self.vb.PREVIEW_SUFFIX))
        self.assertIsNone(self.coll.objects.get(M + self.vb.TUBE_SUFFIX))
        self.assertEqual(self.rings.ring_objects(self.coll, M), [])       # helpers removed
        self.assertIsNone(bpy.data.curves.get(self.rings.RING_CURVE))
        self.assertIsNotNone(self.coll.objects.get(M + "_curve"))           # the path stays
        self.assertTrue(all(e.is_manifold for e in _bm(belly).edges))
        rows, _scene = sys.modules[f"{test_metrics.MODULE_NAME}.muscle_metrics"].compute_muscles(bpy.context)
        row = next(r for r in rows if r["collection"] == M)
        length = sum((b - a).length for a, b in zip(bent[:-1], bent[1:])) / 1000.0
        self.assertAlmostEqual(row["myo_path_length_m"], length, delta=0.02 * length)   # the user's path

    def test_regenerating_replaces_the_belly(self):
        first = self.generate()
        bpy.context.scene.myogen.muscle_shape = 'FAN'
        second = self.generate()
        self.assertIs(first, second)
        self.assertEqual(len([o for o in self.coll.objects if o.name.startswith(M + "_muscle")]), 1)


if __name__ == "__main__":
    unittest.main()
