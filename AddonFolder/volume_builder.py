"""Solid muscle belly: (tube or fibres along the path ∪ attachment layers) − bones.

The belly follows the user's path ``<M>_curve``: a tube (:mod:`tube`) sized
and turned by the section rings on the path (:mod:`rings`) or by the muscle
type's profile, or, for fan-shaped muscles, the union of fibres from the
whole origin attachment to the insertion (:mod:`fan`). Built on a voxel
grid, so it is always closed, lies on the outer face of the bones and never
crosses itself:

1. occupancy of the tube by +Z scanlines (winding number: overlapping parts
   are a union) or of the fibres (capsules), Gaussian-smoothed;
2. a layer over each attachment, up to the minimum thickness outwards from
   its bone (:func:`attachment_layer`), so the whole attachment is covered;
3. minus the origin and insertion bones (ray parity);
4. surface nets + voxel remesh (closed, manifold);
5. vertices next to an attachment are snapped onto it and anchored
   (weight 0 in ``preview.DEFORM_GROUP``); the rest are smoothed and kept
   outside the bones.

The live preview (:func:`start_live`) is this belly at draft resolution; a
wire tube (``<M>_tube``) follows the path and the rings at once and the
solid follows after ``LIVE_DELAY`` s.
"""

import math
import time

import bmesh
import bpy
import numpy as np
from bpy.app.handlers import persistent
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import myo_record
from . import fan
from . import preview
from . import rings
from . import tube

#: Automatic voxel size = largest dimension of the muscle / this.
AUTO_VOXELS_ACROSS = 110
#: Upper bound of voxels along any axis.
MAX_VOXELS_ACROSS = 400
#: The automatic voxel is at most the smallest section radius / this.
VOXELS_PER_RADIUS = 6.0
#: For fan muscles (overlapping fibres) the fibre radius / this is enough.
VOXELS_PER_FIBRE_RADIUS = 3.0
#: Upper bound of grid cells (keeps the time bounded on large muscles).
MAX_CELLS = 8_000_000
#: Automatic attachment thickness along the path, in voxels.
AUTO_THICKNESS_VOXELS = 3.0
#: with the origin's outward normal are on another side (far side of a crest).
SIDE_MIN_COS = 0.0
#: Smoothing passes on the free surface (removes voxel terracing).
SMOOTH_PASSES = 3
#: A voxel is in the layer over an attachment if it lies within this cosine
#: of the outward normal at its nearest attachment point (60°).
LAYER_CONE_COS = 0.5
#: Final remesh voxel, as a fraction of the occupancy voxel.
REMESH_FACTOR = 0.75
#: Free vertices are pushed out of a bone only from at most this deep (voxels):
#: the solid is already cut by the bones, smoothing moves vertices by less.
MAX_PUSH_VOXELS = 3.0
#: Vertices closer than this (in voxels) to an attachment are snapped onto it.
SNAP_VOXELS = 1.0
_UP = Vector((0.0, 0.0, 1.0))


# --------------------------------------------------------------------------
# Occupancy
# --------------------------------------------------------------------------

def _column_crossings(tree, x, y, z_start, z_end, eps):
    """Crossings of the +Z ray at (x, y): list of ``(z, entering)``."""
    out = []
    origin = Vector((x, y, z_start))
    while origin.z < z_end:
        loc, normal, _index, _dist = tree.ray_cast(origin, _UP, z_end - origin.z)
        if loc is None:
            break
        out.append((loc.z, normal.z < 0.0))
        origin = Vector((x, y, loc.z + eps))
    return out


def occupancy(tree, xs, ys, zs, z_start, signed, columns=None):
    """Voxel occupancy of a closed mesh by +Z scanlines.

    :arg tree: World-space BVH of the mesh.
    :type tree: :class:`mathutils.bvhtree.BVHTree`
    :arg xs: Voxel-centre X coordinates.
    :type xs: :class:`numpy.ndarray`
    :arg ys: Voxel-centre Y coordinates.
    :type ys: :class:`numpy.ndarray`
    :arg zs: Voxel-centre Z coordinates (ascending).
    :type zs: :class:`numpy.ndarray`
    :arg z_start: Z where rays start; must be below the mesh (outside it).
    :type z_start: float
    :arg signed: True: inside = positive winding number (needs consistent
       outward normals; overlapping parts are a union). False: ray parity
       (needs a closed mesh only).
    :type signed: bool
    :arg columns: Optional boolean (len(xs), len(ys)) mask of columns to test.
    :type columns: :class:`numpy.ndarray`
    :return: Boolean array (len(xs), len(ys), len(zs)).
    :rtype: :class:`numpy.ndarray`
    """
    occ = np.zeros((len(xs), len(ys), len(zs)), dtype=bool)
    z_end = float(zs[-1]) + 1.0
    eps = max(1e-6, (float(zs[1] - zs[0]) if len(zs) > 1 else 1.0) * 1e-3)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            if columns is not None and not columns[i, j]:
                continue
            hits = _column_crossings(tree, float(x), float(y), z_start, z_end, eps)
            if not hits:
                continue
            hz = np.array([h[0] for h in hits])
            if signed:
                steps = np.array([1 if h[1] else -1 for h in hits])
                state = np.concatenate(([0], np.cumsum(steps))) > 0
            else:
                state = np.arange(len(hits) + 1) % 2 == 1
            occ[i, j, :] = state[np.searchsorted(hz, zs)]
    return occ


