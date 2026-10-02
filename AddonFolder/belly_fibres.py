"""Fibres of a finished (sculpted) belly from a Laplacian field.

Following Choi & Blemker (2013, *Skeletal muscle fascicle arrangements can be
reconstructed using a Laplacian vector field simulation*, PLoS ONE 8(10):
e77576, https://doi.org/10.1371/journal.pone.0077576):

1. the belly mesh is voxelised (:func:`volume_builder.occupancy`);
2. a scalar field ``u`` is solved inside it with Laplace's equation,
   ``u = 0`` on the voxels touching the origin attachment, ``u = 1`` on those
   touching the insertion and no flux through the rest of the belly surface
   (:func:`laplace_field`, conjugate gradients);
3. fibres are the streamlines of ``grad u`` from points spread evenly over
   the origin attachment to the insertion **and** from points spread evenly
   over the insertion back to the origin (:func:`trace`), half of the weight
   each: one side alone leaves much of the other without fibres. They fill
   the belly as sculpted, never cross, and fan out or converge with its
   shape. Detours (much longer than the straight distance between their
   ends) are set apart.

Each fibre runs from attachment to attachment (tendon included): its length
is a muscle-belly length, which the fibre/muscle ratio scales to a fascicle
length as for the path (see ``devdocs/ARCHITECTURE.md``, *Fibre length*).
Each fibre also gets its share of the belly volume (the voxels nearest to
it), used by the fibre-weighted PCSA (:func:`myo_record.pcsa_from_fibres`).
"""

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from . import fan, volume_builder

#: Voxels across the largest extent of the belly.
GRID_ACROSS = 96
#: Default number of fibres (seeds on the origin attachment).
DEFAULT_FIBRES = 150
#: Inside voxels closer than this (voxels) to an attachment are fixed.
CONTACT_VOXELS = 1.5
#: Origin points farther than this (voxels) from the belly are not seeded.
FRONT_REACH_VOXELS = 3.0
#: Streamline step (voxels).
STEP_VOXELS = 0.4
#: A fibre has reached the insertion when ``u`` exceeds this.
REACH_U = 0.97
#: A fibre longer than this times the straight distance between its ends is a detour.
DETOUR_MAX = 2.0
#: Attachment points within this (voxels) of the belly count as touched by it.
CONTACT_REACH_VOXELS = 2.0
#: Points sampled over an attachment to measure the belly's contact.
CONTACT_SAMPLES = 300
#: Conjugate-gradient tolerance (relative residual) and iteration limit.
CG_TOL = 1e-6
CG_MAX_ITER = 4000

#: Name suffix of the fibre display object.
FIBRES_SUFFIX = "_belly_fibres"
#: Name suffix of the detoured fibres' display object.
DETOURS_SUFFIX = "_belly_fibres_detours"

_cache = {}


