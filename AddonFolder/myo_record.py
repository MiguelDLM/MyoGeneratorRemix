"""Muscle record: the data contract shared by MyoGeneratorRemix and MUFIS.

This file is OWNED by MyoGeneratorRemix and copied verbatim into MUFIS
(MUFIS/tools/sync_shared.py). Do not edit the MUFIS copy: edit this one, then
run the sync script. Both copies must stay byte-identical.

MyoGeneratorRemix *writes* records; any other tool may *read* them. Nothing in
here imports either add-on, so a .blend reconstructed with MyoGen can be read by
MUFIS on a machine where MyoGen is not installed.

Layout (schema 1)
-----------------
Collection ``muscles/<M>`` carries the record as custom properties (``myo_*``,
see ``RECORD_KEYS``). Objects inside it carry ``myo_role`` (``ROLES``).
Values are SI. Object references are stored as object names, because ID
properties cannot hold pointers; they are resolved and validated on read.

Scenes made before the schema existed are recognised from MyoGen's naming
convention (``<M>_origin``, ``<M>_muscle``, ...) by ``resolve_objects``.
"""

import json
import math

try:
    import bpy
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import interpolate_bezier
except ImportError:  # imported outside Blender: only the pure functions are usable
    bpy = bmesh = Vector = BVHTree = interpolate_bezier = None

SCHEMA_VERSION = 1
ROOT_COLLECTION = "muscles"
ROLE_KEY = "myo_role"
ROOT_TAG = "myo_root"

# role -> legacy object-name suffix
ROLES = {
    "origin": "_origin",
    "insertion": "_insertion",
    "origin_contour": "_origin_contour",
    "insertion_contour": "_insertion_contour",
    "path": "_curve",
    "belly": "_muscle",
}

# record key -> role whose object name it stores
OBJECT_KEYS = {
    "myo_origin_obj": "origin",
    "myo_insertion_obj": "insertion",
    "myo_path_obj": "path",
    "myo_belly_obj": "belly",
}

RECORD_KEYS = (
    "myo_schema", "myo_name", "myo_side",
    "myo_origin_obj", "myo_insertion_obj", "myo_path_obj", "myo_belly_obj",
    "myo_volume_m3", "myo_volume_raw_m3", "myo_volume_method", "myo_mass_kg",
    "myo_path_length_m", "myo_linear_length_m", "myo_fiber_length_m",
    "myo_pcsa_m2", "myo_pcsa_method",
    "myo_fiber_length_ratio", "myo_pennation_deg",
    "myo_fiber_length_source", "myo_fiber_count", "myo_fiber_length_sd_m",
    "myo_fiber_length_min_m", "myo_fiber_length_max_m", "myo_fiber_reached",
    "myo_fiber_detoured", "myo_origin_contact", "myo_insertion_contact",
    "myo_density_g_cm3", "myo_specific_tension_n_cm2", "myo_force_n",
    "myo_origin_area_m2", "myo_insertion_area_m2",
    "myo_qa", "myo_updated",
)

# Herbst et al. (2022) defaults: fibre length = muscle (path) length, parallel
# fibres, 0.3 N/mm2 = 30 N/cm2. Density: Mendez & Keys (1960), 1.0597 g/cm3.
DEFAULT_FIBER_LENGTH_RATIO = 1.0
DEFAULT_PENNATION_DEG = 0.0
#: Where the fibre length comes from: the muscle path (MyoGenerator), or the
#: fibres of the finished belly (Laplacian streamlines, Choi & Blemker 2013).
FIBER_LENGTH_SOURCES = ("PATH", "BELLY_FIBRES")
#: PCSA from the fibres: ``V cos / mean(Lf)``, or the sum over fibres of
#: ``V_i cos / Lf_i`` (each fibre's share of the volume over its own length).
PCSA_MODELS = ("MEAN", "WEIGHTED")
#: Fibre QA: warn when fewer fibres reach the insertion, or when the longest
#: fibre exceeds this multiple of the path.
FIBER_REACHED_MIN = 0.8
FIBER_MAX_TO_PATH = 2.5
#: Fibre QA: warn when more than this fraction of the fibres detour.
FIBER_DETOURED_MAX = 0.1
#: Fibre QA: warn when the belly touches less than this fraction of an attachment's area.
ATTACHMENT_CONTACT_MIN = 0.5
DEFAULT_SPECIFIC_TENSION_N_CM2 = 30.0
DEFAULT_DENSITY_G_CM3 = 1.0597

QA_OK, QA_INFO, QA_WARNING, QA_ERROR = "OK", "INFO", "WARNING", "ERROR"


