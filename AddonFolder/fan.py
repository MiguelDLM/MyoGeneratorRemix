"""Fan-shaped (convergent) muscles built from fibres.

A fan muscle (temporalis, pectoralis major, …) spreads over a broad origin
and converges on a narrow insertion. Its belly is the union of fibres: one
from every part of the origin attachment to the matching part of the
insertion, all following the muscle path ``<M>_curve``, each with a radius
equal to the local half-thickness of the muscle.

* Fibre starts are spread evenly over the origin attachment
  (:func:`sample_surface`) and lifted off the bone by the half-thickness;
  each fibre ends at the point of the insertion with the same relative
  position (the two footprints are matched in one fixed frame, scaled to
  each other's extent).
* Each fibre runs straight from its start to its end plus the path's bend
  (the path's offset from its chord), so the fibres curve with the path,
  converge on the insertion and never twist around each other.
* Section rings (:mod:`rings`), when used, set at their place the width of
  the fan (X, along its widest direction), its half-thickness (Y) and its
  turn (R). Without rings the fan has its natural width and the default
  thickness (:func:`default_thickness`).

:func:`occupancy` rasterises the fibres (capsules) into the voxel grid of
:mod:`volume_builder`.
"""

import math

import numpy as np
from mathutils import Vector

from . import preview, tube

#: Fibres used for the final mesh (the preview uses ``DRAFT_FIBRES``).
FIBRES = 240
#: Fibres used for the draft preview.
DRAFT_FIBRES = 120
#: Samples along each fibre.
FIBRE_SAMPLES = 40
#: Fibre radii are quantised to this fraction of a voxel when rasterised.
RADIUS_STEP = 0.5
#: Sphere centres stamped per batch (memory bound).
STAMP_CHUNK = 2000
#: Default half-thickness = this x the path length.
THICKNESS_FRACTION = 0.08
#: The default half-thickness swells by this fraction in the middle.
THICKNESS_BELLY = 0.3


def sample_surface(surface_obj, count):
    """About ``count`` points spread evenly over a surface, with outward normals' faces.

    One point per cell of a grid whose spacing gives ``count`` cells over the
    surface's area (the face centre nearest to the cell's centre of mass).

    :arg surface_obj: Attachment surface.
    :type surface_obj: :class:`bpy.types.Object`
    :arg count: Target number of points.
    :type count: int
    :return: ``(points, normals)``: world-space face centres and face normals.
    :rtype: tuple of list of :class:`mathutils.Vector`
    """
    mw = surface_obj.matrix_world
    nm = mw.to_3x3().inverted_safe().transposed()
    centres, normals, areas = [], [], []
    for poly in surface_obj.data.polygons:
        centres.append(mw @ poly.center)
        normals.append((nm @ poly.normal).normalized())
        areas.append(poly.area)
    if not centres:
        return [], []
    total = sum(areas) * mw.median_scale ** 2
    cell = math.sqrt(max(total, 1e-12) / max(count, 1))
    cells = {}
    for c, n in zip(centres, normals):
        key = (round(c.x / cell), round(c.y / cell), round(c.z / cell))
        cells.setdefault(key, []).append((c, n))
    points, out_normals = [], []
    for members in cells.values():
        mean = sum((c for c, _n in members), Vector()) / len(members)
        c, n = min(members, key=lambda m: (m[0] - mean).length)
        points.append(c)
        out_normals.append(n)
    return points, out_normals


def default_thickness(path_points):
    """Default half-thickness profile ``h(u)`` of a fan muscle (Blender units).

    :arg path_points: Arc-length samples of the path.
    :type path_points: list of :class:`mathutils.Vector`
    :return: Function of ``u`` (0-1).
    :rtype: callable
    """
    length = sum((b - a).length for a, b in zip(path_points[:-1], path_points[1:]))
    h0 = THICKNESS_FRACTION * length

    def h(u):
        return h0 * (1.0 + THICKNESS_BELLY * math.sin(math.pi * u))
    return h


def _fixed_basis(axis):
    a = axis.normalized()
    n = a.orthogonal().normalized()
    return a, n, a.cross(n)