def _bm_tree(bm):
    bm.normal_update()
    return BVHTree.FromBMesh(bm)


def attachment_layer(surface_obj, bone_obj, thickness, xs, ys, zs):
    """Voxels of the muscle layer over an attachment, up to ``thickness`` outwards.

    A voxel belongs to the layer when its nearest point on the attachment is
    closer than ``thickness`` and it lies on the outer side of the surface
    (within ``LAYER_CONE_COS`` of the outward normal there) or within one voxel
    of it. Unlike offsetting the surface as a mesh, this never folds, however
    thick the layer or rough the scanned surface; the edges stay at the
    attachment's border instead of spreading sideways.

    :arg surface_obj: Attachment surface.
    :type surface_obj: :class:`bpy.types.Object`
    :arg bone_obj: Bone it lies on (orients the normals, :func:`preview.outward_sign`).
    :type bone_obj: :class:`bpy.types.Object`
    :arg thickness: Layer thickness (Blender units).
    :type thickness: float
    :arg xs: Voxel-centre X coordinates (evenly spaced).
    :type xs: :class:`numpy.ndarray`
    :arg ys: Voxel-centre Y coordinates.
    :type ys: :class:`numpy.ndarray`
    :arg zs: Voxel-centre Z coordinates.
    :type zs: :class:`numpy.ndarray`
    :return: Boolean array (len(xs), len(ys), len(zs)).
    :rtype: :class:`numpy.ndarray`
    """
    voxel = float(xs[1] - xs[0]) if len(xs) > 1 else thickness
    shape = (len(xs), len(ys), len(zs))
    layer = np.zeros(shape, dtype=bool)
    bm = bmesh.new()
    bm.from_mesh(surface_obj.data)
    bm.transform(surface_obj.matrix_world)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=(max(surface_obj.dimensions) or 1.0) * 1e-6)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    sign = preview.outward_sign(surface_obj, bone_obj)
    # Candidates: voxels within the attachment's bounding box grown by the
    # thickness, pre-filtered by a coarse dilation of the voxels it touches.
    pts = np.array([v.co for v in bm.verts] + [f.calc_center_median() for f in bm.faces])
    bm.free()
    grid0 = np.array((xs[0], ys[0], zs[0]))
    ijk = np.clip(np.rint((pts - grid0) / voxel).astype(int), 0, np.array(shape) - 1)
    near = np.zeros(shape, dtype=bool)
    near[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    for _ in range(int(math.ceil(thickness / voxel)) + 1):
        near = _dilate(near)
    cand = np.argwhere(near)
    for i, j, k in cand.tolist():
        p = Vector((xs[i], ys[j], zs[k]))
        q, n, _index, d = tree.find_nearest(p, thickness)
        if q is None:
            continue
        if d <= voxel or (p - q).dot(n) * sign >= LAYER_CONE_COS * d:
            layer[i, j, k] = True
    return layer


def _dilate(mask):
    """6-neighbour binary dilation by one voxel."""
    out = mask.copy()
    out[1:] |= mask[:-1]
    out[:-1] |= mask[1:]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    out[:, :, 1:] |= mask[:, :, :-1]
    out[:, :, :-1] |= mask[:, :, 1:]
    return out


def _world_coords(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    m = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]


def smoothing_passes(sigma, voxel):
    """Box-blur passes giving a Gaussian of standard deviation ``sigma``.

    :arg sigma: Standard deviation (same unit as ``voxel``).
    :type sigma: float
    :arg voxel: Grid spacing.
    :type voxel: float
    :rtype: int
    """
    return max(1, int(math.ceil(1.5 * (sigma / voxel) ** 2)))


# --------------------------------------------------------------------------
# Meshing
# --------------------------------------------------------------------------

def blur(field):
    """3-tap box blur along each axis (zero outside).

    :arg field: Scalar grid.
    :type field: :class:`numpy.ndarray`
    :return: Blurred grid, same shape.
    :rtype: :class:`numpy.ndarray`
    """
    for axis in range(3):
        padded = np.pad(field, [(1, 1) if a == axis else (0, 0) for a in range(3)])
        lo = [slice(None)] * 3
        mid = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis], mid[axis], hi[axis] = slice(0, -2), slice(1, -1), slice(2, None)
        field = (padded[tuple(lo)] + padded[tuple(mid)] + padded[tuple(hi)]) / 3.0
    return field


_CORNERS = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
_EDGES = [(a, b) for a in range(8) for b in range(a + 1, 8)
          if sum(x != y for x, y in zip(_CORNERS[a], _CORNERS[b])) == 1]


