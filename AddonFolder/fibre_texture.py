"""Fibre-oriented muscle texture (visual only).

The procedural muscle material (:mod:`muscle_texture`) draws elongated fibre
bundles. Here its texture coordinates follow the muscle's fibre architecture
instead of the object's axes: for every vertex of a belly
:func:`fibre_coordinates` measures where it lies along the muscle path,
across the section's width and through its thickness, and turns that into a
*phase* (constant along a fibre, changing across fibres) and an *along*
coordinate for the chosen arrangement:

=============  =================================================================
Parallel       fibres along the path, evenly spaced across the width
Fusiform       fibres along the path, converging towards both ends
Convergent     fibres fanning out from the insertion (fan-shaped muscles)
Pennate        fibres at the pennation angle from a tendon along one side
Bipennate      fibres in a "V" from a central tendon
Multipennate   several internal tendons, fibres in alternating "V"s
=============  =================================================================

The coordinates are stored on the mesh as the point attributes
``myo_fibre`` (vector: along, phase, depth, normalised 0-1 like object
coordinates), ``myo_fibre_u`` (0 at the origin, 1 at the insertion) and
``myo_tendon`` (pale tendon colour weight), which the muscle material reads
(:func:`muscle_texture.create_fibre_material`). Each belly carries its
choices in ``Object.myogen_fibres``, ``Object.myogen_pennation`` and
``Object.myogen_tendon_origin`` / ``_insertion`` / ``_fade`` (the tendon
colour follows the distance to each attachment surface); changing any recomputes
the attributes at once.
"""

import math

import bpy
import numpy as np

from . import myo_record, tube
from .muscle_texture import create_fibre_material

#: Arrangements: (identifier, label, description).
ARRANGEMENTS = [
    ('PARALLEL', "Parallel", "Fibres run along the muscle, evenly spaced across its width"),
    ('FUSIFORM', "Fusiform", "Fibres run along the muscle and converge towards both ends"),
    ('CONVERGENT', "Convergent (fan)", "Fibres fan out from the insertion over the width of the origin"),
    ('PENNATE', "Pennate", "Fibres at the pennation angle from a tendon along one side"),
    ('BIPENNATE', "Bipennate", "Fibres in a V from a central tendon, at the pennation angle"),
    ('MULTIPENNATE', "Multipennate", "Several internal tendons; fibres in alternating Vs at the pennation angle"),
]
#: Arrangements that use the pennation angle.
PENNATE = {'PENNATE', 'BIPENNATE', 'MULTIPENNATE'}
#: Internal tendons of a multipennate muscle.
MULTIPENNATE_TENDONS = 3
#: Sections along the path used to find the width direction and half-width.
SECTION_BINS = 24
#: A section whose smaller spread is at least this fraction of the larger is
#: round: it keeps the width direction of the previous section.
ROUND_SECTION = 0.6
#: Sections averaged when smoothing the section radius along the path.
RADIUS_SMOOTHING = 7
#: Default arrangement per muscle type.
TYPE_ARRANGEMENT = {'FUSIFORM': 'FUSIFORM', 'PARALLEL': 'PARALLEL', 'FAN': 'CONVERGENT'}
#: Default fibre bundles across the muscle's width.
DEFAULT_BUNDLES = 30.0
#: Cells across one unit of the material's Y coordinate (Mapping scale x Voronoi scale).
MATERIAL_CELLS_ACROSS = 144.0
#: Bump depth of the texture, in bundle widths.
BUMP_PER_BUNDLE = 2.0
#: Fibres of the fan model used to orient a Convergent texture.
FIELD_FIBRES = 160
#: Default width of the fade from tendon to muscle (fraction of the muscle).
DEFAULT_TENDON_FADE = 0.08
#: Default solid tendon reach from each attachment (fraction of the muscle).
DEFAULT_TENDON = 0.01
#: Default pennation angle (degrees) when the scene's pennation is 0.
DEFAULT_PENNATION = 20.0


