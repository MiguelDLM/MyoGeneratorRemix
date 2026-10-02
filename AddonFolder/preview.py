"""Loft construction and attachment/bone geometry helpers.

The loft (:func:`build_loft`) is the raw material of the *Along the path*
belly: it is built in memory from the path curve and the two attachment
contours and never shown; :mod:`volume_builder` turns it into the solid
belly that the preview and the final mesh show.

Loft construction
-----------------
Both contours are resampled and matched (:mod:`contour_matching`); for
``FOLLOW_PATH`` each section keeps the interpolated contour's principal axes
and is placed on the path with the muscle-shape profile
(:func:`shape_section`); ``DIRECT_CONNECTION`` interpolates the contours along
the straight segment. The end sections lie exactly on the attachment
contours and the caps are draped over the attachment surfaces; the path only
acts away from the ends (:func:`anchor_weight`). The final belly keeps
``ANCHORED_GROUP`` plus a sculpt mask on the vertices lying on the attachments.
"""


import math

import bmesh
import bpy
from mathutils import Vector

from . import contour_matching, myo_record
from .curve_utilities import (calculate_consistent_orientation_frame, get_bezier_point_at_parameter,
                              reset_orientation_frame)

PREVIEW_MATERIAL = "MyoGen preview"
DEFORM_GROUP = "myo_deform"        # 0 at the attachments, 1 where the belly may move
ANCHORED_GROUP = "myo_anchored"    # on the final belly: vertices lying on the attachments


# --------------------------------------------------------------------------
# Loft construction
# --------------------------------------------------------------------------

def contour_points(contour_obj):
    """World-space points of a contour curve (first spline).

    :arg contour_obj: Contour curve.
    :type contour_obj: :class:`bpy.types.Object`
    :return: Points in order; empty for anything that is not a curve.
    :rtype: list of :class:`mathutils.Vector`
    """
    if not contour_obj or contour_obj.type != 'CURVE' or not contour_obj.data.splines:
        return []
    spline = contour_obj.data.splines[0]
    mw = contour_obj.matrix_world
    if spline.type == 'BEZIER':
        return [mw @ p.co for p in spline.bezier_points]
    return [mw @ Vector(p.co[:3]) for p in spline.points]


def _add_cap(bm, loop, reverse):
    """Close a loop of vertices with a triangle fan around its centre."""
    centre = bm.verts.new(sum((v.co for v in loop), Vector()) / len(loop))
    n = len(loop)
    for k in range(n):
        a, b = loop[k], loop[(k + 1) % n]
        try:
            bm.faces.new([centre, b, a] if reverse else [centre, a, b])
        except ValueError:
            pass


def anchor_weight(t, falloff):
    """How free a loft section is to move, from 0 (anchored) to 1 (free).

    Sections at the attachments (``t`` = 0 or 1) are anchored; the weight rises
    smoothly (smoothstep) over ``falloff`` of the length from each end.

    :arg t: Position along the loft, 0 (origin) to 1 (insertion).
    :type t: float
    :arg falloff: Fraction of the length over which the anchoring fades.
    :type falloff: float
    :rtype: float
    """
    if falloff <= 0.0:
        return 0.0 if t in (0.0, 1.0) else 1.0
    x = min(1.0, min(t, 1.0 - t) / falloff)
    return x * x * (3.0 - 2.0 * x)


def _draped_cap(bm, ring, surface_tree, levels, reverse):
    """Close an end ring with concentric rings projected onto the attachment surface.

    Returns the new vertices (all anchored).
    """
    centroid = sum((v.co for v in ring), Vector()) / len(ring)
    n = len(ring)

    def place(p):
        if surface_tree is None:
            return p
        hit = surface_tree.find_nearest(p)[0]
        return hit if hit is not None else p

    created, outer = [], ring
    for level in range(1, levels + 1):
        shrink = 1.0 - level / (levels + 1)
        inner = [bm.verts.new(place(centroid + (v.co - centroid) * shrink)) for v in ring]
        created += inner
        for j in range(n):
            quad = [outer[j], outer[(j + 1) % n], inner[(j + 1) % n], inner[j]]
            try:
                bm.faces.new(list(reversed(quad)) if reverse else quad)
            except ValueError:
                pass
        outer = inner
    centre = bm.verts.new(place(centroid))
    created.append(centre)
    for j in range(n):
        tri = [outer[j], outer[(j + 1) % n], centre]
        try:
            bm.faces.new(list(reversed(tri)) if reverse else tri)
        except ValueError:
            pass
    return created