def surface_nets(field, iso, origin, voxel):
    """Quad mesh of the iso-surface of a scalar grid (naive surface nets).

    One vertex per cell crossed by the surface, at the mean of the edge
    crossings; one quad per grid edge crossing the surface, oriented outwards
    (from values above ``iso`` to below). The field must be below ``iso`` on
    its border.

    :arg field: Values at grid points, shape (X, Y, Z).
    :type field: :class:`numpy.ndarray`
    :arg iso: Iso-value; inside is ``field > iso``.
    :type iso: float
    :arg origin: World position of grid point (0, 0, 0).
    :type origin: sequence of 3 float
    :arg voxel: Grid spacing.
    :type voxel: float
    :return: ``(verts, quads)``: (N, 3) float and (M, 4) int arrays.
    :rtype: tuple
    """
    X, Y, Z = field.shape
    inside = field > iso
    acc = np.zeros((X - 1, Y - 1, Z - 1, 3))
    cnt = np.zeros((X - 1, Y - 1, Z - 1))
    corner = [field[c[0]:X - 1 + c[0], c[1]:Y - 1 + c[1], c[2]:Z - 1 + c[2]] for c in _CORNERS]
    for a, b in _EDGES:
        fa, fb = corner[a], corner[b]
        crossing = (fa > iso) != (fb > iso)
        if not crossing.any():
            continue
        denom = np.where(fb == fa, 1.0, fb - fa)
        t = np.clip((iso - fa) / denom, 0.0, 1.0)
        ca, cb = np.array(_CORNERS[a], float), np.array(_CORNERS[b], float)
        pos = ca + t[..., None] * (cb - ca)
        acc[crossing] += pos[crossing]
        cnt[crossing] += 1
    active = cnt > 0
    vid = -np.ones(active.shape, dtype=np.int64)
    vid[active] = np.arange(int(active.sum()))
    verts = (np.argwhere(active) + acc[active] / cnt[active][:, None]) * voxel + np.asarray(origin)

    quads = []
    # edges along X between points (i,j,k) and (i+1,j,k), j,k interior
    s0, s1 = inside[:-1, 1:-1, 1:-1], inside[1:, 1:-1, 1:-1]
    m = s0 != s1
    q = np.stack([vid[:, :-1, :-1], vid[:, 1:, :-1], vid[:, 1:, 1:], vid[:, :-1, 1:]], axis=-1)
    quads.append(np.where(s0[m][:, None], q[m], q[m][:, ::-1]))
    # edges along Y
    s0, s1 = inside[1:-1, :-1, 1:-1], inside[1:-1, 1:, 1:-1]
    m = s0 != s1
    q = np.stack([vid[:-1, :, :-1], vid[:-1, :, 1:], vid[1:, :, 1:], vid[1:, :, :-1]], axis=-1)
    quads.append(np.where(s0[m][:, None], q[m], q[m][:, ::-1]))
    # edges along Z
    s0, s1 = inside[1:-1, 1:-1, :-1], inside[1:-1, 1:-1, 1:]
    m = s0 != s1
    q = np.stack([vid[:-1, :-1, :], vid[1:, :-1, :], vid[1:, 1:, :], vid[:-1, 1:, :]], axis=-1)
    quads.append(np.where(s0[m][:, None], q[m], q[m][:, ::-1]))
    return verts, np.concatenate(quads)


def manifold_remesh(verts, quads, voxel):
    """Closed manifold mesh from surface-nets output (OpenVDB voxel remesh).

    Surface nets can leave a few non-manifold edges where the field is
    ambiguous (sharp bone edges); Blender's voxel remesher rebuilds the
    surface from its level set, which is always manifold.

    :arg verts: (N, 3) vertex positions.
    :type verts: :class:`numpy.ndarray`
    :arg quads: (M, 4) quad indices.
    :type quads: :class:`numpy.ndarray`
    :arg voxel: Remesh voxel size.
    :type voxel: float
    :return: New bmesh (caller frees it).
    :rtype: :class:`bmesh.types.BMesh`
    """
    mesh = bpy.data.meshes.new("myo_remesh_tmp")
    mesh.vertices.add(len(verts))
    mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    mesh.loops.add(4 * len(quads))
    mesh.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
    mesh.polygons.add(len(quads))
    mesh.polygons.foreach_set("loop_start", np.arange(0, 4 * len(quads), 4, dtype=np.int32))
    mesh.polygons.foreach_set("loop_total", np.full(len(quads), 4, dtype=np.int32))
    mesh.update()
    mesh.remesh_voxel_size = voxel
    mesh.use_remesh_fix_poles = False
    obj = bpy.data.objects.new("myo_remesh_tmp", mesh)
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
        try:
            bpy.ops.object.voxel_remesh()
        except RuntimeError:
            pass                                             # keep the surface-nets mesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    for m in {mesh, data}:
        if m.users == 0:
            bpy.data.meshes.remove(m)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=voxel * 1e-3)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    return bm


# --------------------------------------------------------------------------
# Belly
# --------------------------------------------------------------------------

def _islands(bm):
    seen, islands = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, island = [v], []
        seen.add(v)
        while stack:
            w = stack.pop()
            island.append(w)
            for e in w.link_edges:
                u = e.other_vert(w)
                if u not in seen:
                    seen.add(u)
                    stack.append(u)
        islands.append(island)
    return islands


#: Muscle types built from fibres spread over the origin (:mod:`fan`).
FAN_SHAPES = {'FAN'}


def is_fan(props):
    """True if the current muscle type is built from fibres (fan-shaped muscles).

    :arg props: Scene settings.
    :type props: :class:`properties.MyoGeneratorProperties`
    :rtype: bool
    """
    return props.muscle_shape in FAN_SHAPES


