"""Tube of a muscle: an elliptical section swept along the muscle path.

The path ``<M>_curve`` (edited by the user) gives the course; the section
size and turn along it come either from the muscle type's default profile
(:func:`default_profile`) or from the section rings placed on the path
(:mod:`rings`). The tube guarantees that the solid belly joins both
attachments (e.g. a fusiform muscle between two long bones).
"""

import math

import bmesh
from mathutils import Vector
from mathutils.geometry import interpolate_bezier


#: End section radius = this x the radius of a disc with the attachment's area.
ATTACHMENT_RADIUS_FRACTION = 0.6
#: Per muscle type: ``(belly, thickness)``. Section radius = attachment radii
#: blended along the course x ``1 + belly·sin(πt)``; thickness = height / width.
TYPE_PROFILES = {
    'FUSIFORM': (0.8, 1.0),
    'PARALLEL': (0.0, 0.6),
    'FAN': (0.0, 0.8),
}
#: Sections of the default profile.
DEFAULT_SECTIONS = 5
#: Points per section of the swept tube.
ELLIPSE_POINTS = 32


def frames(points):
    """Unit tangents and parallel-transported normals along ``points``.

    :arg points: Course points.
    :type points: list of :class:`mathutils.Vector`
    :return: ``(tangents, normals)``.
    :rtype: tuple
    """
    tangents = []
    for k in range(len(points)):
        t = points[min(k + 1, len(points) - 1)] - points[max(k - 1, 0)]
        tangents.append(t.normalized() if t.length else Vector((0, 0, 1)))
    normal = tangents[0].orthogonal().normalized()
    normals = [normal]
    for k in range(1, len(points)):
        normal = tangents[k - 1].rotation_difference(tangents[k]) @ normal
        normal = (normal - tangents[k] * normal.dot(tangents[k])).normalized()
        normals.append(normal)
    return tangents, normals


def attachment_radius(surface_obj):
    """Radius used for the tube end at an attachment.

    :arg surface_obj: Attachment surface.
    :type surface_obj: :class:`bpy.types.Object`
    :return: ``ATTACHMENT_RADIUS_FRACTION`` x radius of a disc of the same area.
    :rtype: float
    """
    area = sum(p.area for p in surface_obj.data.polygons) * surface_obj.matrix_world.median_scale ** 2
    return ATTACHMENT_RADIUS_FRACTION * math.sqrt(max(area, 1e-12) / math.pi)


#: Samples of the path per Bezier segment before arc-length resampling.
CURVE_RESOLUTION = 32
#: Arc-length samples of the path used for the tube.
PATH_SAMPLES = 96


def sample_path(curve_obj, samples=PATH_SAMPLES):
    """Points along the evaluated path, evenly spaced by arc length (world space).

    :arg curve_obj: Path curve (first spline; Bezier, poly or NURBS points).
    :type curve_obj: :class:`bpy.types.Object`
    :arg samples: Number of points (≥ 2).
    :type samples: int
    :return: ``samples`` points from the first to the last control point.
    :rtype: list of :class:`mathutils.Vector`
    :raises ValueError: If the curve has fewer than 2 points.
    """
    spline = curve_obj.data.splines[0] if curve_obj.data.splines else None
    mw = curve_obj.matrix_world
    dense = []
    if spline is not None and spline.type == 'BEZIER' and len(spline.bezier_points) >= 2:
        bps = spline.bezier_points
        pairs = list(zip(bps[:-1], bps[1:])) + ([(bps[-1], bps[0])] if spline.use_cyclic_u else [])
        for a, b in pairs:
            seg = interpolate_bezier(a.co, a.handle_right, b.handle_left, b.co, CURVE_RESOLUTION + 1)
            dense.extend(seg if not dense else seg[1:])
    elif spline is not None and len(spline.points) >= 2:
        dense = [Vector(p.co[:3]) for p in spline.points]
    if len(dense) < 2:
        raise ValueError("the path needs at least 2 points")
    dense = [mw @ p for p in dense]
    cum = [0.0]
    for a, b in zip(dense[:-1], dense[1:]):
        cum.append(cum[-1] + (b - a).length)
    total = cum[-1] or 1.0
    out, j = [], 0
    for k in range(samples):
        target = total * k / (samples - 1)
        while j < len(cum) - 2 and cum[j + 1] < target:
            j += 1
        span = (cum[j + 1] - cum[j]) or 1.0
        out.append(dense[j].lerp(dense[j + 1], (target - cum[j]) / span))
    return out