def fibre_coordinates(vertices, path_points, arrangement, pennation_deg=DEFAULT_PENNATION,
                      bundles=None, attachment_u=None, fan_field=None):
    """Fibre texture coordinates of points of a belly.

    :arg vertices: World-space vertex positions, (N, 3).
    :type vertices: :class:`numpy.ndarray`
    :arg path_points: Arc-length samples of the muscle path (:func:`tube.sample_path`).
    :type path_points: list of :class:`mathutils.Vector`
    :arg arrangement: One of ``ARRANGEMENTS``.
    :type arrangement: str
    :arg pennation_deg: Angle between fibres and tendon (pennate arrangements).
    :type pennation_deg: float
    :arg bundles: Fibre bundles across the muscle's width drawn by the
       material (default ``DEFAULT_BUNDLES``); scales the across and depth
       coordinates.
    :type bundles: float
    :arg attachment_u: Position between the attachments (0 at the origin, 1 at
       the insertion) of every point (:func:`attachment_position`). Smooth
       everywhere, unlike the nearest point of the path, which jumps where a
       broad muscle is equally far from two parts of a curved path (a line
       across the texture). Default: the nearest point of the path.
    :type attachment_u: :class:`numpy.ndarray`
    :arg fan_field: Fibre bundle sections of the fan model
       (:func:`fan_fibre_field`): for ``CONVERGENT`` the phase of every point
       is its position across that bundle at its ``u``, so the texture's
       fibres spread over the whole origin and converge on the insertion
       like the fan's fibres.
    :type fan_field: tuple
    :return: ``(coords, u)``: (N, 3) ``(along, phase, depth)`` in units such
       that ``bundles`` bundles span the mean width, and (N,) position along
       the path (0-1).
    :rtype: tuple of :class:`numpy.ndarray`
    """
    P = np.array([list(p) for p in path_points])
    tangents, normals = tube.frames(path_points)
    T = np.array([list(t) for t in tangents])
    N = np.array([list(n) for n in normals])
    B = np.cross(T, N)
    seg_len = np.linalg.norm(P[1:] - P[:-1], axis=1)
    cum = np.concatenate(([0.0], np.cumsum(seg_len)))
    length = float(cum[-1]) or 1.0
    V = np.asarray(vertices, dtype=float)
    # nearest point of the path: segment and parameter
    best = np.full(len(V), np.inf)
    seg = np.zeros(len(V), dtype=int)
    par = np.zeros(len(V))
    for i in range(len(P) - 1):
        ab = P[i + 1] - P[i]
        t = np.clip((V - P[i]) @ ab / max(float(ab @ ab), 1e-18), 0.0, 1.0)
        d = np.linalg.norm(V - (P[i] + np.outer(t, ab)), axis=1)
        closer = d < best
        best[closer], seg[closer], par[closer] = d[closer], i, t[closer]
    if attachment_u is not None:
        u = np.clip(np.asarray(attachment_u, dtype=float), 0.0, 1.0)
        along = u * length
    else:
        along = cum[seg] + par * seg_len[seg]
        u = along / length
    k = np.clip(np.rint(seg + par).astype(int), 0, len(P) - 1)
    centre = P[seg] + (P[seg + 1] - P[seg]) * par[:, None]
    d = V - centre
    dn = np.einsum('ij,ij->i', d, N[k])
    db = np.einsum('ij,ij->i', d, B[k])
    # width direction and half-width of the section, per bin along the path
    bins = np.minimum((u * SECTION_BINS).astype(int), SECTION_BINS - 1)
    theta = np.zeros(SECTION_BINS)
    half = np.full(SECTION_BINS, np.nan)
    have = np.zeros(SECTION_BINS, dtype=bool)
    for b in range(SECTION_BINS):
        sel = bins == b
        if sel.sum() >= 6:
            q = np.stack([dn[sel], db[sel]], axis=1)
            cov = q.T @ q / len(q)
            w, v = np.linalg.eigh(cov)
            prev = theta[b - 1] if b and have[b - 1] else None
            if prev is not None and w[0] > ROUND_SECTION * w[1]:
                theta[b] = prev                                 # round section: no defined width direction
            else:
                theta[b] = math.atan2(v[1, 1], v[0, 1])
                if prev is not None:                            # keep the direction consistent
                    while theta[b] - prev > math.pi / 2:
                        theta[b] -= math.pi
                    while theta[b] - prev < -math.pi / 2:
                        theta[b] += math.pi
            have[b] = True
    if have.any():                                              # fill gaps and smooth along the path
        idx = np.arange(SECTION_BINS)
        theta = np.interp(idx, idx[have], theta[have])
        theta = np.convolve(np.pad(theta, 2, mode='edge'), np.ones(5) / 5, mode='valid')
    thick = np.full(SECTION_BINS, np.nan)
    for b in range(SECTION_BINS):
        sel = bins == b
        if sel.sum() >= 6:
            a_b = dn[sel] * math.cos(theta[b]) + db[sel] * math.sin(theta[b])
            r_b = -dn[sel] * math.sin(theta[b]) + db[sel] * math.cos(theta[b])
            half[b] = np.percentile(np.abs(a_b), 98)
            thick[b] = np.percentile(np.abs(r_b), 98)
    good = ~np.isnan(half)
    centres_u = (np.arange(SECTION_BINS) + 0.5) / SECTION_BINS
    half = np.interp(centres_u, centres_u[good], half[good]) if good.any() else np.ones(SECTION_BINS)
    thick = np.interp(centres_u, centres_u[good], thick[good]) if good.any() else np.ones(SECTION_BINS)
    half = _smooth(half, RADIUS_SMOOTHING)                     # no jumps from section to section
    thick = _smooth(thick, RADIUS_SMOOTHING)
    th = np.interp(u, centres_u, theta)
    hw = np.maximum(np.interp(u, centres_u, half), 1e-9)
    a = dn * np.cos(th) + db * np.sin(th)                     # across the width
    r = -dn * np.sin(th) + db * np.cos(th)                    # through the thickness
    alpha = math.radians(pennation_deg)
    # Every arrangement uses the signed position across the width (smooth,
    # unlike an angle around the axis, which wraps) and the smoothed width.
    if arrangement == 'PARALLEL':
        phase, fibre_along = a, along                          # constant spacing
    elif arrangement == 'CONVERGENT' and fan_field is not None:
        phase, fibre_along = _field_phase(V, u, fan_field), along   # across the fan's own fibre bundle
    elif arrangement in ('FUSIFORM', 'CONVERGENT'):
        phase, fibre_along = a / hw * float(np.mean(half)), along   # converge as the section narrows
    else:
        if arrangement == 'PENNATE':
            across = a + hw                                     # tendon along one side
        elif arrangement == 'BIPENNATE':
            across = np.abs(a)                                  # central tendon
        else:
            spacing = 2.0 * hw / MULTIPENNATE_TENDONS
            across = np.abs(np.mod(a + hw, spacing) - spacing / 2.0)
        phase = -along * math.sin(alpha) + across * math.cos(alpha)
        fibre_along = along * math.cos(alpha) + across * math.sin(alpha)
    # X along the fibres, Y across them, Z through the thickness.
    # One unit for all three coordinates, so the bundles keep the material's
    # own elongation whatever the muscle's proportions: ``bundles`` bundles
    # across the mean width.
    width = 2.0 * float(np.mean(half)) or 1.0
    k = (bundles or DEFAULT_BUNDLES) / MATERIAL_CELLS_ACROSS / width
    coords = np.stack([fibre_along, phase, r], axis=1) * k
    return coords, u


