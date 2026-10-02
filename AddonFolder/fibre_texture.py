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
``Object.myogen_tendon_origin`` / ``_insertion``; changing any recomputes
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
BUMP_PER_BUNDLE = 0.6
#: Default tendon length at each end (fraction of the muscle).
DEFAULT_TENDON = 0.04
#: Default pennation angle (degrees) when the scene's pennation is 0.
DEFAULT_PENNATION = 20.0


def fibre_coordinates(vertices, path_points, arrangement, pennation_deg=DEFAULT_PENNATION,
                      bundles=None):
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
    th = np.interp(u, centres_u, theta)
    hw = np.maximum(np.interp(u, centres_u, half), 1e-9)
    a = dn * np.cos(th) + db * np.sin(th)                     # across the width
    r = -dn * np.sin(th) + db * np.cos(th)                    # through the thickness
    alpha = math.radians(pennation_deg)
    if arrangement in ('PARALLEL', 'FUSIFORM', 'CONVERGENT'):
        # Fibres along the path: the phase is the angle around the section's
        # axis (elliptical, so flat sections spread it over their width),
        # times a radius: the distance around the section for Parallel, the
        # same for every section (fibres converging as the section narrows)
        # for Fusiform and Convergent.
        hr = np.maximum(np.interp(u, centres_u, thick), 1e-9)
        angle = np.arctan2(r / hr, a / hw)
        if arrangement == 'PARALLEL':                           # constant spacing: smoothed local radius
            radius = np.interp(u, centres_u, _smooth((half + thick) / 2.0, RADIUS_SMOOTHING))
        else:                                                   # same for every section: fibres converge
            radius = float(np.mean((half + thick) / 2.0))
        phase, fibre_along = angle * radius, along
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


def tendon_mask(u, origin_fraction, insertion_fraction):
    """Tendon colour weight (0-1) along the muscle.

    1 at each end, fading to 0 over ``origin_fraction`` / ``insertion_fraction``
    of the length (smooth step); 0 fractions give no tendon at that end.

    :arg u: Position along the path (0-1), per vertex.
    :type u: :class:`numpy.ndarray`
    :arg origin_fraction: Tendon length at the origin, fraction of the muscle.
    :type origin_fraction: float
    :arg insertion_fraction: Tendon length at the insertion.
    :type insertion_fraction: float
    :rtype: :class:`numpy.ndarray`
    """
    def fade(x, f):
        if f <= 0.0:
            return np.zeros_like(x)
        t = np.clip(1.0 - x / f, 0.0, 1.0)
        return t * t * (3.0 - 2.0 * t)
    return np.maximum(fade(u, origin_fraction), fade(1.0 - u, insertion_fraction))


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
    coords, u = fibre_coordinates(V, tube.sample_path(path), arrangement, pennation_deg,
                                  belly.myogen_fibre_bundles)
    tendon = tendon_mask(u, belly.myogen_tendon_origin, belly.myogen_tendon_insertion)
    bump = np.full(len(u), bundle_size(V, coords) * BUMP_PER_BUNDLE)
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
    bpy.types.Object.myogen_tendon_origin = bpy.props.FloatProperty(
        name="Tendon at origin", default=DEFAULT_TENDON, min=0.0, max=0.5, subtype='FACTOR',
        update=_on_fibre_setting_changed,
        description="Length of the pale tendon colour at the origin end, as a fraction of the muscle "
                    "(visual only; 0 = none)")
    bpy.types.Object.myogen_tendon_insertion = bpy.props.FloatProperty(
        name="Tendon at insertion", default=DEFAULT_TENDON, min=0.0, max=0.5, subtype='FACTOR',
        update=_on_fibre_setting_changed,
        description="Length of the pale tendon colour at the insertion end, as a fraction of the muscle "
                    "(visual only; 0 = none)")
    bpy.types.Object.myogen_pennation = bpy.props.FloatProperty(
        name="Pennation (°)", default=DEFAULT_PENNATION, min=0.0, max=60.0, precision=0,
        update=_on_fibre_setting_changed,
        description="Angle between the fibres and the tendon in the texture of pennate arrangements "
                    "(visual only; the PCSA uses the scene's pennation angle)")


def unregister():
    """Remove the per-belly fibre settings."""
    for name in ("myogen_fibres", "myogen_pennation", "myogen_fibre_bundles", "myogen_tendon_origin",
                 "myogen_tendon_insertion"):
        if hasattr(bpy.types.Object, name):
            delattr(bpy.types.Object, name)