def build_belly(context, tube_bm, origin_surface, insertion_surface, bones, report=None, fibres=None,
                voxel_scale=1.0, min_radius=None):
    """Solid belly from the tube or the fibres, the attachments and the bones.

    Body = the tube along the muscle path (:func:`tube.path_tube`) or, for fan
    muscles, the fibres from the origin to the insertion (:func:`fan.fibres`,
    rasterised by :func:`fan.occupancy`). The body is smoothed by
    ``surface_smoothing_mm`` **before** the bones are cut (so the face on the
    bone stays exact), joined to a layer over each attachment
    (:func:`attachment_layer`), and the bones are subtracted.

    :arg context: Context (scene settings ``scene.myogen``; unit scale).
    :type context: :class:`bpy.types.Context`
    :arg tube_bm: World-space tube along the path, or None when ``fibres`` is given; not freed.
    :type tube_bm: :class:`bmesh.types.BMesh`
    :arg origin_surface: Origin attachment surface.
    :type origin_surface: :class:`bpy.types.Object`
    :arg insertion_surface: Insertion attachment surface.
    :type insertion_surface: :class:`bpy.types.Object`
    :arg bones: ``(origin_bone, insertion_bone)``; None entries are skipped.
    :type bones: sequence of :class:`bpy.types.Object`
    :arg report: Optional dict filled with ``voxel`` (BU), ``grid``,
       ``seconds``, ``anchored``, ``islands_removed``, ``pieces`` (kept
       disconnected parts) and ``stages`` (seconds per stage).
    :type report: dict
    :arg fibres: ``(courses, radii)`` from :func:`fan.fibres`, or None.
    :type fibres: tuple
    :arg voxel_scale: Multiplies the voxel size (> 1 = faster draft).
    :type voxel_scale: float
    :arg min_radius: Smallest section radius (Blender units): the automatic
       voxel is at most ``min_radius / VOXELS_PER_RADIUS``, so thin muscles
       keep their detail.
    :type min_radius: float
    :return: ``(bm, weights)``: world-space bmesh (caller frees it) and per
       vertex weights (0 = anchored on an attachment, 1 = free).
    :rtype: tuple
    :raises ValueError: If an attachment is missing or the solid is empty.
    """
    started = time.time()
    stages = [('start', started)]
    props = context.scene.myogen
    bu_per_mm = 1.0 / (1000.0 * myo_record.metres_per_unit(context.scene))
    surfaces = [(s, b) for s, b in zip((origin_surface, insertion_surface), bones) if s is not None]
    bone_objs = list({b for b in bones if b is not None and b.type == 'MESH'})
    if origin_surface is None or insertion_surface is None:
        raise ValueError("both attachments are needed")
    if fibres is not None:
        courses, radii = fibres
        body_pts = courses.reshape(-1, 3)
        body_pad = float(radii.max())
    else:
        body_pts = np.array([v.co for v in tube_bm.verts])
        body_pad = 0.0
    allp = np.concatenate([body_pts, _world_coords(origin_surface), _world_coords(insertion_surface)])
    lo, hi = Vector(allp.min(0) - body_pad), Vector(allp.max(0) + body_pad)
    size = max(hi - lo)
    auto = size / AUTO_VOXELS_ACROSS
    if min_radius:
        auto = min(auto, min_radius / (VOXELS_PER_FIBRE_RADIUS if fibres is not None else VOXELS_PER_RADIUS))
    voxel = props.voxel_size_mm * bu_per_mm if props.voxel_size_mm > 0 else auto
    extent = hi - lo
    budget = (max(extent.x, 1e-9) * max(extent.y, 1e-9) * max(extent.z, 1e-9) / MAX_CELLS) ** (1.0 / 3.0)
    voxel = max(voxel, size / MAX_VOXELS_ACROSS, budget) * voxel_scale
    thickness = (props.attachment_thickness_mm * bu_per_mm if props.attachment_thickness_mm > 0
                 else AUTO_THICKNESS_VOXELS * voxel)
    sigma = props.surface_smoothing_mm * bu_per_mm
    pad = thickness + 3 * voxel + 2 * sigma
    lo -= Vector((pad, pad, pad))
    hi += Vector((pad, pad, pad))
    jitter = voxel * 0.0137                                 # avoid rays through mesh vertices
    xs = np.arange(lo.x, hi.x, voxel) + jitter
    ys = np.arange(lo.y, hi.y, voxel) + 0.7 * jitter
    zs = np.arange(lo.z, hi.z, voxel)
    z_start = lo.z - voxel
    shape = (len(xs), len(ys), len(zs))

    link = np.zeros(shape, dtype=bool)                      # layers over the attachments
    for s_obj, b_obj in surfaces:
        link |= attachment_layer(s_obj, b_obj, thickness, xs, ys, zs)
    if fibres is not None:
        body = fan.occupancy(courses, radii, xs, ys, zs)
    else:
        body = occupancy(_bm_tree(tube_bm), xs, ys, zs, z_start, signed=True)

    stages.append(('occupancy', time.time()))
    columns = (body | link).any(axis=2)
    bone = np.zeros(shape, dtype=bool)
    for b in bone_objs:
        bone_low = min((b.matrix_world @ Vector(c)).z for c in b.bound_box) - voxel
        bone |= occupancy(preview._bone_tree(b), xs, ys, zs, min(z_start, bone_low), signed=False, columns=columns)

    stages.append(('bones', time.time()))
    # Smooth the body (outer surface) before cutting the bone, so the face on
    # the bone stays exact; the thin attachment layers are only lightly blurred.
    field = body.astype(np.float32)
    for _ in range(smoothing_passes(sigma, voxel) if sigma > 0 else 0):
        field = blur(field)
    field = np.maximum(field, blur(link.astype(np.float32)))
    field[bone] = 0.0
    if not (field > 0.5).any():
        raise ValueError("the solid belly is empty")
    field = blur(np.pad(field, 2))
    stages.append(('field', time.time()))
    origin = (xs[0] - 2 * voxel, ys[0] - 2 * voxel, zs[0] - 2 * voxel)
    verts, quads = surface_nets(field, 0.5, origin, voxel)

    bm = manifold_remesh(verts, quads, REMESH_FACTOR * voxel)

    stages.append(('mesh', time.time()))
    # Anchor: snap vertices next to an attachment onto it.
    attach = bmesh.new()
    for s, _b in surfaces:
        tmp = bmesh.new()
        tmp.from_mesh(s.data)
        tmp.transform(s.matrix_world)
        vmap = {v: attach.verts.new(v.co) for v in tmp.verts}
        for f in tmp.faces:
            try:
                attach.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                pass
        tmp.free()
    attach_tree = _bm_tree(attach)
    anchored = set()
    for v in bm.verts:
        hit = attach_tree.find_nearest(v.co, SNAP_VOXELS * voxel)
        if hit[0] is not None:
            v.co = hit[0]
            anchored.add(v)
    attach.free()

    stages.append(('anchor', time.time()))
    # Keep the pieces that reach an attachment (or the largest one).
    islands = _islands(bm)
    keep = [isl for isl in islands if any(v in anchored for v in isl)] or [max(islands, key=len)]
    keep_set = {v for isl in keep for v in isl}
    dropped = [v for v in bm.verts if v not in keep_set]
    if dropped:
        bmesh.ops.delete(bm, geom=dropped, context='VERTS')
    anchored = {v for v in anchored if v.is_valid}

    stages.append(('islands', time.time()))
    free = [v for v in bm.verts if v not in anchored]
    if free:
        for _ in range(SMOOTH_PASSES):
            bmesh.ops.smooth_vert(bm, verts=free, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        clearance = props.bone_clearance_mm * bu_per_mm
        preview.push_out_of_bones(free, [b for b in bones if b is not None], clearance,
                                  max_depth=MAX_PUSH_VOXELS * voxel)
    stages.append(('smooth_push', time.time()))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.index_update()
    weights = [0.0 if v in anchored else 1.0 for v in bm.verts]
    if report is not None:
        report.update(voxel=voxel, grid=(len(xs), len(ys), len(zs)), seconds=time.time() - started,
                      anchored=len(anchored), islands_removed=len(islands) - len(keep), pieces=len(keep),
                      stages={b[0]: round(b[1] - a[1], 2) for a, b in zip(stages[:-1], stages[1:])})
    return bm, weights


#: Suffix of the preview object (``<M>_preview``): the solid belly at draft resolution.
PREVIEW_SUFFIX = "_preview"
#: Suffix of the wire tube (``<M>_tube``) that follows the path and the rings at once.
TUBE_SUFFIX = "_tube"
#: Draft voxel factor of the live preview (about 4-6x faster than the final mesh).
DRAFT_VOXEL_SCALE = 1.8
#: Seconds without changes before the live solid preview rebuilds.
LIVE_DELAY = 0.6
#: Fibres drawn in the wire of a fan muscle.
WIRE_FIBRES = 40
#: Seconds before the wire tube follows a change.
TUBE_DELAY = 0.02


def ensure_path(context, muscle_name, coll, objs):
    """The muscle path ``<M>_curve``; the default one is created when missing.

    The path is the user's: it is never rewritten here (see the *Reset Path*
    operator).

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg coll: Muscle collection.
    :type coll: :class:`bpy.types.Collection`
    :arg objs: Muscle objects (:func:`preview.muscle_objects`).
    :type objs: dict
    :rtype: :class:`bpy.types.Object`
    """
    path = coll.objects.get(muscle_name + "_curve")
    if path is None or path.type != 'CURVE':
        path = preview.write_path(coll, muscle_name,
                                  preview.default_path_points(context.scene.myogen, objs["origin"], objs["insertion"]))
    return path


def muscle_sections(context, muscle_name, coll, objs, path, points):
    """Sections of the belly along the path: from the rings, or the type's default profile.

    With *Shape with rings* on, the rings are created when missing: for a
    belly from the type's profile (:func:`tube.default_profile`), for a fan
    from its natural width, thickness and orientation (:func:`fan.fibres`).

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg coll: Muscle collection.
    :type coll: :class:`bpy.types.Collection`
    :arg objs: Muscle objects.
    :type objs: dict
    :arg path: The muscle path.
    :type path: :class:`bpy.types.Object`
    :arg points: Arc-length samples of the path.
    :type points: list of :class:`mathutils.Vector`
    :return: ``(sections, rings)``; ``sections`` is None for a fan without
       rings (natural fan); ``rings`` is empty when rings are off.
    :rtype: tuple
    """
    props = context.scene.myogen
    fan_type = is_fan(props)
    if not props.use_controls:
        return (None if fan_type else tube.default_profile(objs["origin"], objs["insertion"],
                                                           props.muscle_shape)), []
    ring_list = rings.ring_objects(coll, muscle_name)
    if len(ring_list) < 2:
        if fan_type:
            ring_list = rings.create_rings(coll, muscle_name, path, natural_fan_sections(context, objs, points))
        else:
            ring_list = rings.default_rings(coll, muscle_name, path, objs["origin"], objs["insertion"],
                                            props.muscle_shape, props.ring_count)
    return rings.ring_sections(ring_list, points), ring_list


def natural_fan_sections(context, objs, points):
    """Ring sections ``(u, half_width, half_thickness, angle)`` of the natural fan.

    :arg context: Context (``scene.myogen``: bones, ring count).
    :type context: :class:`bpy.types.Context`
    :arg objs: Muscle objects (attachments).
    :type objs: dict
    :arg points: Arc-length samples of the path.
    :type points: list of :class:`mathutils.Vector`
    :rtype: list of tuple
    """
    props = context.scene.myogen
    _c, _r, natural = fan.fibres(points, objs["origin"], objs["insertion"],
                                 (props.origin_object, props.insertion_object), fan.DRAFT_FIBRES)
    h = fan.default_thickness(points)
    count = max(2, props.ring_count)
    secs = []
    for k in range(count):
        u = k / (count - 1)
        j = min(range(len(natural)), key=lambda i: abs(natural[i][0] - u))
        secs.append((u, max(natural[j][1], h(u)), h(u), natural[j][2]))
    return secs


def _inputs(context, muscle_name):
    coll, objs = preview.muscle_objects(context, muscle_name)
    if coll is None:
        raise ValueError(f"muscle collection '{muscle_name}' not found")
    for key in ("origin", "insertion"):
        if objs.get(key) is None or not objs[key].data.polygons:
            raise ValueError(f"the {key} surface is missing")
    path = ensure_path(context, muscle_name, coll, objs)
    points = tube.sample_path(path)
    sections, ring_list = muscle_sections(context, muscle_name, coll, objs, path, points)
    return coll, objs, path, points, sections, ring_list


def _body(context, objs, points, sections, draft):
    """``(tube_bm, fibres, min_radius)`` of the current muscle type."""
    props = context.scene.myogen
    if is_fan(props):
        courses, radii, _natural = fan.fibres(points, objs["origin"], objs["insertion"],
                                              (props.origin_object, props.insertion_object),
                                              fan.DRAFT_FIBRES if draft else fan.FIBRES, sections=sections)
        return None, (courses, radii), float(radii.min())
    return tube.path_tube(points, sections), None, min(min(sec[1], sec[2]) for sec in sections)


def solid_mesh(context, muscle_name, report=None, voxel_scale=1.0):
    """Build the solid belly of a muscle into a new mesh datablock (world space).

    Body = the tube along the path (:func:`tube.path_tube`, sections from the
    rings or the type's profile) or, for fan muscles, the fibres from the
    origin to the insertion (:func:`fan.fibres`). The rings are put back
    perpendicular to the path afterwards.

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg muscle_name: Muscle (collection ``muscles/<muscle_name>``).
    :type muscle_name: str
    :arg report: Optional dict, see :func:`build_belly`.
    :type report: dict
    :arg voxel_scale: See :func:`build_belly`; > 1 also uses fewer fibres.
    :type voxel_scale: float
    :return: ``(mesh, weights)``.
    :rtype: tuple
    :raises ValueError: If the muscle or its inputs are missing, or the solid is empty.
    """
    props = context.scene.myogen
    report = {} if report is None else report
    coll, objs, path, points, sections, ring_list = _inputs(context, muscle_name)
    tube_bm, fibres, min_radius = _body(context, objs, points, sections, voxel_scale > 1.0)
    try:
        bm, weights = build_belly(context, tube_bm, objs["origin"], objs["insertion"],
                                  (props.origin_object, props.insertion_object), report,
                                  fibres=fibres, voxel_scale=voxel_scale, min_radius=min_radius)
    finally:
        if tube_bm is not None:
            tube_bm.free()
    if ring_list:
        rings.align_rings(ring_list, points, sections)
    _remember_state(context)
    mesh = bpy.data.meshes.new(muscle_name + "_muscle")
    bm.to_mesh(mesh)
    bm.free()
    return mesh, weights


def update_tube(context, muscle_name):
    """Rewrite the wire ``<M>_tube`` from the current path and rings (instant feedback).

    A belly shows its tube; a fan shows a subset of its fibres (their courses).

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :return: The tube object.
    :rtype: :class:`bpy.types.Object`
    :raises ValueError: See :func:`solid_mesh`.
    """
    coll, objs, _path, points, sections, _rings = _inputs(context, muscle_name)
    mesh = bpy.data.meshes.new(muscle_name + TUBE_SUFFIX)
    if is_fan(context.scene.myogen):
        courses, _radii, _natural = fan.fibres(points, objs["origin"], objs["insertion"],
                                               (context.scene.myogen.origin_object,
                                                context.scene.myogen.insertion_object),
                                               WIRE_FIBRES, sections=sections)
        verts = courses.reshape(-1, 3).tolist()
        n = courses.shape[1]
        edges = [(f * n + k, f * n + k + 1) for f in range(courses.shape[0]) for k in range(n - 1)]
        mesh.from_pydata(verts, edges, [])
    else:
        bm = tube.path_tube(points, sections)
        bm.to_mesh(mesh)
        bm.free()
    obj = coll.objects.get(muscle_name + TUBE_SUFFIX)
    if obj is None:
        obj = bpy.data.objects.new(muscle_name + TUBE_SUFFIX, mesh)
        coll.objects.link(obj)
        obj.display_type = 'WIRE'
        obj.hide_select = True
        obj[myo_record.ROLE_KEY] = "tube"
    else:
        _replace_mesh(obj, mesh)
    return obj


def _replace_mesh(obj, mesh):
    old = obj.data
    obj.data = mesh
    if old is not None and old.users == 0:
        bpy.data.meshes.remove(old)
    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)