def attachment_position(d_origin, d_insertion):
    """Smooth position between the attachments: 0 on the origin, 1 on the insertion.

    :arg d_origin: Distance of each point to the origin attachment.
    :type d_origin: :class:`numpy.ndarray`
    :arg d_insertion: Distance to the insertion attachment.
    :type d_insertion: :class:`numpy.ndarray`
    :rtype: :class:`numpy.ndarray`
    """
    return d_origin / np.maximum(d_origin + d_insertion, 1e-12)


def fan_fibre_field(path_points, origin_surface, insertion_surface, bones, count=FIELD_FIBRES):
    """Section of the fan's fibre bundle along the muscle: centre, widest direction, half-width.

    :arg path_points: Arc-length samples of the path.
    :type path_points: list of :class:`mathutils.Vector`
    :arg origin_surface: Origin attachment surface.
    :type origin_surface: :class:`bpy.types.Object`
    :arg insertion_surface: Insertion attachment surface.
    :type insertion_surface: :class:`bpy.types.Object`
    :arg bones: ``(origin_bone, insertion_bone)``.
    :type bones: sequence of :class:`bpy.types.Object`
    :arg count: Number of fibres.
    :type count: int
    :return: ``(us, centres, axes, half_widths)`` per fibre sample along the
       muscle (u from 0 to 1): the fibres' centre, their widest direction
       (sign kept consistent) and half-width (world units).
    :rtype: tuple of :class:`numpy.ndarray`
    """
    from . import fan
    courses, _radii, _natural = fan.fibres(path_points, origin_surface, insertion_surface, bones, count)
    n = courses.shape[1]
    us = np.linspace(0.0, 1.0, n)
    centres = courses.mean(0)
    axes = np.empty((n, 3))
    halves = np.empty(n)
    previous = None
    for k in range(n):
        rel = courses[:, k, :] - centres[k]
        _w, v = np.linalg.eigh(rel.T @ rel)
        axis = v[:, 2]
        if previous is not None and axis @ previous < 0.0:
            axis = -axis
        axes[k], previous = axis, axis
        halves[k] = max(float(np.abs(rel @ axis).max()), 1e-9)
    return us, centres, axes, halves


