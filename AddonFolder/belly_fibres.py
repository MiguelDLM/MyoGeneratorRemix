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
#: Where fibres start (see :func:`belly_fibres`).
SEEDINGS = ('ORIGIN', 'INSERTION', 'BOTH', 'PAIRED')
DEFAULT_SEEDING = 'BOTH'
#: Points per paired fibre before export.
PAIRED_SAMPLES = 64
#: A paired fibre with more than this fraction of its inner points outside the belly is a detour.
PAIRED_OUTSIDE_MAX = 0.1
#: Conjugate-gradient tolerance (relative residual) and iteration limit.
CG_TOL = 1e-6
CG_MAX_ITER = 4000

#: Segments of each exported fibre (Modenese & Kohout 2020 use 15).
EXPORT_SEGMENTS = 15

#: Name suffix of the detoured fibres (left out of the measurements), written next to ``<M>_fibres``.
DETOURS_SUFFIX = "_fibre_detours"
#: Fibre display objects of earlier versions (removed when fibres are exported).
LEGACY_DISPLAY_SUFFIXES = ("_belly_fibres", "_belly_fibres_detours")
#: Viewport colours of the exported fibres and of the detours.
FIBRE_COLOR = (1.0, 0.85, 0.3, 1.0)
DETOUR_COLOR = (1.0, 0.0, 1.0, 1.0)

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


def _signature(belly, origin_obj, insertion_obj, count, seeding):
    parts = [count, seeding]
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