def update_preview(context, muscle_name, report=None):
    """Create or replace ``<M>_preview``: the solid belly at draft resolution.

    The preview *is* the final shape, only coarser (``DRAFT_VOXEL_SCALE``).

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg report: Optional dict, see :func:`build_belly`; ``object`` is added.
    :type report: dict
    :return: The preview object.
    :rtype: :class:`bpy.types.Object`
    :raises ValueError: See :func:`solid_mesh`.
    """
    report = {} if report is None else report
    mesh, weights = solid_mesh(context, muscle_name, report, DRAFT_VOXEL_SCALE)
    coll, _objs = preview.muscle_objects(context, muscle_name)
    name = muscle_name + PREVIEW_SUFFIX
    obj = coll.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, mesh)
        coll.objects.link(obj)
    else:
        for mod in list(obj.modifiers):
            obj.modifiers.remove(mod)
        _replace_mesh(obj, mesh)
    obj.data.materials.append(preview._preview_material())
    obj.show_transparent = True        # the path stays visible inside it
    obj.hide_select = True             # clicks go to the path and the rings
    obj[myo_record.ROLE_KEY] = "preview"
    preview.write_deform_weights(obj, weights)
    update_tube(context, muscle_name)
    report["object"] = obj
    return obj


def _remove_object(coll, name):
    obj = coll.objects.get(name) if coll else None
    if obj is not None:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0 and isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)