def fibres(path_points, origin_surface, insertion_surface, bones, count, thickness=None, sections=None):
    """Fibre courses of a fan muscle and their radii.

    Each fibre runs straight from its start on the origin to its end on the
    insertion, plus the path's own bend (its offset from the straight chord
    between its ends), so all fibres curve like the path without twisting.
    Starts and ends are matched in one fixed frame (the chord and two axes
    perpendicular to it), scaling the origin footprint to the insertion's
    extent axis by axis.

    :arg path_points: Arc-length samples of the muscle path (origin to insertion).
    :type path_points: list of :class:`mathutils.Vector`
    :arg origin_surface: Origin attachment surface.
    :type origin_surface: :class:`bpy.types.Object`
    :arg insertion_surface: Insertion attachment surface.
    :type insertion_surface: :class:`bpy.types.Object`
    :arg bones: ``(origin_bone, insertion_bone)`` (orient the normals; None allowed).
    :type bones: sequence of :class:`bpy.types.Object`
    :arg count: Number of fibres (approximate).
    :type count: int
    :arg thickness: Half-thickness ``h(u)``; default :func:`default_thickness`.
    :type thickness: callable
    :arg sections: Ring sections ``(u, width, thickness, twist)``, or None for
       the natural fan. ``width`` is the fan's half-width along its widest
       direction, ``twist`` the angle of that direction about the path from
       the path's transported normal.
    :type sections: list of tuple
    :return: ``(courses, radii, natural)``: ``courses`` is an array
       (fibres, ``FIBRE_SAMPLES``, 3) of world-space points, ``radii`` an
       array (``FIBRE_SAMPLES``,) of half-thicknesses, and ``natural`` a list
       of ``(u, half_width, angle)`` of the natural fan (for default rings).
    :rtype: tuple
    :raises ValueError: If an attachment has no faces.
    """
    starts, s_norms = sample_surface(origin_surface, count)
    ends, e_norms = sample_surface(insertion_surface, max(8, count // 4))
    if not starts or not ends:
        raise ValueError("both attachments need faces")
    thickness = thickness or default_thickness(path_points)
    o_sign = preview.outward_sign(origin_surface, bones[0]) if bones else 1
    i_sign = preview.outward_sign(insertion_surface, bones[1]) if bones and len(bones) > 1 else 1
    h0, h1 = thickness(0.0), thickness(1.0)
    S = np.array([list(p + n * (o_sign * h0)) for p, n in zip(starts, s_norms)])
    E = np.array([list(p + n * (i_sign * h1)) for p, n in zip(ends, e_norms)])
    P0, P1 = path_points[0], path_points[-1]
    axis, n_ax, b_ax = _fixed_basis(P1 - P0 if (P1 - P0).length else Vector((0, 0, 1)))
    basis = np.array([list(n_ax), list(b_ax), list(axis)])          # rows
    s_mean, e_mean = S.mean(0), E.mean(0)
    s_loc = (S - s_mean) @ basis.T                                # coordinates in the fixed frame
    e_std = ((E - e_mean) @ basis.T).std(0)
    s_std = np.maximum(s_loc.std(0), 1e-9)
    scale = e_std / s_std
    scale[2] = 0.0                                                # all ends at the insertion's depth
    ends_m = e_mean + (s_loc * scale) @ basis                     # matched end of every fibre
    # the path's bend: offset of each path point from the chord P0 -> P1
    m = len(path_points)
    chord = np.array([list(P0.lerp(P1, k / (m - 1))) for k in range(m)])
    bend = np.array([list(p) for p in path_points]) - chord
    tangents, normals = tube.frames(path_points)
    us = np.linspace(0.0, 1.0, FIBRE_SAMPLES)
    secs = sorted(sections, key=lambda s: s[0]) if sections else None
    courses = np.empty((len(S), FIBRE_SAMPLES, 3))
    radii = np.empty(FIBRE_SAMPLES)
    natural = []
    for k, u in enumerate(us):
        j = u * (m - 1)
        i0 = min(int(j), m - 2)
        x = j - i0
        b_off = bend[i0] * (1 - x) + bend[i0 + 1] * x
        pts = S * (1.0 - u) + ends_m * u + b_off                   # (fibres, 3)
        t = tangents[i0].lerp(tangents[i0 + 1], x).normalized()
        nrm = normals[i0].lerp(normals[i0 + 1], x)
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bi = t.cross(nrm)
        T, N, B = np.array(t), np.array(nrm), np.array(bi)
        centre = pts.mean(0)
        rel = pts - centre
        flat = np.stack([rel @ N, rel @ B], axis=1)                # section coordinates
        cov = flat.T @ flat / max(len(flat), 1)
        _w, v = np.linalg.eigh(cov)
        major = v[:, 1]
        angle = math.atan2(major[1], major[0])
        a_coord = flat @ major
        half_width = float(np.abs(a_coord).max()) if len(a_coord) else 0.0
        natural.append((float(u), half_width, angle))
        radius = thickness(u)
        if secs:
            width, radius, twist = tube._interp_sections(secs, float(u))
            minor = np.array((-major[1], major[0]))
            b_coord = flat @ minor
            turn = twist - angle
            ca, sa = math.cos(turn), math.sin(turn)
            major_r = np.array((ca * major[0] - sa * major[1], sa * major[0] + ca * major[1]))
            minor_r = np.array((-major_r[1], major_r[0]))
            a_new = a_coord * (width / max(half_width, 1e-9))
            new_flat = np.outer(a_new, major_r) + np.outer(b_coord, minor_r)
            along = rel @ T
            pts = centre + np.outer(new_flat[:, 0], N) + np.outer(new_flat[:, 1], B) + np.outer(along, T)
        radii[k] = radius
        courses[:, k, :] = pts
    return courses, radii, natural


#: Fibres used to measure the natural fan (for the rings).
NATURAL_FIBRES = 60


def natural_profile(path_points, origin_surface, insertion_surface, bones):
    """The fan's natural section along the path, as used by the rings.

    :arg path_points: Arc-length samples of the path.
    :type path_points: list of :class:`mathutils.Vector`
    :arg origin_surface: Origin attachment surface.
    :type origin_surface: :class:`bpy.types.Object`
    :arg insertion_surface: Insertion attachment surface.
    :type insertion_surface: :class:`bpy.types.Object`
    :arg bones: ``(origin_bone, insertion_bone)``.
    :type bones: sequence of :class:`bpy.types.Object`
    :return: ``natural(u) -> (half_width, half_thickness, angle)``: the fan's
       half-width along its widest direction, the default half-thickness and
       the angle of the widest direction about the path.
    :rtype: callable
    """
    _c, _r, nat = fibres(path_points, origin_surface, insertion_surface, bones, NATURAL_FIBRES)
    h = default_thickness(path_points)
    us = [n[0] for n in nat]
    widths = [n[1] for n in nat]
    angles = [nat[0][2]]
    for _u, _w, a in nat[1:]:                                   # unwrap (the widest direction repeats every π)
        while a - angles[-1] > math.pi / 2:
            a -= math.pi
        while a - angles[-1] < -math.pi / 2:
            a += math.pi
        angles.append(a)

    def natural(u):
        return (max(float(np.interp(u, us, widths)), h(u)), h(u), float(np.interp(u, us, angles)))
    return natural


def occupancy(courses, radii, xs, ys, zs):
    """Voxels within each fibre's radius of its course (union of capsules).

    Each fibre is sampled densely enough (spacing ≤ half the radius) and a
    sphere is stamped at every sample. Samples are grouped by radius
    (quantised to ``RADIUS_STEP`` voxel) so each group is written at once with
    a precomputed spherical stencil.

    :arg courses: Fibre courses (fibres, samples, 3).
    :type courses: :class:`numpy.ndarray`
    :arg radii: Radius at each sample (samples,).
    :type radii: :class:`numpy.ndarray`
    :arg xs: Voxel-centre X coordinates (evenly spaced).
    :type xs: :class:`numpy.ndarray`
    :arg ys: Voxel-centre Y coordinates.
    :type ys: :class:`numpy.ndarray`
    :arg zs: Voxel-centre Z coordinates.
    :type zs: :class:`numpy.ndarray`
    :return: Boolean array (len(xs), len(ys), len(zs)).
    :rtype: :class:`numpy.ndarray`
    """
    voxel = float(xs[1] - xs[0])
    shape = np.array((len(xs), len(ys), len(zs)))
    occ = np.zeros(tuple(shape), dtype=bool)
    grid0 = np.array((xs[0], ys[0], zs[0]))
    f, n, _ = courses.shape
    # densify each segment k so consecutive samples are <= half the radius apart
    pts, rad = [], []
    for k in range(n - 1):
        a, b = courses[:, k], courses[:, k + 1]
        r = 0.5 * (radii[k] + radii[k + 1])
        seg = float(np.linalg.norm(b - a, axis=1).max())
        steps = max(1, int(math.ceil(seg / max(0.5 * r, 0.5 * voxel))))
        for j in range(steps):
            t = j / steps
            pts.append(a + (b - a) * t)
            rad.append(np.full(f, radii[k] + (radii[k + 1] - radii[k]) * t))
    pts.append(courses[:, -1])
    rad.append(np.full(f, radii[-1]))
    P = np.concatenate(pts)
    R = np.concatenate(rad) / voxel
    centre = np.rint((P - grid0) / voxel).astype(np.int64)
    levels = np.maximum(np.rint(R / RADIUS_STEP).astype(int), 1)
    for level in np.unique(levels):
        r = level * RADIUS_STEP
        span = int(math.ceil(r))
        g = np.arange(-span, span + 1)
        di, dj, dk = np.meshgrid(g, g, g, indexing='ij')
        inside = di ** 2 + dj ** 2 + dk ** 2 <= r * r
        stencil = np.stack([di[inside], dj[inside], dk[inside]], axis=1)
        c = np.unique(centre[levels == level], axis=0)
        for chunk in range(0, len(c), STAMP_CHUNK):
            idx = (c[chunk:chunk + STAMP_CHUNK, None, :] + stencil[None, :, :]).reshape(-1, 3)
            ok = np.all((idx >= 0) & (idx < shape), axis=1)
            idx = idx[ok]
            occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return occ