def assignment(cost):
    """Minimum-cost assignment of every row to a distinct column (Hungarian
    algorithm with potentials, ``O(n^2 m)``; ``n`` rows <= ``m`` columns).

    :arg cost: Cost matrix, (n, m) with n <= m.
    :type cost: :class:`numpy.ndarray`
    :return: Column of each row.
    :rtype: :class:`numpy.ndarray`
    :raises ValueError: If there are more rows than columns.
    """
    cost = np.asarray(cost, dtype=float)
    n, m = cost.shape
    if n > m:
        raise ValueError("more rows than columns")
    u = np.zeros(n + 1)
    v = np.zeros(m + 1)
    p = np.zeros(m + 1, dtype=int)                              # row matched to each column (1-based, 0 = none)
    way = np.zeros(m + 1, dtype=int)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = np.full(m + 1, np.inf)
        used = np.zeros(m + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            free = ~used[1:]
            cur = cost[i0 - 1] - u[i0] - v[1:]
            better = free & (cur < minv[1:])
            minv[1:][better] = cur[better]
            way[1:][better] = j0
            cand = np.where(free, minv[1:], np.inf)
            j1 = int(np.argmin(cand)) + 1
            delta = cand[j1 - 1]
            cols = np.nonzero(used)[0]
            u[p[cols]] += delta
            v[cols] -= delta
            minv[1:][free] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    out = np.zeros(n, dtype=int)
    for j in range(1, m + 1):
        if p[j]:
            out[p[j] - 1] = j - 1
    return out


def _field_parameter(course, grid):
    """Field value along a course (origin to insertion), 0 and 1 at its ends, non-decreasing."""
    _inside, _fixed, _values, u, _known, _grad, origin, voxel = grid
    values = np.asarray(_sample(u, origin, voxel, np.asarray(course)), dtype=float)
    values[0], values[-1] = 0.0, 1.0
    return np.clip(np.maximum.accumulate(values), 0.0, 1.0)


def paired_courses(forward, backward, grid, samples=PAIRED_SAMPLES):
    """One fibre per pair of seeds, the seeds spread over both attachments.

    ``forward`` (seeded on the origin) and ``backward`` (seeded on the
    insertion, reversed) streamlines are paired by optimal transport with
    cost ``|end(f) - insertion seed(b)|^2 + |start(b) - origin seed(f)|^2``:
    each fibre joins two seeds the field would nearly join, and fibres do
    not cross. The fibre is the forward streamline near its origin blending
    smoothly (by field value) into the backward one near its insertion, so it
    ends exactly on both seeds and follows the belly in between. With unequal
    counts, the smaller set is paired completely.

    :arg forward: Courses from origin seeds (origin to insertion).
    :type forward: list of :class:`numpy.ndarray`
    :arg backward: Courses from insertion seeds, reversed (origin to insertion).
    :type backward: list of :class:`numpy.ndarray`
    :arg grid: Field grid (internal).
    :type grid: tuple
    :arg samples: Points per fibre.
    :type samples: int
    :return: Paired fibres, (samples, 3) each.
    :rtype: list of :class:`numpy.ndarray`
    """
    f_start = np.array([c[0] for c in forward])
    f_end = np.array([c[-1] for c in forward])
    b_start = np.array([c[0] for c in backward])                # arrival on the origin
    b_end = np.array([c[-1] for c in backward])                 # insertion seed
    cost = (((f_end[:, None, :] - b_end[None, :, :]) ** 2).sum(axis=2)
            + ((b_start[None, :, :] - f_start[:, None, :]) ** 2).sum(axis=2))
    if len(forward) <= len(backward):
        pairs = list(enumerate(assignment(cost)))
    else:
        pairs = [(int(a), b) for b, a in enumerate(assignment(cost.T))]
    t = np.linspace(0.0, 1.0, samples)
    w = (t * t * (3.0 - 2.0 * t))[:, None]

    def at(course):
        par = _field_parameter(course, grid)
        return np.stack([np.interp(t, par, course[:, k]) for k in range(3)], axis=1)
    return [(1.0 - w) * at(forward[a]) + w * at(backward[b]) for a, b in pairs]


def _outside_fraction(course, grid):
    """Fraction of the inner points of a course outside the belly."""
    inside, _fixed, _values, _u, _known, _grad, origin, voxel = grid
    inner = np.asarray(course)[2:-2]
    if not len(inner):
        return 0.0
    return float(np.mean(_sample(inside.astype(float), origin, voxel, inner) < 0.5))


def _contact(surface_obj, belly_tree, distance, count=CONTACT_SAMPLES):
    """Fraction of an attachment's area within ``distance`` of the belly."""
    points, _normals = fan.sample_surface(surface_obj, count)
    if not points:
        return 0.0
    return float(np.mean([belly_tree.find_nearest(p)[3] <= distance for p in points]))


def belly_fibres(belly, origin_obj, insertion_obj, count=DEFAULT_FIBRES, seeding=DEFAULT_SEEDING):
    """Fibres of a finished belly between its attachments (Laplacian field).

    ``seeding`` (:data:`SEEDINGS`) chooses where fibres start:

    * ``ORIGIN``: ``count`` points spread over the origin, traced to the
      insertion. They gather where the field is strongest on the insertion
      and may leave much of it without fibres.
    * ``INSERTION``: the same from the insertion back to the origin.
    * ``BOTH`` (default): both sets, each carrying half of the weight: both
      attachments are covered and the mean length does not depend on the
      side chosen, but each set bunches up on the other attachment.
    * ``PAIRED``: one fibre per pair of points, the points spread evenly over
      both attachments and paired by optimal transport so that each fibre
      joins where the field would take each of its ends
      (:func:`paired_courses`); uniform coverage of both, equal weights.

    Every course runs origin to insertion.

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
    :arg count: Points seeded on each seeded attachment.
    :type count: int
    :arg seeding: One of :data:`SEEDINGS`.
    :type seeding: str
    :return: dict with

       * ``courses``: kept fibres, (K, 3) world-space arrays from origin to insertion;
       * ``lengths`` (Blender units) and ``weights`` (sum 1: each seeding side
         carries half) of the kept fibres;
       * ``shares``: fraction of the belly volume nearest to each kept fibre (sum 1);
       * ``detours``: courses of the detoured fibres; ``detoured``: their
         fraction of the arrived fibres;
       * ``seeding``: the seeding used;
       * ``covered`` / ``covered_insertion``: fraction of the origin /
         insertion points the belly covers (seeded), None for a side not seeded;
       * ``reached``: fraction of the seeded streamlines that arrived;
       * ``origin_contact`` / ``insertion_contact``: fraction of each
         attachment's area the belly touches;
       * ``seeds``, ``voxel`` and ``iterations``.
    :rtype: dict
    :raises ValueError: If the belly does not touch an attachment or no fibre
       arrives.
    """
    if seeding not in SEEDINGS:
        raise ValueError(f"unknown seeding '{seeding}'")
    key = _signature(belly, origin_obj, insertion_obj, count, seeding)
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

    from_origin = seeding in ('ORIGIN', 'BOTH', 'PAIRED')
    from_insertion = seeding in ('INSERTION', 'BOTH', 'PAIRED')
    forward, n_o, seeded_o = (_trace_from(grid, origin_obj, insertion_obj, 0.0, count) if from_origin
                              else ([], 0, 0))
    backward, n_i, seeded_i = (_trace_from(grid, insertion_obj, origin_obj, 1.0, count) if from_insertion
                               else ([], 0, 0))
    if from_origin and not seeded_o:
        raise ValueError("the belly does not cover the origin attachment")
    if from_insertion and not seeded_i:
        raise ValueError("the belly does not cover the insertion attachment")
    if not forward and not backward:
        raise ValueError("no fibre reached the other attachment")
    backward = [c[::-1] for c in backward]                      # origin to insertion
    if seeding == 'PAIRED':
        if not forward or not backward:
            raise ValueError("no fibre arrived from one of the attachments: cannot pair")
        sets = [(c, 1.0) for c in paired_courses(forward, backward, grid)]
    else:
        sets = [(c, 0.5 / len(forward) if backward else 1.0 / len(forward)) for c in forward] + \
               [(c, 0.5 / len(backward) if forward else 1.0 / len(backward)) for c in backward]
    kept, weights, detours = [], [], []
    for c, w in sets:
        length = float(np.linalg.norm(np.diff(c, axis=0), axis=1).sum())
        straight = float(np.linalg.norm(c[-1] - c[0]))
        outside = seeding == 'PAIRED' and _outside_fraction(c, grid) > PAIRED_OUTSIDE_MAX
        if outside or length > DETOUR_MAX * max(straight, 1e-12):
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
        "seeding": seeding,
        "seeds": seeded_o + seeded_i,
        "covered": seeded_o / max(n_o, 1) if from_origin else None,
        "covered_insertion": seeded_i / max(n_i, 1) if from_insertion else None,
        "reached": (len(forward) + len(backward)) / max(seeded_o + seeded_i, 1),
        "origin_contact": _contact(origin_obj, belly_tree, contact),
        "insertion_contact": _contact(insertion_obj, belly_tree, contact),
        "voxel": voxel,
        "iterations": iterations,
    }
    _cache.clear()                                              # keep only the latest muscle state
    _cache[key] = result
    return result