def remove_preview(muscle_name):
    """Delete ``<M>_preview`` and the wire tube if they exist.

    :arg muscle_name: Muscle name.
    :type muscle_name: str
    """
    for suffix in (PREVIEW_SUFFIX, TUBE_SUFFIX):
        obj = bpy.data.objects.get(muscle_name + suffix)
        if obj is not None:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)


def generate_final(context, muscle_name):
    """Build the final belly ``<M>_muscle`` at full resolution.

    Replaces an existing belly, removes the construction helpers (preview,
    wire tube and rings) and writes the anchored vertex group and sculpt mask
    (:func:`preview.protect_anchored`). The path ``<M>_curve`` is kept: it is
    the muscle path used for the measurements.

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :return: ``(belly, report)``; ``report["anchored_count"]`` is added.
    :rtype: tuple
    :raises ValueError: See :func:`solid_mesh`.
    """
    stop_live(context)
    report = {}
    mesh, weights = solid_mesh(context, muscle_name, report)
    remove_preview(muscle_name)
    coll, _objs = preview.muscle_objects(context, muscle_name)
    name = muscle_name + "_muscle"
    belly = coll.objects.get(name)
    if belly is None:
        belly = bpy.data.objects.new(name, mesh)
        coll.objects.link(belly)
    else:
        _replace_mesh(belly, mesh)
        belly.matrix_world.identity()
    belly[myo_record.ROLE_KEY] = "belly"
    preview.write_deform_weights(belly, weights)
    report["anchored_count"] = preview.protect_anchored(belly)
    rings.remove_rings(coll, muscle_name)                 # construction helpers, no longer needed
    return belly, report