def _bvh(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def _shift(a, axis, step):
    """``a`` shifted by one cell (zero fill, no wrap)."""
    out = np.zeros_like(a)
    src = [slice(None)] * 3
    dst = [slice(None)] * 3
    if step > 0:
        src[axis], dst[axis] = slice(None, -1), slice(1, None)
    else:
        src[axis], dst[axis] = slice(1, None), slice(None, -1)
    out[tuple(dst)] = a[tuple(src)]
    return out


def laplace_field(inside, fixed, values, tol=CG_TOL, max_iter=CG_MAX_ITER):
    """Solve Laplace's equation on a voxel region.

    Dirichlet values on ``fixed`` voxels, zero flux through the boundary of
    ``inside`` (only neighbours inside count). Free voxels not connected to a
    fixed one stay 0.

    :arg inside: Region, boolean (X, Y, Z).
    :type inside: :class:`numpy.ndarray`
    :arg fixed: Fixed voxels (subset of ``inside``).
    :type fixed: :class:`numpy.ndarray`
    :arg values: Values of the fixed voxels (read where ``fixed``).
    :type values: :class:`numpy.ndarray`
    :arg tol: Relative residual at which to stop.
    :type tol: float
    :arg max_iter: Iteration limit.
    :type max_iter: int
    :return: ``(u, iterations)``: field (0 outside ``inside``) and iterations used.
    :rtype: tuple
    """
    free = inside & ~fixed
    inside_f = inside.astype(float)
    shifts = [(ax, s) for ax in range(3) for s in (1, -1)]
    degree = sum(_shift(inside_f, ax, s) for ax, s in shifts) * free
    fixed_u = np.where(fixed, values, 0.0)
    b = sum(_shift(fixed_u, ax, s) for ax, s in shifts) * free
    freef = free.astype(float)

    def apply(x):
        return (degree * x - sum(_shift(x, ax, s) for ax, s in shifts)) * freef

    x = np.zeros_like(b)
    r = b.copy()
    p = r.copy()
    rr = float(np.sum(r * r))
    stop = (tol ** 2) * max(rr, 1e-300)
    it = 0
    while it < max_iter and rr > stop:
        ap = apply(p)
        alpha = rr / max(float(np.sum(p * ap)), 1e-300)
        x += alpha * p
        r -= alpha * ap
        rr_new = float(np.sum(r * r))
        p = r + (rr_new / rr) * p
        rr = rr_new
        it += 1
    return np.where(fixed, values, x) * inside, it


def _extend(u, inside, passes=3):
    """Copy the field a few voxels outside the region (for gradients at its surface)."""
    u = u.copy()
    known = inside.copy()
    shifts = [(ax, s) for ax in range(3) for s in (1, -1)]
    for _ in range(passes):
        total = sum(_shift(u * known, ax, s) for ax, s in shifts)
        count = sum(_shift(known.astype(float), ax, s) for ax, s in shifts)
        grow = ~known & (count > 0)
        u[grow] = total[grow] / count[grow]
        known |= grow
    return u, known


def _sample(field, origin, voxel, pts):
    """Trilinear sample of a (X, Y, Z[, C]) grid at world points (clamped)."""
    g = (pts - origin) / voxel
    shape = np.array(field.shape[:3])
    g = np.clip(g, 0.0, shape - 1.000001)
    i = np.floor(g).astype(int)
    f = g - i
    out = 0.0
    for dx in (0, 1):
        wx = f[:, 0] if dx else 1.0 - f[:, 0]
        for dy in (0, 1):
            wy = f[:, 1] if dy else 1.0 - f[:, 1]
            for dz in (0, 1):
                wz = f[:, 2] if dz else 1.0 - f[:, 2]
                w = wx * wy * wz
                v = field[i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz]
                out = out + (w[:, None] * v if v.ndim == 2 else w * v)
    return out


def trace(grad, u, known, origin, voxel, seeds, max_steps):
    """Streamlines of ``grad`` from ``seeds`` until ``u`` reaches ``REACH_U``.

    :arg grad: Gradient field (X, Y, Z, 3).
    :type grad: :class:`numpy.ndarray`
    :arg u: Field (X, Y, Z), extended outside the region.
    :type u: :class:`numpy.ndarray`
    :arg known: Voxels where ``u`` is defined.
    :type known: :class:`numpy.ndarray`
    :arg origin: World position of voxel (0, 0, 0).
    :type origin: :class:`numpy.ndarray`
    :arg voxel: Voxel size.
    :type voxel: float
    :arg seeds: Start points (N, 3).
    :type seeds: :class:`numpy.ndarray`
    :arg max_steps: Step limit.
    :type max_steps: int
    :return: ``(courses, reached)``: list of (K, 3) arrays and boolean (N,).
    :rtype: tuple
    """
    h = STEP_VOXELS * voxel
    pts = seeds.astype(float).copy()
    active = np.ones(len(pts), dtype=bool)
    reached = np.zeros(len(pts), dtype=bool)
    courses = [[p.copy()] for p in pts]
    knownf = known.astype(float)

    def direction(p):
        d = _sample(grad, origin, voxel, p)
        n = np.linalg.norm(d, axis=1)
        return d / np.maximum(n, 1e-12)[:, None], n > 1e-12

    for _ in range(max_steps):
        idx = np.nonzero(active)[0]
        if not len(idx):
            break
        p = pts[idx]
        d1, ok1 = direction(p)
        d2, ok2 = direction(p + 0.5 * h * d1)                    # midpoint (RK2)
        q = p + h * d2
        inside = _sample(knownf, origin, voxel, q) > 0.5
        ok = ok1 & ok2 & inside
        uq = _sample(u, origin, voxel, q)
        for k, j in enumerate(idx):
            if not ok[k]:
                active[j] = False
                continue
            pts[j] = q[k]
            courses[j].append(q[k].copy())
            if uq[k] >= REACH_U:
                active[j] = False
                reached[j] = True
    return [np.array(c) for c in courses], reached


def closed_belly(belly, voxel):
    """World-space closed copy of a belly, whatever its defects.

    Holes are filled and the surface is rebuilt by a temporary voxel Remesh
    (as :func:`myo_record.enclosed_volume`): sculpted bellies often have open
    or non-manifold edges and self-overlaps, which break inside/outside tests.
    The belly is left unchanged.

    :arg belly: Belly mesh object.
    :type belly: :class:`bpy.types.Object`
    :arg voxel: Remesh voxel size (Blender units).
    :type voxel: float
    :return: Closed bmesh (caller frees it).
    :rtype: :class:`bmesh.types.BMesh`
    """
    import bmesh
    import bpy
    bm = bmesh.new()
    bm.from_mesh(belly.data)
    bm.transform(belly.matrix_world)
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    mesh = bpy.data.meshes.new("myo_belly_fibres")
    bm.to_mesh(mesh)
    bm.free()
    temp = bpy.data.objects.new("myo_belly_fibres", mesh)
    bpy.context.scene.collection.objects.link(temp)
    try:
        mod = temp.modifiers.new("remesh", 'REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = voxel
        evaluated = temp.evaluated_get(bpy.context.evaluated_depsgraph_get())
        out = bmesh.new()
        out.from_mesh(evaluated.to_mesh())
        evaluated.to_mesh_clear()
    finally:
        bpy.data.objects.remove(temp, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    out.normal_update()
    return out


def _signature(belly, origin_obj, insertion_obj, count):
    parts = [count]
    for obj in (belly, origin_obj, insertion_obj):
        co = np.empty(len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get("co", co)
        parts += [obj.name, len(co), float(co.sum()), float((co * co).sum()),
                  tuple(round(x, 9) for row in obj.matrix_world for x in row)]
    return tuple(parts)


def _front_tree(inside, fixed, values, value, origin, voxel):
    """KD-tree of the free voxels next to the fixed layer of one attachment."""
    side = (fixed & (values == value)).astype(float)
    front = inside & ~fixed & sum(_shift(side, ax, s) for ax in range(3) for s in (1, -1)).astype(bool)
    cells = np.argwhere(front)
    tree = KDTree(len(cells))
    for k, c in enumerate((origin + cells * voxel).tolist()):
        tree.insert(c, k)
    tree.balance()
    return tree, len(cells)


def _trace_from(grid, surface_obj, other_obj, value, count):
    """Fibres from points spread over one attachment to the other one.

    :return: ``(courses, points, seeded)``: courses (start on ``surface_obj``,
       end on ``other_obj``) of the fibres that arrived, number of surface
       points, number of them the belly covers.
    """
    inside, fixed, values, u, known, grad, origin, voxel = grid
    tree, n_front = _front_tree(inside, fixed, values, value, origin, voxel)
    points, _normals = fan.sample_surface(surface_obj, count)
    if not n_front or not points:
        return [], len(points), 0
    starts, firsts = [], []
    for p in points:
        co, _k, d = tree.find(p)
        if d <= FRONT_REACH_VOXELS * voxel:                    # the belly covers this part of the surface
            starts.append(list(p))
            firsts.append(list(co))
    if not starts:
        return [], len(points), 0
    if value == 0.0:                                            # downhill to the insertion
        field, direction = u, grad
    else:                                                       # uphill back to the origin
        field, direction = 1.0 - u, -grad
    max_steps = int(4 * sum(inside.shape) / STEP_VOXELS)
    courses, reached = trace(direction, field, known, origin, voxel, np.array(firsts), max_steps)
    other = _bvh(other_obj)
    out = []
    for start, course, ok in zip(starts, courses, reached):
        if ok:
            end = other.find_nearest(Vector(course[-1].tolist()))[0]
            out.append(np.vstack([start, course] + ([list(end)] if end is not None else [])))
    return out, len(points), len(starts)


def _contact(surface_obj, belly_tree, distance, count=CONTACT_SAMPLES):
    """Fraction of an attachment's area within ``distance`` of the belly."""
    points, _normals = fan.sample_surface(surface_obj, count)
    if not points:
        return 0.0
    return float(np.mean([belly_tree.find_nearest(p)[3] <= distance for p in points]))


def belly_fibres(belly, origin_obj, insertion_obj, count=DEFAULT_FIBRES):
    """Fibres of a finished belly between its attachments (Laplacian field).

    Fibres are traced **from both attachments**: ``count`` from points spread
    over the origin to the insertion, and ``count`` from points spread over
    the insertion back to the origin (reversed, so every course runs origin
    to insertion). Streamlines seeded on one side only gather where the field
    is strongest on the other and leave much of it without fibres; the two
    sets together cover both attachments, and each set carries half of the
    weight, so the mean length no longer depends on the side chosen.

    Fibres longer than ``DETOUR_MAX`` times the straight distance between
    their ends are **detours** (the field following a thin curved sheet round
    a bend): they are kept apart and left out of the lengths and the volume
    shares.

    Results are cached until the belly or the attachments change.

    :arg belly: Belly mesh (closed by :func:`closed_belly` first).
    :type belly: :class:`bpy.types.Object`
    :arg origin_obj: Origin attachment surface.
    :type origin_obj: :class:`bpy.types.Object`
    :arg insertion_obj: Insertion attachment surface.
    :type insertion_obj: :class:`bpy.types.Object`
    :arg count: Fibres seeded on each attachment.
    :type count: int
    :return: dict with

       * ``courses``: kept fibres, (K, 3) world-space arrays from origin to insertion;
       * ``lengths`` (Blender units) and ``weights`` (sum 1: each seeding side
         carries half) of the kept fibres;
       * ``shares``: fraction of the belly volume nearest to each kept fibre (sum 1);
       * ``detours``: courses of the detoured fibres; ``detoured``: their
         fraction of the arrived fibres;
       * ``covered`` / ``covered_insertion``: fraction of the origin /
         insertion points the belly covers (seeded);
       * ``reached``: fraction of the seeded fibres that arrived;
       * ``origin_contact`` / ``insertion_contact``: fraction of each
         attachment's area the belly touches;
       * ``seeds``, ``voxel`` and ``iterations``.
    :rtype: dict
    :raises ValueError: If the belly does not touch an attachment or no fibre
       arrives.
    """
    key = _signature(belly, origin_obj, insertion_obj, count)
    if key in _cache:
        return _cache[key]
    if not belly.data.vertices:
        raise ValueError("the belly mesh is empty")
    voxel = max(belly.dimensions) / GRID_ACROSS
    bm = closed_belly(belly, voxel * 0.5)
    belly_tree = BVHTree.FromBMesh(bm)
    co = np.array([list(v.co) for v in bm.verts])
    bm.free()
    lo, hi = co.min(0), co.max(0)
    pad = 3 * voxel
    lo, hi = lo - pad, hi + pad
    jitter = voxel * 0.0137                                     # avoid rays through vertices
    xs = np.arange(lo[0], hi[0], voxel) + jitter
    ys = np.arange(lo[1], hi[1], voxel) + 0.7 * jitter
    zs = np.arange(lo[2], hi[2], voxel)
    inside = volume_builder.occupancy(belly_tree, xs, ys, zs, lo[2] - voxel, signed=False)
    origin = np.array([xs[0], ys[0], zs[0]])

    fixed = np.zeros(inside.shape, dtype=bool)
    values = np.zeros(inside.shape)
    cells = np.argwhere(inside)
    centres = origin + cells * voxel
    reach = CONTACT_VOXELS * voxel
    dist = []
    for obj in (origin_obj, insertion_obj):
        tree = _bvh(obj)
        d = np.full(len(cells), np.inf)
        for k, p in enumerate(centres.tolist()):
            hit = tree.find_nearest(Vector(p), reach)
            if hit[0] is not None:
                d[k] = hit[3]
        dist.append(d)
    near_o, near_i = np.isfinite(dist[0]), np.isfinite(dist[1])
    if not near_o.any() or not near_i.any():
        missing = "origin" if not near_o.any() else "insertion"
        raise ValueError(f"the belly does not touch the {missing} attachment")
    to_insertion = near_i & (~near_o | (dist[1] < dist[0]))
    to_origin = near_o & ~to_insertion
    for mask, value in ((to_origin, 0.0), (to_insertion, 1.0)):
        c = cells[mask]
        fixed[c[:, 0], c[:, 1], c[:, 2]] = True
        values[c[:, 0], c[:, 1], c[:, 2]] = value

    u, iterations = laplace_field(inside, fixed, values)
    u_ext, known = _extend(u, inside)
    grad = np.stack(np.gradient(u_ext, voxel), axis=-1)
    grid = (inside, fixed, values, u_ext, known, grad, origin, voxel)

    forward, n_o, seeded_o = _trace_from(grid, origin_obj, insertion_obj, 0.0, count)
    backward, n_i, seeded_i = _trace_from(grid, insertion_obj, origin_obj, 1.0, count)
    if not seeded_o:
        raise ValueError("the belly does not cover the origin attachment")
    if not forward and not backward:
        raise ValueError("no fibre reached the other attachment")
    backward = [c[::-1] for c in backward]                      # origin to insertion
    sets = [(c, 0.5 / len(forward) if backward else 1.0 / len(forward)) for c in forward] + \
           [(c, 0.5 / len(backward) if forward else 1.0 / len(backward)) for c in backward]
    kept, weights, detours = [], [], []
    for c, w in sets:
        length = float(np.linalg.norm(np.diff(c, axis=0), axis=1).sum())
        straight = float(np.linalg.norm(c[-1] - c[0]))
        if length > DETOUR_MAX * max(straight, 1e-12):
            detours.append(c)
        else:
            kept.append(c)
            weights.append(w)
    if not kept:
        raise ValueError("every fibre detours")
    weights = np.array(weights) / sum(weights)
    lengths = np.array([float(np.linalg.norm(np.diff(c, axis=0), axis=1).sum()) for c in kept])

    tree = KDTree(sum(len(c) for c in kept))
    owner = []
    for f, c in enumerate(kept):
        for p in c.tolist():
            tree.insert(p, len(owner))
            owner.append(f)
    tree.balance()
    counts = np.zeros(len(kept))
    for p in centres.tolist():
        counts[owner[tree.find(p)[1]]] += 1
    contact = CONTACT_REACH_VOXELS * voxel
    result = {
        "courses": kept,
        "lengths": lengths,
        "weights": weights,
        "shares": counts / max(counts.sum(), 1.0),
        "detours": detours,
        "detoured": len(detours) / len(sets),
        "seeds": seeded_o + seeded_i,
        "covered": seeded_o / max(n_o, 1),
        "covered_insertion": seeded_i / max(n_i, 1),
        "reached": len(sets) / max(seeded_o + seeded_i, 1),
        "origin_contact": _contact(origin_obj, belly_tree, contact),
        "insertion_contact": _contact(insertion_obj, belly_tree, contact),
        "voxel": voxel,
        "iterations": iterations,
    }
    _cache.clear()                                              # keep only the latest muscle state
    _cache[key] = result
    return result


def show_fibres(collection, muscle_name, courses, detours=()):
    """Create (or replace) ``<M>_belly_fibres``: a curve with one poly spline per fibre.

    Detoured fibres, if given, go to ``<M>_belly_fibres_detours`` (magenta).

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg courses: World-space fibre courses.
    :type courses: list of :class:`numpy.ndarray`
    :arg detours: World-space courses of detoured fibres.
    :type detours: list of :class:`numpy.ndarray`
    :return: The curve object of the kept fibres.
    :rtype: :class:`bpy.types.Object`
    """
    remove_fibres(collection, muscle_name)
    obj = _curve_object(collection, muscle_name + FIBRES_SUFFIX, courses, (1.0, 0.85, 0.3, 1.0))
    if len(detours):
        _curve_object(collection, muscle_name + DETOURS_SUFFIX, detours, (1.0, 0.0, 1.0, 1.0))
    return obj


def _curve_object(collection, name, courses, color):
    import bpy
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    for c in courses:
        spline = curve.splines.new('POLY')
        spline.points.add(len(c) - 1)
        for p, q in zip(spline.points, c.tolist()):
            p.co = (q[0], q[1], q[2], 1.0)
    obj = bpy.data.objects.new(name, curve)
    obj.show_in_front = True
    obj.color = color
    collection.objects.link(obj)
    return obj


def remove_fibres(collection, muscle_name):
    """Delete ``<M>_belly_fibres`` (and its detours) if present.

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :return: True if something was removed.
    :rtype: bool
    """
    import bpy
    removed = False
    for name in (muscle_name + FIBRES_SUFFIX, muscle_name + DETOURS_SUFFIX):
        obj = collection.objects.get(name)
        if obj is None:
            continue
        curve = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if curve.users == 0:
            bpy.data.curves.remove(curve)
        removed = True
    return removed


def length_stats(lengths, weights=None):
    """Weighted mean and standard deviation, median, min and max of fibre lengths.

    :arg lengths: Fibre lengths.
    :type lengths: :class:`numpy.ndarray`
    :arg weights: Fibre weights (default equal).
    :type weights: :class:`numpy.ndarray`
    :rtype: dict
    """
    lengths = np.asarray(lengths, dtype=float)
    w = np.full(len(lengths), 1.0 / len(lengths)) if weights is None else np.asarray(weights) / np.sum(weights)
    mean = float(np.dot(w, lengths))
    return {
        "mean": mean,
        "sd": float(np.sqrt(np.dot(w, (lengths - mean) ** 2))),
        "median": float(np.median(lengths)),
        "min": float(lengths.min()),
        "max": float(lengths.max()),
    }