def _polyline_mesh(collection, name, courses, color):
    """Create a hidden mesh of polylines (one edge chain per course), replacing ``name``."""
    import bpy
    old = collection.objects.get(name)
    if old is not None:
        data = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
    verts, edges = [], []
    for c in courses:
        base = len(verts)
        verts.extend(map(tuple, np.asarray(c).tolist()))
        edges.extend((base + k, base + k + 1) for k in range(len(c) - 1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.color = color
    obj.show_in_front = True
    obj.hide_viewport = True
    obj.hide_render = True
    return obj


def remove_legacy_display(collection, muscle_name):
    """Delete the fibre curves made by the former *Show Belly Fibres* operator.

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    """
    import bpy
    for suffix in LEGACY_DISPLAY_SUFFIXES:
        obj = collection.objects.get(muscle_name + suffix)
        if obj is not None:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data is not None and data.users == 0 and isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)


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


def resample(course, segments=EXPORT_SEGMENTS):
    """A polyline resampled to ``segments + 1`` points evenly spaced along it.

    :arg course: Polyline, (K, 3).
    :type course: :class:`numpy.ndarray`
    :arg segments: Number of segments.
    :type segments: int
    :rtype: :class:`numpy.ndarray`
    """
    course = np.asarray(course, dtype=float)
    cum = np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(course, axis=0), axis=1))))
    if cum[-1] <= 0.0:
        return np.repeat(course[:1], segments + 1, axis=0)
    t = np.linspace(0.0, cum[-1], segments + 1)
    return np.stack([np.interp(t, cum, course[:, i]) for i in range(3)], axis=1)


def export_fibres(collection, muscle_name, fibres, volume_m3, metres_per_unit, fiber_length_ratio,
                  pennation_deg, segments=EXPORT_SEGMENTS):
    """Write the fibres of a belly for simulators (``<M>_fibres``, :func:`myo_record.write_fibres`).

    Each kept fibre is resampled to ``segments`` segments; its rest length,
    area weight, volume share and PCSA by both sharing rules
    (:func:`myo_record.fibre_pcsa`) are stored with it.

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg fibres: Result of :func:`belly_fibres`.
    :type fibres: dict
    :arg volume_m3: Belly volume (m³).
    :type volume_m3: float
    :arg metres_per_unit: Metres per Blender unit.
    :type metres_per_unit: float
    :arg fiber_length_ratio: Fascicle / fibre-line length.
    :type fiber_length_ratio: float
    :arg pennation_deg: Pennation angle (degrees).
    :type pennation_deg: float
    :arg segments: Segments per fibre.
    :type segments: int
    :return: The fibres object.
    :rtype: :class:`bpy.types.Object`
    """
    from . import myo_record
    lengths_m = [float(x) * metres_per_unit for x in fibres["lengths"]]
    by_area, by_volume = myo_record.fibre_pcsa(volume_m3, lengths_m, fibres["weights"], fibres["shares"],
                                               fiber_length_ratio, pennation_deg)
    remove_legacy_display(collection, muscle_name)
    if len(fibres["detours"]):
        _polyline_mesh(collection, muscle_name + DETOURS_SUFFIX, fibres["detours"], DETOUR_COLOR)
    else:
        old = collection.objects.get(muscle_name + DETOURS_SUFFIX)
        if old is not None:
            import bpy
            bpy.data.objects.remove(old, do_unlink=True)
    obj = myo_record.write_fibres(
        collection, muscle_name + myo_record.ROLES["fibres"],
        [resample(c, segments).tolist() for c in fibres["courses"]],
        {"myo_fibre_length_m": lengths_m,
         "myo_fibre_weight": list(map(float, fibres["weights"])),
         "myo_fibre_share": list(map(float, fibres["shares"])),
         "myo_fibre_pcsa_area_m2": by_area,
         "myo_fibre_pcsa_volume_m2": by_volume},
        seeding=fibres.get("seeding", ""))
    obj.color = FIBRE_COLOR
    obj.show_in_front = True
    return obj