def describe_report(context, report):
    """One-line summary of a :func:`build_belly` report for the panel.

    :arg context: Context (unit scale).
    :type context: :class:`bpy.types.Context`
    :arg report: Report dict (with ``object``).
    :type report: dict
    :rtype: str
    """
    mm = report.get("voxel", 0.0) * myo_record.metres_per_unit(context.scene) * 1000.0
    text = f"{len(report['object'].data.vertices)} vertices, voxel {mm:.2f} mm, {report.get('seconds', 0):.1f} s"
    if report.get("pieces", 1) > 1:
        text += f" | {report['pieces']} separate pieces: widen the rings between them"
    return text


def on_controls_toggled(self, context):
    """*Shape with rings* switched: create or show the rings (on), hide them (off), and rebuild.

    The rings are kept when switched off, with their positions and sizes.

    :arg self: Scene settings (``scene.myogen``).
    :type self: :class:`properties.MyoGeneratorProperties`
    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    """
    coll, _objs = preview.muscle_objects(context, self.muscle_name)
    if coll is not None:
        rings.set_visible(coll, self.muscle_name, self.use_controls)
    schedule_rebuild(context)


# --------------------------------------------------------------------------
# Live preview
# --------------------------------------------------------------------------

_pending = False
_last_state = None


def _state(context):
    """Signature of what the belly depends on: path, rings, attachments."""
    props = context.scene.myogen
    coll, objs = preview.muscle_objects(context)
    if coll is None:
        return None
    name = props.muscle_name
    parts = []
    path = coll.objects.get(name + "_curve")
    if path is not None and path.type == 'CURVE' and path.data.splines:
        sp = path.data.splines[0]
        pts = [tuple(p.co) + tuple(p.handle_left) + tuple(p.handle_right) for p in sp.bezier_points] or \
              [tuple(p.co) for p in sp.points]
        parts.append(tuple(round(x, 5) for p in pts for x in p))
        parts.append(tuple(round(x, 5) for row in path.matrix_world for x in row))
    for ring in rings.ring_objects(coll, name):
        parts.append(tuple(round(x, 5) for row in ring.matrix_world for x in row))
    for key in ("origin", "insertion"):
        obj = objs.get(key)
        if obj is not None:
            parts.append((len(obj.data.vertices),) + tuple(round(x, 5) for row in obj.matrix_world for x in row))
    return hash(tuple(parts))