def _surface_tree(obj):
    from mathutils.bvhtree import BVHTree
    if obj is None or obj.type != 'MESH' or not obj.data.polygons:
        return None
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def push_out_of_bones(points, bones, clearance, max_depth=None):
    """Move points that lie inside a bone to just outside its surface.

    Inside/outside is decided by ray parity (:func:`inside_bone`), which needs
    a closed bone mesh but not consistent normals (scans often have unreliable
    normals). With ``max_depth``, a point whose nearest bone surface is
    farther than that is left alone: it cannot be a vertex that slipped into
    the bone, so the inside test must be wrong (this used to pull vertices
    tens of millimetres onto the bone).

    :arg points: Points to correct in place (``mathutils.Vector``-like with ``co``
       or plain vectors in a list).
    :type points: list
    :arg bones: Bone objects.
    :type bones: list of :class:`bpy.types.Object`
    :arg clearance: Distance kept from the surface (Blender units).
    :type clearance: float
    :arg max_depth: Largest plausible depth inside the bone (Blender units), or None.
    :type max_depth: float
    :return: Number of points moved.
    :rtype: int
    """
    moved = 0
    for bone in bones:
        tree = _bone_tree(bone)
        for item in points:
            p = item.co if hasattr(item, "co") else item
            q = tree.find_nearest(p)[0] if max_depth is None else tree.find_nearest(p, max_depth)[0]
            if q is None or not inside_bone(tree, p):
                continue
            out = (q - p)
            new = q + (out.normalized() * clearance if out.length > 0.0 else Vector())
            if hasattr(item, "co"):
                item.co = new
            else:
                item[:] = new
            moved += 1
    return moved


#: Muscle-shape presets: ``(belly_bulge, bulge_position, flatness)``.
#: ``NATURAL`` keeps the plain interpolation between the contours.
SHAPE_PRESETS = {
    'FUSIFORM': (0.35, 0.5, 0.75),
    'PARALLEL': (0.0, 0.5, 0.5),
    'FAN': (0.15, 0.65, 0.35),
    'SHEET': (0.0, 0.5, 0.2),
}


#: Shapes whose final mesh defaults to filling the fossa around the origin.
SPACE_FILLING_SHAPES = {'FAN', 'SHEET'}


def belly_bump(t, peak):
    """Belly profile: 0 at both ends, 1 at ``peak``, smooth in between.

    :arg t: Position along the path, 0 (origin) to 1 (insertion).
    :type t: float
    :arg peak: Position of the maximum, 0 to 1.
    :type peak: float
    :rtype: float
    """
    peak = min(max(peak, 0.05), 0.95)
    u = 0.5 * t / peak if t <= peak else 0.5 + 0.5 * (t - peak) / (1.0 - peak)
    return math.sin(math.pi * min(max(u, 0.0), 1.0))


#: Flatness acts fully in the middle and fades out over this fraction of the
#: length at each end, so the section turns smoothly into the attachment outline.
FLATNESS_RAMP = 0.3