# --------------------------------------------------------------------------
# Units
# --------------------------------------------------------------------------

def metres_per_unit(scene):
    """Length of one Blender unit in metres (``scene.unit_settings.scale_length``).

    :arg scene: Scene whose unit settings are read.
    :type scene: :class:`bpy.types.Scene`
    :return: Metres per Blender unit; 1.0 when the scale is missing or not positive.
    :rtype: float
    """
    try:
        scale = float(scene.unit_settings.scale_length)
    except AttributeError:
        scale = 1.0
    return scale if scale > 0.0 else 1.0


def force_from_pcsa(pcsa_m2, specific_tension_n_cm2):
    """Maximum isometric muscle force: ``F = PCSA x specific tension``.

    :arg pcsa_m2: Physiological cross-sectional area (m²).
    :type pcsa_m2: float
    :arg specific_tension_n_cm2: Specific tension (N/cm²), e.g. 30.
    :type specific_tension_n_cm2: float
    :return: Force (N).
    :rtype: float
    """
    return pcsa_m2 * specific_tension_n_cm2 * 1e4


def pcsa_from_volume(volume_m3, path_length_m,
                     fiber_length_ratio=DEFAULT_FIBER_LENGTH_RATIO,
                     pennation_deg=DEFAULT_PENNATION_DEG):
    """PCSA from muscle volume: ``PCSA = V cos(theta) / Lf`` with ``Lf = L_path x ratio``.

    With the defaults (ratio 1, 0°) this is the Herbst et al. (2022) estimate
    ``V / L``: fibre length equal to muscle length, parallel fibres, no tendon.

    :arg volume_m3: Muscle volume (m³).
    :type volume_m3: float
    :arg path_length_m: Length of the muscle path curve (m).
    :type path_length_m: float
    :arg fiber_length_ratio: Fibre length / muscle length (0.7-0.9 is reported
       for masticatory muscles).
    :type fiber_length_ratio: float
    :arg pennation_deg: Pennation angle (degrees).
    :type pennation_deg: float
    :return: ``(pcsa_m2, fiber_length_m)``; PCSA is 0.0 when the fibre length is not positive.
    :rtype: tuple of float
    """
    fiber_length_m = path_length_m * fiber_length_ratio
    if fiber_length_m <= 0.0:
        return 0.0, fiber_length_m
    pcsa = volume_m3 * math.cos(math.radians(pennation_deg)) / fiber_length_m
    return pcsa, fiber_length_m


def pcsa_from_fibres(volume_m3, lengths_m, shares, fiber_length_ratio=DEFAULT_FIBER_LENGTH_RATIO,
                     pennation_deg=DEFAULT_PENNATION_DEG, model="MEAN", weights=None):
    """PCSA from the lengths of many fibres of a belly.

    ``MEAN``: ``PCSA = V cos(theta) / Lf`` with ``Lf = mean(L_i) x ratio``
    (mean weighted by ``weights``). ``WEIGHTED``: ``PCSA = cos(theta) x
    sum_i(V_i / (L_i x ratio))`` with ``V_i = V x share_i``, each fibre's
    part of the volume; short fibres then count more, as they do in a muscle
    of mixed fibre lengths (a fan). The returned fibre length is the
    (weighted) ``mean(L_i) x ratio`` in both cases.

    :arg volume_m3: Muscle volume (m³).
    :type volume_m3: float
    :arg lengths_m: Fibre lengths (m), attachment to attachment.
    :type lengths_m: sequence of float
    :arg shares: Fraction of the volume of each fibre (sum 1); used by ``WEIGHTED``.
    :type shares: sequence of float
    :arg fiber_length_ratio: Fascicle / fibre-line length (tendon excluded).
    :type fiber_length_ratio: float
    :arg pennation_deg: Pennation angle (degrees).
    :type pennation_deg: float
    :arg model: One of :data:`PCSA_MODELS`.
    :type model: str
    :arg weights: Weight of each fibre in the mean length (default equal).
    :type weights: sequence of float
    :return: ``(pcsa_m2, fiber_length_m)``; PCSA is 0.0 without positive lengths.
    :rtype: tuple of float
    """
    lengths = [float(x) * fiber_length_ratio for x in lengths_m]
    weights = [1.0] * len(lengths) if weights is None else [float(w) for w in weights]
    if not lengths or sum(weights) <= 0.0:
        return 0.0, 0.0
    mean = sum(w * x for w, x in zip(weights, lengths)) / sum(weights)
    if min(lengths) <= 0.0:
        return 0.0, mean
    cos = math.cos(math.radians(pennation_deg))
    if model == "WEIGHTED":
        total = sum(shares) or 1.0
        return volume_m3 * cos * sum(v / total / x for v, x in zip(shares, lengths)), mean
    return volume_m3 * cos / mean, mean