def _remember_state(context):
    global _last_state
    _last_state = _state(context)


def start_live(context):
    """Build the preview and keep it updated while the path, the rings, the
    settings or the attachments change.

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :return: The preview object.
    :rtype: :class:`bpy.types.Object`
    :raises ValueError: See :func:`solid_mesh`.
    """
    props = context.scene.myogen
    coll, _objs = preview.muscle_objects(context)
    legacy = coll.objects.get(props.muscle_name + "_rig") if coll else None
    if legacy is not None and legacy.type == 'ARMATURE':      # control rig of an earlier version
        bpy.data.objects.remove(legacy, do_unlink=True)
    report = {}
    obj = update_preview(context, props.muscle_name, report)
    rings.set_visible(coll, props.muscle_name, props.use_controls)
    props.preview_live = True
    props.preview_status = describe_report(context, report)
    return obj


def stop_live(context):
    """Stop updating the preview (the object is kept).

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    """
    global _pending
    context.scene.myogen.preview_live = False
    _pending = False
    for fn in (_live_rebuild, _tube_refresh):
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)


def _live_rebuild():
    global _pending
    _pending = False
    context = bpy.context
    props = getattr(context.scene, "myogen", None)
    if props is None or not props.preview_live:
        return None
    report = {}
    try:
        update_preview(context, props.muscle_name, report)
        props.preview_status = describe_report(context, report)
    except ValueError as error:
        props.preview_status = f"Preview failed: {error}"
    return None


def _tube_refresh():
    context = bpy.context
    props = getattr(context.scene, "myogen", None)
    if props is None or not props.preview_live:
        return None
    try:
        update_tube(context, props.muscle_name)
    except ValueError:
        pass
    return None


def schedule_rebuild(context):
    """Refresh the wire tube now and rebuild the live preview after ``LIVE_DELAY`` s
    without further changes.

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    """
    global _pending
    if not context.scene.myogen.preview_live:
        return
    for fn, delay in ((_tube_refresh, TUBE_DELAY), (_live_rebuild, LIVE_DELAY)):
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)
        bpy.app.timers.register(fn, first_interval=delay)
    _pending = True


def on_setting_changed(self, context):
    """Update callback of every belly setting: schedule a live rebuild.

    :arg self: Scene settings (``scene.myogen``).
    :type self: :class:`properties.MyoGeneratorProperties`
    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    """
    schedule_rebuild(context)


def on_shape_changed(self, context):
    """Muscle type changed: rebuild the live preview (Fan builds the belly from fibres).

    The path and the rings are kept; *Reset Rings* sizes the rings with the
    new type's profile.

    :arg self: Scene settings (``scene.myogen``).
    :type self: :class:`properties.MyoGeneratorProperties`
    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    """
    schedule_rebuild(context)


def flush_live(context):
    """Run a pending live rebuild now (tests; before generating).

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :return: True if a rebuild ran.
    :rtype: bool
    """
    if not _pending:
        return False
    for fn in (_live_rebuild, _tube_refresh):
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)
    _tube_refresh()
    _live_rebuild()
    return True


@persistent
def _on_depsgraph_update(scene, depsgraph):
    """Schedule a refresh when the path, a ring or an attachment of
    the live muscle changes (our own updates leave the state unchanged)."""
    props = getattr(scene, "myogen", None)
    if props is None or not props.preview_live:
        return
    name = props.muscle_name
    watched = {name + s for s in ("_curve", "_origin", "_insertion")}
    for update in depsgraph.updates:
        if not isinstance(update.id, bpy.types.Object):
            continue
        obj = update.id.original
        if obj.name in watched or rings.is_ring(obj, name):
            state = _state(bpy.context)
            if state != _last_state:
                _remember_state(bpy.context)
                schedule_rebuild(bpy.context)
            return


def register():
    """Install the depsgraph handler of the live preview."""
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)


def unregister():
    """Remove the depsgraph handler and any pending refresh."""
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    for fn in (_live_rebuild, _tube_refresh):
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)