def _field_phase(vertices, u, field):
    """Position of every point across the fan's fibre bundle at its ``u``, scaled so
    the fibres converge as the bundle narrows (constant phase along a fibre)."""
    us, centres, axes, halves = field
    c = np.stack([np.interp(u, us, centres[:, i]) for i in range(3)], axis=1)
    a = np.stack([np.interp(u, us, axes[:, i]) for i in range(3)], axis=1)
    a /= np.maximum(np.linalg.norm(a, axis=1), 1e-12)[:, None]
    hw = np.interp(u, us, halves)
    return np.einsum('ij,ij->i', np.asarray(vertices) - c, a) / hw * float(np.mean(halves))


def bundle_size(vertices, coords):
    """World size of one unit of the fibre coordinates (Blender units per unit).

    :arg vertices: World-space vertex positions, (N, 3).
    :type vertices: :class:`numpy.ndarray`
    :arg coords: Their fibre coordinates (:func:`fibre_coordinates`).
    :type coords: :class:`numpy.ndarray`
    :rtype: float
    """
    span_world = float(np.ptp(np.asarray(vertices), axis=0).max())
    span_coord = float(np.ptp(coords[:, 0])) or 1.0
    return span_world / span_coord / MATERIAL_CELLS_ACROSS


def attachment_distance(vertices, surface_obj):
    """Distance of each point to an attachment surface (Blender units).

    :arg vertices: World-space points, (N, 3).
    :type vertices: :class:`numpy.ndarray`
    :arg surface_obj: Attachment surface.
    :type surface_obj: :class:`bpy.types.Object`
    :rtype: :class:`numpy.ndarray`
    """
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(surface_obj.data)
    bm.transform(surface_obj.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return np.array([tree.find_nearest(Vector(p))[3] for p in np.asarray(vertices).tolist()])


def tendon_mask(d_origin, d_insertion, origin_extent, insertion_extent, fade):
    """Tendon colour weight (0-1) from the distance to each attachment.

    Solid tendon within ``*_extent`` of the attachment surface (so it follows
    the attachment's outline: a line, a "]", a patch), then a smooth fade
    into the muscle over ``fade``; all as fractions of the muscle length.
    A 0 extent gives no tendon at that end.

    :arg d_origin: Distance of each point to the origin attachment / muscle length.
    :type d_origin: :class:`numpy.ndarray`
    :arg d_insertion: Distance to the insertion attachment / muscle length.
    :type d_insertion: :class:`numpy.ndarray`
    :arg origin_extent: Solid tendon reach from the origin.
    :type origin_extent: float
    :arg insertion_extent: Solid tendon reach from the insertion.
    :type insertion_extent: float
    :arg fade: Width of the fade into the muscle.
    :type fade: float
    :rtype: :class:`numpy.ndarray`
    """
    def end(d, extent):
        if extent <= 0.0:
            return np.zeros_like(d)
        t = np.clip(1.0 - (d - extent) / max(fade, 1e-9), 0.0, 1.0)
        return t * t * (3.0 - 2.0 * t)
    return np.maximum(end(d_origin, origin_extent), end(d_insertion, insertion_extent))


def _smooth(values, width):
    """Moving average along the path (edges padded)."""
    pad = width // 2
    return np.convolve(np.pad(values, pad, mode='edge'), np.ones(width) / width, mode='valid')


def apply_fibre_texture(context, belly, arrangement=None, pennation_deg=None):
    """Write the fibre coordinates on a belly and give it the fibre material.

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg belly: Final belly (its collection holds the muscle path).
    :type belly: :class:`bpy.types.Object`
    :arg arrangement: Arrangement (default: ``belly.myogen_fibres``).
    :type arrangement: str
    :arg pennation_deg: Pennation angle (default: ``belly.myogen_pennation``).
    :type pennation_deg: float
    :return: True if applied (False without a path).
    :rtype: bool
    """
    arrangement = arrangement or belly.myogen_fibres
    pennation_deg = belly.myogen_pennation if pennation_deg is None else pennation_deg
    coll = next((c for c in belly.users_collection if myo_record.is_muscle_collection(c)), None)
    path = myo_record.resolve_objects(coll).get("path") if coll else None
    if path is None or path.type != 'CURVE':
        return False
    mesh = belly.data
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    m = np.array(belly.matrix_world)
    V = co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
    objs = myo_record.resolve_objects(coll)
    points = tube.sample_path(path)
    length = sum((b - a).length for a, b in zip(points[:-1], points[1:])) or 1.0
    far = np.full(len(V), np.inf)
    d_o = attachment_distance(V, objs["origin"]) / length if objs.get("origin") else far
    d_i = attachment_distance(V, objs["insertion"]) / length if objs.get("insertion") else far
    both = objs.get("origin") is not None and objs.get("insertion") is not None
    field = None
    if arrangement == 'CONVERGENT' and both:
        props = context.scene.myogen
        field = fan_fibre_field(points, objs["origin"], objs["insertion"],
                                (props.origin_object, props.insertion_object))
    coords, u = fibre_coordinates(V, points, arrangement, pennation_deg, belly.myogen_fibre_bundles,
                                  attachment_u=attachment_position(d_o, d_i) if both else None,
                                  fan_field=field)
    tendon = tendon_mask(d_o, d_i, belly.myogen_tendon_origin, belly.myogen_tendon_insertion,
                         belly.myogen_tendon_fade)
    bump = np.full(len(u), bundle_size(V, coords) * BUMP_PER_BUNDLE * belly.myogen_relief)
    for name, kind, data, key in (("myo_fibre", 'FLOAT_VECTOR', coords, "vector"),
                                  ("myo_fibre_u", 'FLOAT', u, "value"),
                                  ("myo_tendon", 'FLOAT', tendon, "value"),
                                  ("myo_bump", 'FLOAT', bump, "value")):
        attr = mesh.attributes.get(name)
        if attr is not None and (attr.data_type != kind or attr.domain != 'POINT'):
            mesh.attributes.remove(attr)
            attr = None
        if attr is None:
            attr = mesh.attributes.new(name, kind, 'POINT')
        attr.data.foreach_set(key, data.astype(np.float32).ravel())
    material = create_fibre_material(context.scene)
    if mesh.materials.get(material.name) is None or len(mesh.materials) != 1:
        mesh.materials.clear()
        mesh.materials.append(material)
    mesh.update()
    return True


_suspended = False


def _on_fibre_setting_changed(self, context):
    if self.type == 'MESH' and not _suspended:
        apply_fibre_texture(context, self)


def default_arrangement(props):
    """Arrangement used for a new belly of the current muscle type.

    :arg props: Scene settings.
    :type props: :class:`properties.MyoGeneratorProperties`
    :rtype: str
    """
    return TYPE_ARRANGEMENT.get(props.muscle_shape, 'FUSIFORM')


def set_defaults(belly, props):
    """Give a new belly the default arrangement of its type (no recomputation).

    :arg belly: Final belly.
    :type belly: :class:`bpy.types.Object`
    :arg props: Scene settings (muscle type, pennation angle).
    :type props: :class:`properties.MyoGeneratorProperties`
    """
    global _suspended
    _suspended = True                                           # no recomputation per property
    try:
        belly.myogen_pennation = props.pennation_deg if props.pennation_deg > 0 else DEFAULT_PENNATION
        belly.myogen_fibres = default_arrangement(props)
    finally:
        _suspended = False


def register():
    """Add the per-belly fibre settings to ``bpy.types.Object``."""
    bpy.types.Object.myogen_fibres = bpy.props.EnumProperty(
        name="Fibres", items=ARRANGEMENTS, default='FUSIFORM', update=_on_fibre_setting_changed,
        description="Fibre arrangement drawn by the muscle texture (visual only)")
    bpy.types.Object.myogen_fibre_bundles = bpy.props.FloatProperty(
        name="Bundles", default=DEFAULT_BUNDLES, min=2.0, soft_max=150.0, precision=0,
        update=_on_fibre_setting_changed,
        description="Fibre bundles drawn across the muscle's width: fewer = coarser bundles (visual only)")
    bpy.types.Object.myogen_relief = bpy.props.FloatProperty(
        name="Relief", default=1.0, min=0.0, soft_max=4.0, update=_on_fibre_setting_changed,
        description="Depth of the texture's relief (bump), relative to the default (visual only)")
    bpy.types.Object.myogen_tendon_origin = bpy.props.FloatProperty(
        name="Tendon at origin", default=DEFAULT_TENDON, min=0.0, max=0.5, subtype='FACTOR',
        update=_on_fibre_setting_changed,
        description="How far the solid pale tendon colour reaches from the origin attachment, all along its "
                    "outline, as a fraction of the muscle length (visual only; 0 = none)")
    bpy.types.Object.myogen_tendon_insertion = bpy.props.FloatProperty(
        name="Tendon at insertion", default=DEFAULT_TENDON, min=0.0, max=0.5, subtype='FACTOR',
        update=_on_fibre_setting_changed,
        description="How far the solid pale tendon colour reaches from the insertion attachment, all along "
                    "its outline, as a fraction of the muscle length (visual only; 0 = none)")
    bpy.types.Object.myogen_tendon_fade = bpy.props.FloatProperty(
        name="Tendon fade", default=DEFAULT_TENDON_FADE, min=0.0, max=0.6, subtype='FACTOR',
        update=_on_fibre_setting_changed,
        description="Width of the fade from tendon to muscle, as a fraction of the muscle length: larger = "
                    "softer (visual only)")
    bpy.types.Object.myogen_pennation = bpy.props.FloatProperty(
        name="Pennation (°)", default=DEFAULT_PENNATION, min=0.0, max=60.0, precision=0,
        update=_on_fibre_setting_changed,
        description="Angle between the fibres and the tendon in the texture of pennate arrangements "
                    "(visual only; the PCSA uses the scene's pennation angle)")


def unregister():
    """Remove the per-belly fibre settings."""
    for name in ("myogen_fibres", "myogen_pennation", "myogen_fibre_bundles", "myogen_relief", "myogen_tendon_origin",
                 "myogen_tendon_insertion", "myogen_tendon_fade"):
        if hasattr(bpy.types.Object, name):
            delattr(bpy.types.Object, name)