def flatness_ramp(t):
    """Weight of the flatness setting along the path: 0 at both ends, 1 in the middle.

    :arg t: Position along the path, 0 to 1.
    :type t: float
    :rtype: float
    """
    x = min(max(min(t, 1.0 - t) / FLATNESS_RAMP, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def curve_tilt(curve_obj, t):
    """Tilt (radians) of the path at ``t``, interpolated between control points.

    Uses the same parameterisation as
    :func:`curve_utilities.get_bezier_point_at_parameter`.

    :arg curve_obj: Muscle path (first spline, Bezier).
    :type curve_obj: :class:`bpy.types.Object`
    :arg t: Parameter along the path, 0 to 1.
    :type t: float
    :rtype: float
    """
    if curve_obj is None or curve_obj.type != 'CURVE' or not curve_obj.data.splines:
        return 0.0
    points = curve_obj.data.splines[0].bezier_points
    if len(points) < 2:
        return 0.0
    seg = 1.0 / (len(points) - 1)
    k = min(int(t / seg), len(points) - 2)
    u = (t - k * seg) / seg
    return points[k].tilt * (1.0 - u) + points[k + 1].tilt * u


def shape_section(points, position, tangent, scale, tilt=0.0, flatness=None, flatness_weight=1.0):
    """Place an interpolated section on the path with the muscle-shape profile.

    The section's own principal axes in the plane normal to the path (major =
    width, minor = thickness) are kept; the section is centred on ``position``,
    scaled by ``scale`` and rotated by ``tilt`` about the tangent. With
    ``flatness`` the thickness is set to ``flatness`` x width (clamped to a
    factor 0.2-5 of the interpolated thickness).

    :arg points: Interpolated section points (world space).
    :type points: list of :class:`mathutils.Vector`
    :arg position: Point on the path.
    :type position: :class:`mathutils.Vector`
    :arg tangent: Path tangent at ``position``.
    :type tangent: :class:`mathutils.Vector`
    :arg scale: Size factor (curve radius x belly bulge).
    :type scale: float
    :arg tilt: Rotation about the tangent (radians).
    :type tilt: float
    :arg flatness: Thickness/width ratio, or None to keep the interpolated one.
    :type flatness: float or None
    :arg flatness_weight: 0-1, how much of the flatness change is applied
       (it fades out towards the attachments, :func:`flatness_ramp`).
    :type flatness_weight: float
    :return: New section points, same order.
    :rtype: list of :class:`mathutils.Vector`
    """
    T = tangent.normalized()
    centre = sum(points, Vector()) / len(points)
    rel = [p - centre for p in points]
    flat = [r - T * r.dot(T) for r in rel]
    ref = max(flat, key=lambda f: f.length)
    if ref.length == 0.0:
        return [position + r * scale for r in rel]
    b1 = ref.normalized()
    b2 = T.cross(b1)
    sxx = sum(f.dot(b1) ** 2 for f in flat)
    syy = sum(f.dot(b2) ** 2 for f in flat)
    sxy = sum(f.dot(b1) * f.dot(b2) for f in flat)
    angle = 0.5 * math.atan2(2.0 * sxy, sxx - syy)
    e1 = b1 * math.cos(angle) + b2 * math.sin(angle)
    e2 = T.cross(e1)
    a = [f.dot(e1) for f in flat]
    b = [f.dot(e2) for f in flat]
    minor = 1.0
    if flatness is not None:
        rms_a = math.sqrt(sum(x * x for x in a) / len(a))
        rms_b = math.sqrt(sum(x * x for x in b) / len(b))
        if rms_b > 0.0:
            minor = min(max(flatness * rms_a / rms_b, 0.2), 5.0)
            minor = 1.0 + (minor - 1.0) * flatness_weight
    r1 = e1 * math.cos(tilt) + e2 * math.sin(tilt)
    r2 = T.cross(r1)
    return [position + r1 * (ai * scale) + r2 * (bi * scale * minor) + T * (r.dot(T) * scale)
            for ai, bi, r in zip(a, b, rel)]


def build_loft(props, curve_obj, origin_contour, insertion_contour, origin_surface=None, insertion_surface=None,
               shape=None):
    """Loft a muscle belly between two contours, anchored to the attachments.

    The first and last sections are exactly the (matched) contour points,
    closed by caps draped over the attachment surfaces. Away from the ends the
    sections follow the path and the muscle-shape profile (:func:`shape_section`:
    curve radius and tilt, belly bulge, flatness), blended in over
    ``props.anchor_falloff`` of the length (:func:`anchor_weight`); smoothing
    never touches anchored vertices. This loft is the live preview and the
    input of :func:`volume_builder.build_belly`, which makes the final belly.

    :arg props: Scene settings (``scene.myogen``): connection mode, matching,
       contour resolution, curve subdivisions, offsets.
    :type props: :class:`properties.MyoGeneratorProperties`
    :arg curve_obj: Muscle path (needed for ``FOLLOW_PATH``).
    :type curve_obj: :class:`bpy.types.Object`
    :arg origin_contour: Origin contour curve.
    :type origin_contour: :class:`bpy.types.Object`
    :arg insertion_contour: Insertion contour curve.
    :type insertion_contour: :class:`bpy.types.Object`
    :arg origin_surface: Origin attachment surface, for the draped cap (None: flat cap).
    :type origin_surface: :class:`bpy.types.Object`
    :arg insertion_surface: Insertion attachment surface, for the draped cap.
    :type insertion_surface: :class:`bpy.types.Object`
    :return: ``(bm, construction)``: a new bmesh (caller frees it) and a dict
       with ``origin``/``insertion`` (matched contour points), ``sections``
       (list of point lists, origin to insertion), ``weights`` (per vertex, in
       bmesh order: 0 = anchored, 1 = free; see :func:`anchor_weight`) and
       ``info`` (matching diagnostics, see :func:`contour_matching.match_contours`).
    :rtype: tuple
    :arg shape: Muscle shape for the profile (default ``props.muscle_shape``);
       ``'NATURAL'`` = plain interpolation.
    :type shape: str
    :raises ValueError: If a contour has fewer than 3 points.
    """
    origin_loop, insertion_loop = contour_points(origin_contour), contour_points(insertion_contour)
    if len(origin_loop) < 3 or len(insertion_loop) < 3:
        raise ValueError("origin and insertion contours need at least 3 points each")
    n = max(6, int(props.muscle_contour_resolution * 0.75))
    origin, insertion, info = prepare_contour_loops(props, origin_loop, insertion_loop, n)

    follow = props.muscle_connection_mode == 'FOLLOW_PATH' and curve_obj is not None
    steps = max(4 if follow else 2, int(props.muscle_curve_subdivisions))
    params = [k / (steps - 1) for k in range(steps)]
    if follow:
        reset_orientation_frame()
        frames = [calculate_consistent_orientation_frame(curve_obj, t) for t in params]

    falloff = props.anchor_falloff
    shaped = (shape or props.muscle_shape) != 'NATURAL'
    bulge = props.belly_bulge if shaped else 0.0
    flatness = props.flatness if shaped else None
    sections, ring_weights = [], []
    for k, t in enumerate(params):
        straight = [o.lerp(i, t) for o, i in zip(origin, insertion)]
        w = anchor_weight(t, falloff)
        if follow and w > 0.0:
            tangent, _normal, _binormal, radius = frames[k]
            position = get_bezier_point_at_parameter(curve_obj, t)[0]
            scale = radius * (1.0 + bulge * belly_bump(t, props.bulge_position))
            on_path = shape_section(straight, position, tangent, scale, curve_tilt(curve_obj, t), flatness,
                                    flatness_ramp(t))
            section = [a.lerp(b, w) for a, b in zip(straight, on_path)]
        else:
            section = straight
        sections.append(section)
        ring_weights.append(w)

    bm = bmesh.new()
    rings = [[bm.verts.new(p) for p in section] for section in sections]
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(n):
            quad = [a[j], b[j], b[(j + 1) % n], a[(j + 1) % n]]
            try:
                bm.faces.new(quad)
            except ValueError:
                pass
    levels = 3
    _draped_cap(bm, rings[0], _surface_tree(origin_surface), levels, reverse=True)
    _draped_cap(bm, rings[-1], _surface_tree(insertion_surface), levels, reverse=False)

    weight_of = {}
    for ring, w in zip(rings, ring_weights):
        for v in ring:
            weight_of[v] = w
    free = [v for v in bm.verts if weight_of.get(v, 0.0) > 0.0]
    if follow and free:
        for _ in range(2):
            bmesh.ops.smooth_vert(bm, verts=free, factor=0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.index_update()
    weights = [weight_of.get(v, 0.0) for v in bm.verts]
    return bm, {"origin": origin, "insertion": insertion, "sections": sections, "weights": weights, "info": info}


def prepare_contour_loops(props, origin_loop, insertion_loop, n):
    """Resample and match the two contours of a loft.

    Both contours are resampled to ``n`` points evenly spaced by arc length.
    With ``props.contour_matching == 'AUTO'`` the insertion contour is
    re-indexed by :func:`contour_matching.match_contours`; with ``'INDEX'``
    points are joined by index as in earlier versions. The manual offsets and
    reversals in ``props`` are applied afterwards as fine-tuning.

    :arg props: Scene settings (``scene.myogen``).
    :type props: :class:`properties.MyoGeneratorProperties`
    :arg origin_loop: Origin contour points.
    :type origin_loop: sequence of :class:`mathutils.Vector`
    :arg insertion_loop: Insertion contour points.
    :type insertion_loop: sequence of :class:`mathutils.Vector`
    :arg n: Points per contour.
    :type n: int
    :return: ``(origin, insertion, info)``: lists of ``n`` vectors in matched order,
       and ``info`` with ``mode``, ``shift``, ``reversed``, ``waist`` (1 = no
       hourglass) and ``section_area`` (mid-section area / end areas; ~0 = folded).
    :rtype: tuple
    """
    if props.contour_matching == 'AUTO':
        o, i, info = contour_matching.match_contours(origin_loop, insertion_loop, n)
    else:
        o = contour_matching.resample_closed_loop(origin_loop, n)
        i = contour_matching.resample_closed_loop(insertion_loop, n)
        info = {"shift": 0, "reversed": False}
    origin = [Vector(p) for p in o]
    insertion = [Vector(p) for p in i]
    origin = contour_matching.apply_match(origin, props.origin_contour_offset % n, props.origin_reverse_orientation)
    insertion = contour_matching.apply_match(insertion, props.insertion_contour_offset % n,
                                             props.insertion_reverse_orientation)
    info["mode"] = props.contour_matching
    info["waist"] = contour_matching.waist_index(origin, insertion)
    info["section_area"] = contour_matching.section_area_ratio(origin, insertion)
    return origin, insertion, info


def describe_match(info):
    """One-line summary of a contour match for the panel and the overlay.

    :arg info: ``info`` returned by :func:`prepare_contour_loops`.
    :type info: dict
    :rtype: str
    """
    text = f"{'Automatic' if info['mode'] == 'AUTO' else 'By index'} matching"
    if info["mode"] == 'AUTO':
        text += f": shift {info['shift']}{', reversed' if info['reversed'] else ''}"
    text += f" | waist {info['waist']:.2f}, mid-section area {info['section_area']:.2f}"
    if is_twisted(info):
        text += " - twisted/hourglass: check the contours or the offsets"
    return text


def is_twisted(info):
    """Whether the matching diagnostics indicate a twisted or hourglass loft.

    :arg info: Matching diagnostics.
    :type info: dict
    :rtype: bool
    """
    return info["waist"] < 0.8 or info["section_area"] < 0.5


# --------------------------------------------------------------------------
# Preview object
# --------------------------------------------------------------------------

def muscle_objects(context, muscle_name=None):
    """Collection and objects of the muscle being reconstructed.

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg muscle_name: Muscle (default: ``scene.myogen.muscle_name``).
    :type muscle_name: str
    :return: ``(collection, objects)`` with ``objects`` from
       :func:`myo_record.resolve_objects`; ``(None, {})`` if the muscle
       collection does not exist.
    :rtype: tuple
    """
    name = muscle_name or context.scene.myogen.muscle_name
    root = myo_record.get_root()
    coll = root.children.get(name) if root else None
    if coll is None:
        return None, {}
    return coll, myo_record.resolve_objects(coll)


def _preview_material():
    mat = bpy.data.materials.get(PREVIEW_MATERIAL)
    if mat is None:
        mat = bpy.data.materials.new(PREVIEW_MATERIAL)
        mat.diffuse_color = (0.25, 0.65, 1.0, 0.45)
    return mat


def write_deform_weights(obj, weights):
    """Store per-vertex freedom in the ``DEFORM_GROUP`` vertex group.

    :arg obj: Mesh object.
    :type obj: :class:`bpy.types.Object`
    :arg weights: One weight per vertex (0 = anchored, 1 = free).
    :type weights: sequence of float
    """
    group = obj.vertex_groups.get(DEFORM_GROUP) or obj.vertex_groups.new(name=DEFORM_GROUP)
    by_weight = {}
    for index, w in enumerate(weights):
        by_weight.setdefault(round(w, 6), []).append(index)
    group.remove(list(range(len(obj.data.vertices))))
    for w, indices in by_weight.items():
        group.add(indices, w, 'REPLACE')


def bone_targets(props):
    """Bones the belly must stay outside of (the origin and insertion bones).

    :arg props: Scene settings (``scene.myogen``).
    :type props: :class:`properties.MyoGeneratorProperties`
    :return: Distinct mesh objects (may be empty).
    :rtype: list of :class:`bpy.types.Object`
    """
    out = []
    for obj in (props.origin_object, props.insertion_object):
        if obj is not None and obj.type == 'MESH' and obj not in out:
            out.append(obj)
    return out


_bone_trees = {}


def _bone_tree(obj):
    """Cached world-space BVH of a bone (rebuilt if its mesh changes)."""
    from mathutils.bvhtree import BVHTree
    key = (obj.name, len(obj.data.vertices), tuple(round(x, 4) for x in obj.matrix_world.translation))
    if key not in _bone_trees:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        if len(_bone_trees) > 8:
            _bone_trees.clear()
        _bone_trees[key] = BVHTree.FromBMesh(bm)
        bm.free()
    return _bone_trees[key]


_RAY = Vector((0.31, 0.57, 0.76)).normalized()
#: Three independent ray directions for the inside/outside majority vote.
_RAYS = (_RAY, Vector((-0.83, 0.21, 0.52)).normalized(), Vector((0.17, -0.94, 0.29)).normalized())
#: Vertices less than this deep in a bone (mm) count as contact, not penetration.
DIAGNOSIS_CONTACT_MM = 0.05


def _parity(tree, point, direction):
    hits, origin = 0, point.copy()
    eps = max(1e-4, 1e-6 * (abs(point.x) + abs(point.y) + abs(point.z)))
    for _ in range(256):
        hit = tree.ray_cast(origin, direction)
        if hit[0] is None:
            break
        hits += 1
        origin = hit[0] + direction * eps
    return hits % 2 == 1


def inside_bone(tree, point):
    """True if ``point`` is inside the closed mesh of ``tree`` (ray parity).

    Parity needs a closed mesh but not consistent normals, which scans often
    lack. A single ray that passes exactly through an edge or a vertex counts
    that crossing twice and flips the answer, so the majority of three rays
    in independent directions (``_RAYS``) decides.

    :arg tree: World-space BVH of the bone (:func:`_bone_tree`).
    :type tree: :class:`mathutils.bvhtree.BVHTree`
    :arg point: World-space point.
    :type point: :class:`mathutils.Vector`
    :rtype: bool
    """
    votes = 0
    for k, direction in enumerate(_RAYS):
        votes += _parity(tree, point, direction)
        if votes >= 2 or votes + (len(_RAYS) - 1 - k) < 2:   # decided
            break
    return votes >= 2


def outward_sign(surface_obj, bone_obj, samples=200):
    """+1 if the attachment's face normals point out of the bone, -1 if into it.

    Decided by majority over sampled faces: a point just off each face along
    its normal is tested with :func:`inside_bone`.

    :arg surface_obj: Attachment surface.
    :type surface_obj: :class:`bpy.types.Object`
    :arg bone_obj: Bone it lies on (None: +1).
    :type bone_obj: :class:`bpy.types.Object`
    :arg samples: Faces to test.
    :type samples: int
    :rtype: int
    """
    if bone_obj is None or bone_obj.type != 'MESH' or not surface_obj.data.polygons:
        return 1
    tree = _bone_tree(bone_obj)
    mw = surface_obj.matrix_world
    nm = mw.to_3x3().inverted_safe().transposed()
    size = max(surface_obj.dimensions) or 1.0
    polys = surface_obj.data.polygons
    votes = 0
    for poly in list(polys)[::max(1, len(polys) // samples)]:
        c = mw @ poly.center
        n = (nm @ poly.normal).normalized() * size * 0.01
        a, b = inside_bone(tree, c + n), inside_bone(tree, c - n)
        votes += (1 if b and not a else -1 if a and not b else 0)
    return -1 if votes < 0 else 1


def attachment_anchor(surface_obj, bone_obj=None, toward=None):
    """Where the muscle path should start on an attachment, outside the bone.

    The area centroid of a concave or wrapping attachment (a fossa, a sleeve
    around a process) lies inside the bone. The anchor is the point of the
    surface nearest to the area centroid moved towards the other attachment
    (``toward``) by the surface's RMS size: on a flat patch that is about the
    centroid, on a sleeve the face of the process that looks at the other
    attachment. The normal is that of the nearest face, oriented out of the
    bone (:func:`outward_sign`).

    :arg surface_obj: Attachment surface.
    :type surface_obj: :class:`bpy.types.Object`
    :arg bone_obj: Bone the attachment lies on (orients the normal).
    :type bone_obj: :class:`bpy.types.Object`
    :arg toward: World position of the other attachment (e.g. its centroid).
    :type toward: :class:`mathutils.Vector`
    :return: ``(point, normal, size)``: world-space point on the surface, unit
       outward normal and the RMS distance of the surface from its centroid
       (Blender units).
    :rtype: tuple
    """
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(surface_obj.data)
    bm.transform(surface_obj.matrix_world)
    bm.normal_update()
    area = sum(f.calc_area() for f in bm.faces) or 1.0
    centroid = sum((f.calc_center_median() * f.calc_area() for f in bm.faces), Vector()) / area
    size = math.sqrt(sum((v.co - centroid).length_squared for v in bm.verts) / max(1, len(bm.verts)))
    target = centroid
    if toward is not None and (toward - centroid).length > 0.0:
        target = centroid + (toward - centroid).normalized() * size
    point, normal, _index, _dist = BVHTree.FromBMesh(bm).find_nearest(target)
    bm.free()
    if normal is None or normal.length == 0.0:
        normal = Vector((0.0, 0.0, 1.0))
    normal = normal.normalized() * outward_sign(surface_obj, bone_obj)
    return point, normal, size


def area_centroid(surface_obj):
    """Area-weighted centroid of a surface (world space).

    :arg surface_obj: Mesh object.
    :type surface_obj: :class:`bpy.types.Object`
    :rtype: :class:`mathutils.Vector`
    """
    mw = surface_obj.matrix_world
    total, acc = 0.0, Vector()
    for poly in surface_obj.data.polygons:
        acc += (mw @ poly.center) * poly.area
        total += poly.area
    return acc / total if total else mw.translation.copy()


def diagnose(context, preview):
    """Self-intersections and bone penetration of the (deformed) preview.

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg preview: Preview object.
    :type preview: :class:`bpy.types.Object`
    :return: ``crossing_faces`` (faces that intersect another non-adjacent face),
       ``faces``, ``inside_bone`` (fraction of free vertices inside a bone, by
       ray parity, deeper than ``DIAGNOSIS_CONTACT_MM``; anchored vertices lie
       on the bone by design and are not counted) and ``inside_by_bone`` (bone name -> fraction).
    :rtype: dict
    """
    from mathutils.bvhtree import BVHTree
    evaluated = preview.evaluated_get(context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.transform(preview.matrix_world)
    evaluated.to_mesh_clear()
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    crossing = set()
    for a, b in tree.overlap(tree):
        if a != b and not ({v.index for v in bm.faces[a].verts} & {v.index for v in bm.faces[b].verts}):
            crossing.update((a, b))
    group = preview.vertex_groups.get(DEFORM_GROUP)
    weights = None
    if group is not None and not preview.modifiers:
        weights = [0.0] * len(preview.data.vertices)
        for v in preview.data.vertices:
            for g in v.groups:
                if g.group == group.index:
                    weights[v.index] = g.weight
    points = [v.co.copy() for k, v in enumerate(bm.verts)
              if weights is None or k >= len(weights) or weights[k] > 0.0]   # anchored lie on bone
    faces = len(bm.faces)
    bm.free()

    tolerance = DIAGNOSIS_CONTACT_MM / (1000.0 * myo_record.metres_per_unit(context.scene))
    inside_by_bone, inside_any = {}, set()
    for bone in bone_targets(context.scene.myogen):
        btree = _bone_tree(bone)
        count = 0
        for k, p in enumerate(points):
            if btree.find_nearest(p)[3] > tolerance and inside_bone(btree, p):   # contact is not penetration
                count += 1
                inside_any.add(k)
        inside_by_bone[bone.name] = count / len(points) if points else 0.0
    return {"crossing_faces": len(crossing), "faces": faces,
            "inside_bone": len(inside_any) / len(points) if points else 0.0, "inside_by_bone": inside_by_bone}


def describe_diagnosis(d):
    """One-line summary of :func:`diagnose` for the panel.

    :arg d: Output of :func:`diagnose`.
    :type d: dict
    :rtype: str
    """
    return (f"Crossing faces: {d['crossing_faces']} of {d['faces']} | "
            f"inside bone: {d['inside_bone'] * 100:.1f}% of free vertices")


def protect_anchored(obj):
    """Mark the vertices lying on the attachments of a final belly.

    Creates the ``ANCHORED_GROUP`` vertex group (from ``DEFORM_GROUP`` weights
    of 0) and a sculpt mask on the same vertices, so sculpting and smoothing
    leave them in place.

    :arg obj: Final belly (still carrying ``DEFORM_GROUP``).
    :type obj: :class:`bpy.types.Object`
    :return: Number of anchored vertices.
    :rtype: int
    """
    deform = obj.vertex_groups.get(DEFORM_GROUP)
    if deform is None:
        return 0
    free = {v.index for v in obj.data.vertices
            if any(g.group == deform.index and g.weight > 0.0 for g in v.groups)}
    anchored = [v.index for v in obj.data.vertices if v.index not in free]
    group = obj.vertex_groups.get(ANCHORED_GROUP) or obj.vertex_groups.new(name=ANCHORED_GROUP)
    group.add(anchored, 1.0, 'REPLACE')
    mask = obj.data.attributes.get(".sculpt_mask") or obj.data.attributes.new(".sculpt_mask", 'FLOAT', 'POINT')
    values = [0.0] * len(obj.data.vertices)
    for i in anchored:
        values[i] = 1.0
    mask.data.foreach_set("value", values)
    return len(anchored)


# --------------------------------------------------------------------------
# Muscle path
# --------------------------------------------------------------------------

#: Path ends are lifted off the attachment by this fraction of its RMS size.
PATH_LIFT = 0.25
#: The second and fourth path points bulge along the attachment normals by
#: this fraction of the origin-insertion distance.
PATH_BEND = 0.15
#: Custom property marking a path computed from the belly (Fill fossa).
AUTO_PATH_KEY = "myo_path_auto"


def write_path(collection, muscle_name, points, auto=False):
    """Create or replace ``<M>_curve``: a Bezier through ``points`` (AUTO handles, radius 1).

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg points: World-space points, origin to insertion (≥ 2).
    :type points: sequence of :class:`mathutils.Vector`
    :arg auto: Mark the path as computed (``AUTO_PATH_KEY``).
    :type auto: bool
    :return: The path object.
    :rtype: :class:`bpy.types.Object`
    """
    name = muscle_name + "_curve"
    obj = collection.objects.get(name)
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
    spline = curve.splines.new(type='BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for bp, p in zip(spline.bezier_points, points):
        bp.co = p
        bp.radius = 1.0
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    if obj is None:
        obj = bpy.data.objects.new(name, curve)
        collection.objects.link(obj)
    else:
        old = obj.data
        obj.data = curve
        if old.users == 0:
            bpy.data.curves.remove(old)
    obj.matrix_world.identity()
    obj.show_in_front = True               # visible through the preview while editing
    obj[myo_record.ROLE_KEY] = "path"
    if auto:
        obj[AUTO_PATH_KEY] = True
    elif AUTO_PATH_KEY in obj:
        del obj[AUTO_PATH_KEY]
    return obj


def default_path_points(props, origin_surface, insertion_surface):
    """Five path points leaving each attachment along its outward normal, outside the bone.

    The ends are :func:`attachment_anchor` points (not the centroids, which lie
    inside the bone for concave or wrapping attachments), lifted by
    ``PATH_LIFT`` x the attachment size; the 2nd and 4th points bulge along the
    normals by ``PATH_BEND`` x the origin-insertion distance.

    :arg props: Scene settings (``origin_object``, ``insertion_object``).
    :type props: :class:`properties.MyoGeneratorProperties`
    :arg origin_surface: Origin attachment surface.
    :type origin_surface: :class:`bpy.types.Object`
    :arg insertion_surface: Insertion attachment surface.
    :type insertion_surface: :class:`bpy.types.Object`
    :rtype: list of :class:`mathutils.Vector`
    """
    o_point, o_normal, o_size = attachment_anchor(origin_surface, props.origin_object,
                                                  area_centroid(insertion_surface))
    i_point, i_normal, i_size = attachment_anchor(insertion_surface, props.insertion_object,
                                                  area_centroid(origin_surface))
    lift = PATH_LIFT * min(o_size, i_size)
    start, end = o_point + o_normal * lift, i_point + i_normal * lift
    distance = (end - start).length
    pts = [start.lerp(end, k / 4) for k in range(5)]
    pts[1] = pts[1] + o_normal * distance * PATH_BEND
    pts[3] = pts[3] + i_normal * distance * PATH_BEND
    return pts


def register():
    """Nothing to register (kept for symmetry with the other modules)."""


def unregister():
    """Forget cached bone trees."""
    _bone_trees.clear()