def pcsa_method_label(fiber_length_ratio, pennation_deg, source="PATH", model="MEAN"):
    """Human-readable description of the PCSA assumptions, stored in ``myo_pcsa_method``.

    :arg fiber_length_ratio: Fibre length / muscle length used.
    :type fiber_length_ratio: float
    :arg pennation_deg: Pennation angle used (degrees).
    :type pennation_deg: float
    :arg source: One of :data:`FIBER_LENGTH_SOURCES`.
    :type source: str
    :arg model: One of :data:`PCSA_MODELS` (only with ``BELLY_FIBRES``).
    :type model: str
    :rtype: str
    """
    if source == "BELLY_FIBRES":
        if model == "WEIGHTED":
            return (f"PCSA = cos({pennation_deg:g} deg) * sum(V_i / (L_i*{fiber_length_ratio:g})); "
                    "L_i = belly fibres (Laplacian streamlines from both attachments, detours excluded), "
                    "V_i = their volume shares")
        return (f"PCSA = V*cos({pennation_deg:g} deg) / (mean(L_i)*{fiber_length_ratio:g}); "
                "L_i = belly fibres (Laplacian streamlines from both attachments, detours excluded)")
    return (f"PCSA = V*cos({pennation_deg:g} deg) / (L_path*{fiber_length_ratio:g}); "
            "L_path = evaluated path-curve length; tendon ignored")


# --------------------------------------------------------------------------
# Geometry (world space, Blender units)
# --------------------------------------------------------------------------

def curve_length(curve_obj, resolution=32):
    """Evaluated world-space length of all splines of a curve object.

    Bezier segments are sampled with ``interpolate_bezier`` instead of joining
    control points with straight lines, which under-estimates curved paths.

    :arg curve_obj: Path curve (anything else returns 0.0).
    :type curve_obj: :class:`bpy.types.Object`
    :arg resolution: Samples per Bezier segment.
    :type resolution: int
    :return: Length in Blender units.
    :rtype: float
    """
    if not curve_obj or curve_obj.type != 'CURVE':
        return 0.0
    mw = curve_obj.matrix_world
    total = 0.0
    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            bpts = list(spline.bezier_points)
            pairs = list(zip(bpts[:-1], bpts[1:]))
            if spline.use_cyclic_u and len(bpts) > 1:
                pairs.append((bpts[-1], bpts[0]))
            for a, b in pairs:
                pts = interpolate_bezier(mw @ a.co, mw @ a.handle_right,
                                         mw @ b.handle_left, mw @ b.co, resolution)
                total += sum((pts[i] - pts[i - 1]).length for i in range(1, len(pts)))
        else:
            pts = [mw @ Vector(p.co[:3]) for p in spline.points]
            total += sum((pts[i] - pts[i - 1]).length for i in range(1, len(pts)))
    return total


def mesh_stats(obj):
    """Volume, area, centroid and hole error of a mesh, in world space.

    ``hole_error`` is the relative volume change obtained by filling the holes
    of an open mesh (0.0 for a closed one), i.e. how much an imperfect belly
    mesh can bias its volume.

    :arg obj: Mesh object (anything else returns zeros).
    :type obj: :class:`bpy.types.Object`
    :return: ``(abs_volume, signed_volume, area, centroid, hole_error)`` in Blender
       units (BU³, BU², BU).
    :rtype: tuple
    """
    if not obj or obj.type != 'MESH':
        return 0.0, 0.0, 0.0, Vector(), 0.0
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    signed = bm.calc_volume(signed=True) if bm.faces else 0.0
    area = sum(f.calc_area() for f in bm.faces)
    centroid = (sum((v.co for v in bm.verts), Vector()) / len(bm.verts)) if bm.verts else Vector()
    hole_error = 0.0
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary and signed:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
        hole_error = abs(abs(bm.calc_volume(signed=True)) - abs(signed)) / abs(signed)
        if hole_error == 0.0:
            hole_error = 1e-9  # open but negligible: still worth an INFO line
    bm.free()
    return abs(signed), signed, area, centroid, hole_error