def project_on_path(points, location):
    """Arc-length fraction (0-1) of the point of a sampled path nearest to ``location``.

    :arg points: Arc-length samples (:func:`sample_path`).
    :type points: list of :class:`mathutils.Vector`
    :arg location: World-space point.
    :type location: :class:`mathutils.Vector`
    :rtype: float
    """
    best, best_u = float("inf"), 0.0
    n = len(points)
    for k in range(n - 1):
        a, b = points[k], points[k + 1]
        ab = b - a
        t = min(max((location - a).dot(ab) / (ab.length_squared or 1.0), 0.0), 1.0)
        d = (a + ab * t - location).length
        if d < best:
            best, best_u = d, (k + t) / (n - 1)
    return best_u


def default_profile(origin_surface, insertion_surface, shape):
    """Default sections ``(u, width, thickness, twist)`` of a muscle type.

    :arg origin_surface: Origin attachment surface.
    :type origin_surface: :class:`bpy.types.Object`
    :arg insertion_surface: Insertion attachment surface.
    :type insertion_surface: :class:`bpy.types.Object`
    :arg shape: Muscle type (``TYPE_PROFILES`` key).
    :type shape: str
    :rtype: list of tuple
    """
    belly, thickness = TYPE_PROFILES.get(shape, (0.0, 1.0))
    r0, r1 = attachment_radius(origin_surface), attachment_radius(insertion_surface)
    out = []
    for k in range(DEFAULT_SECTIONS):
        u = k / (DEFAULT_SECTIONS - 1)
        r = (r0 * (1 - u) + r1 * u) * (1.0 + belly * math.sin(math.pi * u))
        out.append((u, r, r * thickness, 0.0))
    return out


def _interp_sections(sections, u):
    """Width, thickness and twist at ``u`` (smooth between sections sorted by u)."""
    if u <= sections[0][0]:
        return sections[0][1:]
    if u >= sections[-1][0]:
        return sections[-1][1:]
    for a, b in zip(sections[:-1], sections[1:]):
        if a[0] <= u <= b[0]:
            x = (u - a[0]) / ((b[0] - a[0]) or 1.0)
            x = x * x * (3 - 2 * x)
            return tuple(av * (1 - x) + bv * x for av, bv in zip(a[1:], b[1:]))
    return sections[-1][1:]


def path_tube(points, sections, ellipse=ELLIPSE_POINTS):
    """Closed tube along a sampled path, sized and turned by ``sections``.

    :arg points: Arc-length samples of the path (:func:`sample_path`).
    :type points: list of :class:`mathutils.Vector`
    :arg sections: ``(u, width, thickness, twist)`` with ``u`` the arc-length
       fraction (0 = origin end, 1 = insertion end) and ``twist`` the turn of
       the width direction about the path (radians, from the path's
       parallel-transported normal).
    :type sections: list of tuple
    :arg ellipse: Points per section.
    :type ellipse: int
    :return: New world-space bmesh with outward normals (caller frees it).
    :rtype: :class:`bmesh.types.BMesh`
    :raises ValueError: With fewer than 2 path points or no section.
    """
    if len(points) < 2 or not sections:
        raise ValueError("the tube needs a path and at least one section")
    sections = sorted(sections, key=lambda s: s[0])
    tangents, normals = frames(points)
    n = len(points)
    bm = bmesh.new()
    loops = []
    for k, (c, t, nrm) in enumerate(zip(points, tangents, normals)):
        w, h, twist = _interp_sections(sections, k / (n - 1))
        b = t.cross(nrm)
        major = nrm * math.cos(twist) + b * math.sin(twist)
        minor = t.cross(major)
        loops.append([bm.verts.new(c + major * (max(w, 1e-6) * math.cos(2 * math.pi * j / ellipse))
                                   + minor * (max(h, 1e-6) * math.sin(2 * math.pi * j / ellipse)))
                      for j in range(ellipse)])
    _bridge_and_cap(bm, loops, ellipse)
    return bm


def _bridge_and_cap(bm, loops, ellipse):
    for a_loop, b_loop in zip(loops[:-1], loops[1:]):
        for k in range(ellipse):
            bm.faces.new([a_loop[k], a_loop[(k + 1) % ellipse], b_loop[(k + 1) % ellipse], b_loop[k]])
    for loop, reverse in ((loops[0], True), (loops[-1], False)):
        centre = bm.verts.new(sum((v.co for v in loop), Vector()) / ellipse)
        for k in range(ellipse):
            tri = [centre, loop[k], loop[(k + 1) % ellipse]]
            bm.faces.new(tri[::-1] if reverse else tri)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