def mesh_defects(obj):
    """Self-intersections and non-manifold edges of a mesh (world space).

    A belly whose surface passes through itself (folds, overlapping lofts,
    boolean leftovers) or has edges shared by more than two faces does not
    enclose a well-defined volume: the usual signed-volume sum counts doubly
    covered regions twice or is simply wrong.

    :arg obj: Mesh object.
    :type obj: :class:`bpy.types.Object`
    :return: ``(intersecting_face_pairs, non_manifold_edges, boundary_edges)``;
       face pairs sharing a vertex are not counted as intersecting.
    :rtype: tuple of int
    """
    if not obj or obj.type != 'MESH':
        return 0, 0, 0
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bm.faces.ensure_lookup_table()
    pairs = set()
    for a, b in BVHTree.FromBMesh(bm).overlap(BVHTree.FromBMesh(bm)):
        if a == b or (b, a) in pairs:
            continue
        if {v.index for v in bm.faces[a].verts} & {v.index for v in bm.faces[b].verts}:
            continue
        pairs.add((a, b))
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    bm.free()
    return len(pairs), non_manifold, boundary


def enclosed_volume(obj, resolution=300, fill_holes=True):
    """Volume actually enclosed by a closed mesh, robust to self-overlap.

    The mesh is rebuilt as the boundary of its union with a temporary voxel
    Remesh modifier (``max dimension / resolution`` voxels; the object is left
    unchanged). Validated against analytic cases: within 0.2 % for a sphere,
    and it recovers the union of two overlapping spheres where the signed sum
    over-counts by 18 %. Small holes are filled first on a temporary copy
    (the voxel remesh needs a closed surface); use it only when
    :func:`mesh_stats` reports a small ``hole_error``.

    :arg obj: Mesh object (left unchanged).
    :type obj: :class:`bpy.types.Object`
    :arg resolution: Voxels along the longest dimension.
    :type resolution: int
    :arg fill_holes: Fill boundary loops before remeshing.
    :type fill_holes: bool
    :return: Volume in Blender units cubed.
    :rtype: float
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    if fill_holes:
        boundary = [e for e in bm.edges if e.is_boundary]
        if boundary:
            bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    mesh = bpy.data.meshes.new("myo_enclosed_volume")
    bm.to_mesh(mesh)
    bm.free()
    temp = bpy.data.objects.new("myo_enclosed_volume", mesh)
    bpy.context.scene.collection.objects.link(temp)
    try:
        mod = temp.modifiers.new("remesh", 'REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = max(obj.dimensions) / resolution
        evaluated = temp.evaluated_get(bpy.context.evaluated_depsgraph_get())
        result = evaluated.to_mesh()
        rbm = bmesh.new()
        rbm.from_mesh(result)
        volume = abs(rbm.calc_volume(signed=True))
        rbm.free()
        evaluated.to_mesh_clear()
    finally:
        bpy.data.objects.remove(temp, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    return volume


def winding_volume(triangles, samples=6000, seed=0, chunk=25):
    """Enclosed volume by the generalized winding number (Jacobson et al. 2013).

    Points are sampled uniformly in the bounding box; a point is inside when
    the surface winds around it at least once (|w| >= 0.5). Robust to holes,
    non-manifold edges and self-overlap, but statistical: use it as a fallback
    when :func:`enclosed_volume` fails. Pure numpy (no ``bpy``).

    :arg triangles: Triangle corner coordinates.
    :type triangles: array-like of shape (m, 3, 3)
    :arg samples: Number of random points.
    :type samples: int
    :arg seed: Random seed (results are reproducible).
    :type seed: int
    :arg chunk: Points processed at once (memory: ``chunk * m * 9`` floats).
    :type chunk: int
    :return: ``(volume, standard_error, doubly_covered_volume)`` in the units
       of ``triangles`` cubed.
    :rtype: tuple of float
    """
    import numpy as np
    T = np.asarray(triangles, dtype=float)
    lo, hi = T.reshape(-1, 3).min(axis=0), T.reshape(-1, 3).max(axis=0)
    box = float(np.prod(hi - lo))
    points = lo + np.random.default_rng(seed).random((samples, 3)) * (hi - lo)
    w = np.empty(samples)
    for s in range(0, samples, chunk):
        P = points[s:s + chunk][:, None, :]
        a, b, c = T[None, :, 0] - P, T[None, :, 1] - P, T[None, :, 2] - P
        la, lb, lc = (np.linalg.norm(x, axis=2) for x in (a, b, c))
        det = np.einsum('ijk,ijk->ij', a, np.cross(b, c))
        den = (la * lb * lc + np.einsum('ijk,ijk->ij', a, b) * lc + np.einsum('ijk,ijk->ij', b, c) * la
               + np.einsum('ijk,ijk->ij', c, a) * lb)
        w[s:s + chunk] = np.abs(np.arctan2(det, den).sum(axis=1) / (2 * math.pi))
    inside = (w >= 0.5).mean()
    return box * inside, box * math.sqrt(inside * (1 - inside) / samples), box * (w >= 1.5).mean()


def mesh_triangles(obj):
    """World-space triangle corners of a mesh (for :func:`winding_volume`).

    :arg obj: Mesh object.
    :type obj: :class:`bpy.types.Object`
    :rtype: list of 3 tuples of 3 floats
    """
    obj.data.calc_loop_triangles()
    mw = obj.matrix_world
    co = [mw @ v.co for v in obj.data.vertices]
    return [[tuple(co[i]) for i in t.vertices] for t in obj.data.loop_triangles]


def robust_volume(obj, raw_volume, tolerance=0.02):
    """Volume of a defective belly (self-overlap, non-manifold edges, holes).

    Tries :func:`enclosed_volume` at two resolutions; it is accepted if both
    agree within 3 % and the result has not collapsed (more than a quarter of
    ``raw_volume``). Otherwise falls back to :func:`winding_volume`.

    :arg obj: Mesh object.
    :type obj: :class:`bpy.types.Object`
    :arg raw_volume: Signed-sum volume of the same mesh (Blender units cubed).
    :type raw_volume: float
    :arg tolerance: Relative difference below which ``raw_volume`` is kept.
    :type tolerance: float
    :return: ``(volume, method, uncertainty)``; ``method`` is ``"mesh"`` when the
       raw volume is confirmed, ``"voxel union"`` or ``"winding number"``;
       ``uncertainty`` is the relative standard error (0 for exact methods).
    :rtype: tuple
    """
    fine, coarse = enclosed_volume(obj, 300), enclosed_volume(obj, 200)
    if fine > 0.25 * raw_volume and coarse > 0 and abs(fine / coarse - 1.0) < 0.03:
        volume, method, error = fine, "voxel union", 0.0
    else:
        volume, se, _double = winding_volume(mesh_triangles(obj))
        method, error = "winding number", se / volume if volume else 1.0
    if volume <= 0.0 or abs(raw_volume / volume - 1.0) <= max(tolerance, 2 * error):
        return raw_volume, "mesh", 0.0
    return volume, method, error


def max_dimension(obj):
    """Longest bounding-box dimension of an object.

    :arg obj: Object, or None.
    :type obj: :class:`bpy.types.Object`
    :return: Length in Blender units (0.0 for None).
    :rtype: float
    """
    return max(obj.dimensions) if obj is not None else 0.0


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------

def get_root(create=False, scene=None):
    """The MyoGen root collection (``'muscles'``), tagged with ``myo_root`` on first use.

    :arg create: Create (and link to ``scene``) the collection if missing, and tag it.
    :type create: bool
    :arg scene: Scene to link a new root to (default: the context scene).
    :type scene: :class:`bpy.types.Scene`
    :return: The root collection, or None if it does not exist and ``create`` is False.
    :rtype: :class:`bpy.types.Collection` or None
    """
    for coll in bpy.data.collections:
        if coll.get(ROOT_TAG):
            return coll
    coll = bpy.data.collections.get(ROOT_COLLECTION)
    if coll is None and create:
        coll = bpy.data.collections.new(ROOT_COLLECTION)
        (scene or bpy.context.scene).collection.children.link(coll)
    if coll is not None and create:
        coll[ROOT_TAG] = True
    return coll


_SIDE_SUFFIXES = (("_left", "L"), ("_right", "R"), ("_l", "L"), ("_r", "R"),
                  (".l", "L"), (".r", "R"), ("_mid", "M"))


def parse_side(name):
    """Side of a muscle from its name suffix.

    :arg name: Muscle name such as ``'temp_sup_left'``.
    :type name: str
    :return: ``'L'``, ``'R'``, ``'M'`` or ``''`` (no suffix).
    :rtype: str
    """
    low = name.lower()
    for token, side in _SIDE_SUFFIXES:
        if low.endswith(token):
            return side
    return ""


def strip_side(name):
    """Muscle name without its side suffix (``'temp_sup_left'`` -> ``'temp_sup'``).

    :arg name: Muscle name.
    :type name: str
    :rtype: str
    """
    low = name.lower()
    for token, _side in _SIDE_SUFFIXES:
        if low.endswith(token):
            return name[: -len(token)]
    return name


def resolve_objects(coll):
    """Objects of a muscle collection, by role.

    Uses the ``myo_role`` tags; falls back to MyoGen's naming convention
    (``<M>_origin``, ``<M>_muscle``, ...) so scenes made before the schema
    existed are still understood.

    :arg coll: A muscle collection (child of the root).
    :type coll: :class:`bpy.types.Collection`
    :return: Role (see :data:`ROLES`) -> object; roles without an object are absent.
    :rtype: dict
    """
    found = {}
    for obj in coll.objects:
        role = obj.get(ROLE_KEY)
        if role in ROLES and role not in found:
            found[role] = obj
    name = coll.name
    for role, suffix in ROLES.items():
        if role not in found:
            obj = coll.objects.get(name + suffix)
            if obj is not None:
                found[role] = obj
    return found


def is_muscle_collection(coll):
    """Whether a collection is a MyoGen muscle (has a record, or legacy-named objects).

    :arg coll: Collection to test.
    :type coll: :class:`bpy.types.Collection`
    :rtype: bool
    """
    if coll.get("myo_schema"):
        return True
    objs = resolve_objects(coll)
    return "origin" in objs or "insertion" in objs or "belly" in objs


def iter_muscle_collections():
    """All MyoGen muscle collections of the file.

    :return: Muscle collections (children of the root); empty if there is no root.
    :rtype: list of :class:`bpy.types.Collection`
    """
    root = get_root()
    if root is None:
        return []
    return [c for c in root.children if is_muscle_collection(c)]


def tag_roles(coll):
    """Write ``myo_role`` on every object :func:`resolve_objects` recognises.

    :arg coll: A muscle collection.
    :type coll: :class:`bpy.types.Collection`
    """
    for role, obj in resolve_objects(coll).items():
        obj[ROLE_KEY] = role


# --------------------------------------------------------------------------
# Record read / write
# --------------------------------------------------------------------------

def write_record(coll, values):
    """Store a muscle record on its collection (also sets ``myo_schema``).

    :arg coll: The muscle collection.
    :type coll: :class:`bpy.types.Collection`
    :arg values: Record keys (see :data:`RECORD_KEYS`) -> values; ``myo_qa`` may be
       a list of ``(level, message)``, it is stored as JSON.
    :type values: dict
    :raises KeyError: If a key is not in :data:`RECORD_KEYS`.
    """
    unknown = set(values) - set(RECORD_KEYS)
    if unknown:
        raise KeyError(f"Unknown muscle-record keys: {sorted(unknown)}")
    coll["myo_schema"] = SCHEMA_VERSION
    for key, value in values.items():
        if key == "myo_qa" and not isinstance(value, str):
            value = json.dumps(value)
        coll[key] = value


def read_record(coll):
    """Read a muscle record.

    :arg coll: The muscle collection.
    :type coll: :class:`bpy.types.Collection`
    :return: Every key of :data:`RECORD_KEYS` (None when missing) plus
       ``objects`` (role -> object; stored names first, then tags/names),
       ``collection`` (collection name), ``qa`` (list of ``[level, message]``)
       and ``has_pcsa`` (True when a positive PCSA is stored). ``myo_name`` and
       ``myo_side`` fall back to the collection name.
    :rtype: dict
    """
    rec = {key: coll.get(key) for key in RECORD_KEYS}
    objs = resolve_objects(coll)
    for key, role in OBJECT_KEYS.items():
        stored = rec.get(key)
        obj = bpy.data.objects.get(stored) if stored else None
        if obj is not None:
            objs[role] = obj
    rec["objects"] = objs
    rec["collection"] = coll.name
    rec["myo_name"] = rec.get("myo_name") or coll.name
    rec["myo_side"] = rec.get("myo_side") if rec.get("myo_side") is not None else parse_side(coll.name)
    try:
        rec["qa"] = json.loads(rec.get("myo_qa") or "[]")
    except (TypeError, ValueError):
        rec["qa"] = []
    pcsa = rec.get("myo_pcsa_m2")
    rec["has_pcsa"] = isinstance(pcsa, (int, float)) and pcsa > 0.0
    return rec


# --------------------------------------------------------------------------
# Plausibility checks (dimensionless, so they hold from a shrew to a T. rex)
# --------------------------------------------------------------------------

REF_LENGTH_RANGE_M = (0.003, 6.0)        # skull / jaw longest dimension
FIBER_TO_REF = (0.03, 1.2)
CBRT_VOLUME_TO_REF = (0.01, 0.6)
PATH_TO_LINEAR = (0.9, 1.8)          # tolerant: path ends are often edited by hand
BILATERAL_VOLUME_RATIO = 1.5
HOLE_VOLUME_TOLERANCE = 0.02            # relative volume change
OVERLAP_VOLUME_TOLERANCE = 0.02         # raw vs enclosed volume
DENSITY_RANGE = (1.0, 1.1)               # g/cm3
SPECIFIC_TENSION_RANGE = (10.0, 60.0)    # N/cm2
FIBER_RATIO_RANGE = (0.3, 1.0)


def _fmt_len(m):
    if m >= 1.0:
        return f"{m:.2f} m"
    if m >= 0.01:
        return f"{m * 100:.1f} cm"
    return f"{m * 1000:.2f} mm"


def check_scene_scale(scene, ref_length_bu, what="Reference bone"):
    """Check that a reference length is a plausible vertebrate skull size.

    :arg scene: Scene (for the unit scale).
    :type scene: :class:`bpy.types.Scene`
    :arg ref_length_bu: Reference length in Blender units (e.g. the longest
       dimension of the cranium).
    :type ref_length_bu: float
    :arg what: Name of the measured thing, used in the messages.
    :type what: str
    :return: ``(ref_length_m or None, findings)``; findings are ``(level, message)``
       with a hint about the Unit Scale that would make the size plausible.
    :rtype: tuple
    """
    if not ref_length_bu or ref_length_bu <= 0.0:
        return None, [(QA_INFO, "No reference bone found: scale not checked")]
    mpu = metres_per_unit(scene)
    ref_bu = ref_length_bu
    ref_m = ref_bu * mpu
    lo, hi = REF_LENGTH_RANGE_M
    findings = []
    if not (lo <= ref_m <= hi):
        hint = ""
        for unit, scale in (("millimetres", 0.001), ("centimetres", 0.01), ("metres", 1.0)):
            if lo <= ref_bu * scale <= hi and abs(scale - mpu) > 1e-9:
                hint = (f" If the model was built in {unit}, set Scene > Units > Unit Scale "
                        f"to {scale:g} (1 BU = 1 {unit[:-1]}).")
                break
        findings.append((QA_ERROR,
                         f"{what} is {_fmt_len(ref_m)} long with Unit Scale {mpu:g}: "
                         f"implausible for a vertebrate skull ({_fmt_len(lo)}-{_fmt_len(hi)}).{hint}"))
    else:
        findings.append((QA_OK, f"{what}: {_fmt_len(ref_m)} (Unit Scale {mpu:g})"))
    return ref_m, findings


def check_parameters(density_g_cm3, specific_tension_n_cm2, fiber_length_ratio):
    """Check the physiological parameters against literature ranges.

    :arg density_g_cm3: Muscle density (g/cm³).
    :type density_g_cm3: float
    :arg specific_tension_n_cm2: Specific tension (N/cm²).
    :type specific_tension_n_cm2: float
    :arg fiber_length_ratio: Fibre / muscle length ratio.
    :type fiber_length_ratio: float
    :return: Findings ``(level, message)``; empty when everything is in range.
    :rtype: list of tuple
    """
    findings = []
    if not (DENSITY_RANGE[0] <= density_g_cm3 <= DENSITY_RANGE[1]):
        findings.append((QA_WARNING, f"Muscle density {density_g_cm3:g} g/cm3 is outside "
                                     f"{DENSITY_RANGE[0]}-{DENSITY_RANGE[1]} (typically 1.0564-1.06)"))
    if not (SPECIFIC_TENSION_RANGE[0] <= specific_tension_n_cm2 <= SPECIFIC_TENSION_RANGE[1]):
        findings.append((QA_WARNING, f"Specific tension {specific_tension_n_cm2:g} N/cm2 is outside "
                                     f"{SPECIFIC_TENSION_RANGE[0]:g}-{SPECIFIC_TENSION_RANGE[1]:g} "
                                     "(25-37 N/cm2 are the usual values)"))
    if not (FIBER_RATIO_RANGE[0] <= fiber_length_ratio <= FIBER_RATIO_RANGE[1]):
        findings.append((QA_WARNING, f"Fibre/muscle length ratio {fiber_length_ratio:g} is outside "
                                     f"{FIBER_RATIO_RANGE[0]}-{FIBER_RATIO_RANGE[1]} (0.7-0.9 reported "
                                     "for masticatory muscles)"))
    return findings


def check_muscle(values, ref_length_m, belly_hole_error=0.0, belly_signed_volume=1.0):
    """Plausibility findings for one muscle.

    All size checks are ratios (to ``ref_length_m`` or between lengths), so the
    same thresholds hold for any body size.

    :arg values: Record values of the muscle (SI, keys from :data:`RECORD_KEYS`).
    :type values: dict
    :arg ref_length_m: Reference (skull) length in metres, or None to skip size checks.
    :type ref_length_m: float or None
    :arg belly_hole_error: ``hole_error`` from :func:`mesh_stats`.
    :type belly_hole_error: float
    :arg belly_signed_volume: Signed volume from :func:`mesh_stats` (negative =
       inverted normals).
    :type belly_signed_volume: float
    :return: Findings ``(level, message)``.
    :rtype: list of tuple
    """
    findings = []
    vol = values.get("myo_volume_m3") or 0.0
    path = values.get("myo_path_length_m") or 0.0
    linear = values.get("myo_linear_length_m") or 0.0
    fiber = values.get("myo_fiber_length_m") or 0.0
    if vol <= 0.0:
        findings.append((QA_ERROR, "Volume is zero: the belly mesh is missing or empty"))
    elif belly_hole_error > HOLE_VOLUME_TOLERANCE:
        findings.append((QA_WARNING, f"Belly mesh has holes: closing them changes the volume by "
                                     f"{belly_hole_error * 100:.1f}%"))
    elif belly_hole_error > 0.0:
        findings.append((QA_INFO, f"Belly mesh has small holes (volume effect "
                                  f"{belly_hole_error * 100:.2f}%)"))
    if belly_signed_volume < 0.0:
        findings.append((QA_INFO, "Belly normals point inwards (volume taken as absolute value)"))
    if path <= 0.0:
        findings.append((QA_ERROR, "Path curve is missing or has zero length: no PCSA"))
    elif linear > 0.0:
        ratio = path / linear
        if ratio < PATH_TO_LINEAR[0]:
            findings.append((QA_WARNING, f"Path ({_fmt_len(path)}) is shorter than the straight "
                                         f"origin-insertion distance ({_fmt_len(linear)})"))
        elif ratio > PATH_TO_LINEAR[1]:
            findings.append((QA_WARNING, f"Path is {ratio:.2f}x the straight origin-insertion distance: "
                                         "check the curve handles"))
    if ref_length_m:
        if fiber > 0.0 and not (FIBER_TO_REF[0] <= fiber / ref_length_m <= FIBER_TO_REF[1]):
            findings.append((QA_WARNING, f"Fibre length is {fiber / ref_length_m:.2f}x the skull length "
                                         f"(expected {FIBER_TO_REF[0]}-{FIBER_TO_REF[1]})"))
        if vol > 0.0:
            rel = vol ** (1.0 / 3.0) / ref_length_m
            if not (CBRT_VOLUME_TO_REF[0] <= rel <= CBRT_VOLUME_TO_REF[1]):
                findings.append((QA_WARNING, f"Muscle size (cube root of volume) is {rel:.3f}x the skull "
                                             f"length (expected {CBRT_VOLUME_TO_REF[0]}-{CBRT_VOLUME_TO_REF[1]})"))
    return findings


def check_bilateral(volumes_by_name):
    """Compare the volumes of left/right counterparts.

    :arg volumes_by_name: Collection name -> volume (m³).
    :type volumes_by_name: dict
    :return: Collection name -> findings, only for pairs that differ more than
       :data:`BILATERAL_VOLUME_RATIO`.
    :rtype: dict
    """
    out = {}
    pairs = {}
    for name, vol in volumes_by_name.items():
        side = parse_side(name)
        if side in ("L", "R"):
            pairs.setdefault(strip_side(name), {})[side] = (name, vol)
    for base, sides in pairs.items():
        if "L" in sides and "R" in sides:
            (ln, lv), (rn, rv) = sides["L"], sides["R"]
            if lv > 0.0 and rv > 0.0 and max(lv, rv) / min(lv, rv) > BILATERAL_VOLUME_RATIO:
                msg = (QA_WARNING, f"Left/right volumes of '{base}' differ {max(lv, rv) / min(lv, rv):.2f}x")
                out.setdefault(ln, []).append(msg)
                out.setdefault(rn, []).append(msg)
    return out


def worst_level(findings):
    """Most severe level among findings.

    :arg findings: ``(level, message)`` pairs.
    :type findings: list of tuple
    :return: One of ``QA_OK``, ``QA_INFO``, ``QA_WARNING``, ``QA_ERROR``.
    :rtype: str
    """
    order = {QA_OK: 0, QA_INFO: 1, QA_WARNING: 2, QA_ERROR: 3}
    level = QA_OK
    for lvl, _msg in findings:
        if order.get(lvl, 0) > order[level]:
            level = lvl
    return level


LEVEL_ICONS = {QA_OK: 'CHECKMARK', QA_INFO: 'INFO', QA_WARNING: 'ERROR', QA_ERROR: 'CANCEL'}
