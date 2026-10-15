# `myo_record`

Source: `myo_record.py`

Muscle record: the data contract shared by MyoGeneratorRemix and MUFIS.

This file is OWNED by MyoGeneratorRemix and copied verbatim into MUFIS
(MUFIS/tools/sync_shared.py). Do not edit the MUFIS copy: edit this one, then
run the sync script. Both copies must stay byte-identical.

MyoGeneratorRemix *writes* records; any other tool may *read* them. Nothing in
here imports either add-on, so a .blend reconstructed with MyoGen can be read by
MUFIS on a machine where MyoGen is not installed.

Layout (schema 1)
-----------------
Collection `muscles/<M>` carries the record as custom properties (`myo_*`,
see `RECORD_KEYS`). Objects inside it carry `myo_role` (`ROLES`).
Values are SI. Object references are stored as object names, because ID
properties cannot hold pointers; they are resolved and validated on read.

Scenes made before the schema existed are recognised from MyoGen's naming
convention (`<M>_origin`, `<M>_muscle`, ...) by `resolve_objects`.

## Constants

| Name | Value |
|---|---|
| `SCHEMA_VERSION` | `1` |
| `ROOT_COLLECTION` | `'muscles'` |
| `ROLE_KEY` | `'myo_role'` |
| `ROOT_TAG` | `'myo_root'` |
| `ROLES` | `{'origin': '_origin', 'insertion': '_insertion', 'origin_contour': '_origin_contour', '...` |
| `OBJECT_KEYS` | `{'myo_origin_obj': 'origin', 'myo_insertion_obj': 'insertion', 'myo_path_obj': 'path', ...` |
| `RECORD_KEYS` | `('myo_schema', 'myo_name', 'myo_side', 'myo_origin_obj', 'myo_insertion_obj', 'myo_path...` |
| `DEFAULT_FIBER_LENGTH_RATIO` | `1.0` |
| `DEFAULT_PENNATION_DEG` | `0.0` |
| `FIBER_LENGTH_SOURCES` | `('PATH', 'BELLY_FIBRES')` |
| `PCSA_MODELS` | `('MEAN', 'WEIGHTED')` |
| `FIBER_REACHED_MIN` | `0.8` |
| `FIBER_MAX_TO_PATH` | `2.5` |
| `FIBER_DETOURED_MAX` | `0.1` |
| `ATTACHMENT_CONTACT_MIN` | `0.5` |
| `DEFAULT_SPECIFIC_TENSION_N_CM2` | `30.0` |
| `DEFAULT_DENSITY_G_CM3` | `1.0597` |
| `_SIDE_SUFFIXES` | `(('_left', 'L'), ('_right', 'R'), ('_l', 'L'), ('_r', 'R'), ('.l', 'L'), ('.r', 'R'), (...` |
| `FIBRE_POINTS_KEY` | `'myo_fibre_points'` |
| `FIBRE_SEEDING_KEY` | `'myo_fibre_seeding'` |
| `FIBRE_LIST_KEYS` | `('myo_fibre_length_m', 'myo_fibre_weight', 'myo_fibre_share', 'myo_fibre_pcsa_area_m2',...` |
| `REF_LENGTH_RANGE_M` | `(0.003, 6.0)` |
| `FIBER_TO_REF` | `(0.03, 1.2)` |
| `CBRT_VOLUME_TO_REF` | `(0.01, 0.6)` |
| `PATH_TO_LINEAR` | `(0.9, 1.8)` |
| `PATH_END_TO_PATH` | `0.1` |
| `BILATERAL_VOLUME_RATIO` | `1.5` |
| `HOLE_VOLUME_TOLERANCE` | `0.02` |
| `OVERLAP_VOLUME_TOLERANCE` | `0.02` |
| `MUSCLE_OVERLAP_WARNING` | `0.02` |
| `MUSCLE_OVERLAP_INFO` | `0.002` |
| `DENSITY_RANGE` | `(1.0, 1.1)` |
| `SPECIFIC_TENSION_RANGE` | `(10.0, 60.0)` |
| `FIBER_RATIO_RANGE` | `(0.3, 1.0)` |
| `LEVEL_ICONS` | `{QA_OK: 'CHECKMARK', QA_INFO: 'INFO', QA_WARNING: 'ERROR', QA_ERROR: 'CANCEL'}` |

## Functions

### `metres_per_unit(scene)`

Length of one Blender unit in metres (`scene.unit_settings.scale_length`).

| Parameter | Type | Description |
|---|---|---|
| `scene` | `bpy.types.Scene` | Scene whose unit settings are read. |

**Returns** (float): Metres per Blender unit; 1.0 when the scale is missing or not positive.

### `force_from_pcsa(pcsa_m2, specific_tension_n_cm2)`

Maximum isometric muscle force: `F = PCSA x specific tension`.

| Parameter | Type | Description |
|---|---|---|
| `pcsa_m2` | float | Physiological cross-sectional area (m²). |
| `specific_tension_n_cm2` | float | Specific tension (N/cm²), e.g. 30. |

**Returns** (float): Force (N).

### `pcsa_from_volume(volume_m3, path_length_m, fiber_length_ratio=DEFAULT_FIBER_LENGTH_RATIO, pennation_deg=DEFAULT_PENNATION_DEG)`

PCSA from muscle volume: `PCSA = V cos(theta) / Lf` with `Lf = L_path x ratio`.

With the defaults (ratio 1, 0°) this is the Herbst et al. (2022) estimate
`V / L`: fibre length equal to muscle length, parallel fibres, no tendon.

| Parameter | Type | Description |
|---|---|---|
| `volume_m3` | float | Muscle volume (m³). |
| `path_length_m` | float | Length of the muscle path curve (m). |
| `fiber_length_ratio` | float | Fibre length / muscle length (0.7-0.9 is reported for masticatory muscles). |
| `pennation_deg` | float | Pennation angle (degrees). |

**Returns** (tuple of float): `(pcsa_m2, fiber_length_m)`; PCSA is 0.0 when the fibre length is not positive.

### `pcsa_from_fibres(volume_m3, lengths_m, shares, fiber_length_ratio=DEFAULT_FIBER_LENGTH_RATIO, pennation_deg=DEFAULT_PENNATION_DEG, model='MEAN', weights=None)`

PCSA from the lengths of many fibres of a belly.

`MEAN`: `PCSA = V cos(theta) / Lf` with `Lf = mean(L_i) x ratio`
(mean weighted by `weights`). `WEIGHTED`: `PCSA = cos(theta) x
sum_i(V_i / (L_i x ratio))` with `V_i = V x share_i`, each fibre's
part of the volume; short fibres then count more, as they do in a muscle
of mixed fibre lengths (a fan). The returned fibre length is the
(weighted) `mean(L_i) x ratio` in both cases.

| Parameter | Type | Description |
|---|---|---|
| `volume_m3` | float | Muscle volume (m³). |
| `lengths_m` | sequence of float | Fibre lengths (m), attachment to attachment. |
| `shares` | sequence of float | Fraction of the volume of each fibre (sum 1); used by `WEIGHTED`. |
| `fiber_length_ratio` | float | Fascicle / fibre-line length (tendon excluded). |
| `pennation_deg` | float | Pennation angle (degrees). |
| `model` | str | One of `PCSA_MODELS`. |
| `weights` | sequence of float | Weight of each fibre in the mean length (default equal). |

**Returns** (tuple of float): `(pcsa_m2, fiber_length_m)`; PCSA is 0.0 without positive lengths.

### `fibre_pcsa(volume_m3, lengths_m, weights, shares, fiber_length_ratio=DEFAULT_FIBER_LENGTH_RATIO, pennation_deg=DEFAULT_PENNATION_DEG)`

PCSA of every fibre of a belly, by the two sharing rules.

* **By area** (option A): the muscle's PCSA from the mean fibre length
  (`pcsa_from_fibres`, `MEAN`) shared in proportion to `weights`
  (each fibre's part of the attachment area it was seeded on).
* **By volume** (option B): `V_i cos(theta) / (L_i x ratio)` with
  `V_i = V x share_i`, the fibre's own part of the volume over its own
  length (Woodley & Mercer 2005); the sum is the `WEIGHTED` PCSA.

| Parameter | Type | Description |
|---|---|---|
| `volume_m3` | float | Muscle volume (m³). |
| `lengths_m` | sequence of float | Fibre lengths at rest (m), attachment to attachment. |
| `weights` | sequence of float | Area weight of each fibre (any positive scale). |
| `shares` | sequence of float | Volume share of each fibre (any positive scale). |
| `fiber_length_ratio` | float | Fascicle / fibre-line length. |
| `pennation_deg` | float | Pennation angle (degrees). |

**Returns** (tuple of list): `(by_area_m2, by_volume_m2)`, one value per fibre each.

### `pcsa_method_label(fiber_length_ratio, pennation_deg, source='PATH', model='MEAN')`

Human-readable description of the PCSA assumptions, stored in `myo_pcsa_method`.

| Parameter | Type | Description |
|---|---|---|
| `fiber_length_ratio` | float | Fibre length / muscle length used. |
| `pennation_deg` | float | Pennation angle used (degrees). |
| `source` | str | One of `FIBER_LENGTH_SOURCES`. |
| `model` | str | One of `PCSA_MODELS` (only with `BELLY_FIBRES`). |

**Returns** (str): 

### `curve_length(curve_obj, resolution=32)`

Evaluated world-space length of all splines of a curve object.

Bezier segments are sampled with `interpolate_bezier` instead of joining
control points with straight lines, which under-estimates curved paths.

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Path curve (anything else returns 0.0). |
| `resolution` | int | Samples per Bezier segment. |

**Returns** (float): Length in Blender units.

### `curve_ends(curve_obj)`

World positions of the first and last points of a curve's first spline.

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Curve object (Bezier or poly/NURBS spline). |

**Returns** (tuple of `mathutils.Vector` or None): `(start, end)` or None if the curve has no points.

### `mesh_stats(obj)`

Volume, area, centroid and hole error of a mesh, in world space.

`hole_error` is the relative volume change obtained by filling the holes
of an open mesh (0.0 for a closed one), i.e. how much an imperfect belly
mesh can bias its volume.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Mesh object (anything else returns zeros). |

**Returns** (tuple): `(abs_volume, signed_volume, area, centroid, hole_error)` in Blender units (BU³, BU², BU).

### `mesh_defects(obj)`

Self-intersections and non-manifold edges of a mesh (world space).

A belly whose surface passes through itself (folds, overlapping lofts,
boolean leftovers) or has edges shared by more than two faces does not
enclose a well-defined volume: the usual signed-volume sum counts doubly
covered regions twice or is simply wrong.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Mesh object. |

**Returns** (tuple of int): `(intersecting_face_pairs, non_manifold_edges, boundary_edges)`; face pairs sharing a vertex are not counted as intersecting.

### `enclosed_volume(obj, resolution=300, fill_holes=True)`

Volume actually enclosed by a closed mesh, robust to self-overlap.

The mesh is rebuilt as the boundary of its union with a temporary voxel
Remesh modifier (`max dimension / resolution` voxels; the object is left
unchanged). Validated against analytic cases: within 0.2 % for a sphere,
and it recovers the union of two overlapping spheres where the signed sum
over-counts by 18 %. Small holes are filled first on a temporary copy
(the voxel remesh needs a closed surface); use it only when
`mesh_stats` reports a small `hole_error`.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Mesh object (left unchanged). |
| `resolution` | int | Voxels along the longest dimension. |
| `fill_holes` | bool | Fill boundary loops before remeshing. |

**Returns** (float): Volume in Blender units cubed.

### `winding_volume(triangles, samples=6000, seed=0, chunk=25)`

Enclosed volume by the generalized winding number (Jacobson et al. 2013).

Points are sampled uniformly in the bounding box; a point is inside when
the surface winds around it at least once (|w| >= 0.5). Robust to holes,
non-manifold edges and self-overlap, but statistical: use it as a fallback
when `enclosed_volume` fails. Pure numpy (no `bpy`).

| Parameter | Type | Description |
|---|---|---|
| `triangles` | array-like of shape (m, 3, 3) | Triangle corner coordinates. |
| `samples` | int | Number of random points. |
| `seed` | int | Random seed (results are reproducible). |
| `chunk` | int | Points processed at once (memory: `chunk * m * 9` floats). |

**Returns** (tuple of float): `(volume, standard_error, doubly_covered_volume)` in the units of `triangles` cubed.

### `mesh_triangles(obj)`

World-space triangle corners of a mesh (for `winding_volume`).

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Mesh object. |

**Returns** (list of 3 tuples of 3 floats): 

### `robust_volume(obj, raw_volume, tolerance=0.02)`

Volume of a defective belly (self-overlap, non-manifold edges, holes).

Tries `enclosed_volume` at two resolutions; it is accepted if both
agree within 3 % and the result has not collapsed (more than a quarter of
`raw_volume`). Otherwise falls back to `winding_volume`.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Mesh object. |
| `raw_volume` | float | Signed-sum volume of the same mesh (Blender units cubed). |
| `tolerance` | float | Relative difference below which `raw_volume` is kept. |

**Returns** (tuple): `(volume, method, uncertainty)`; `method` is `"mesh"` when the raw volume is confirmed, `"voxel union"` or `"winding number"`; `uncertainty` is the relative standard error (0 for exact methods).

### `max_dimension(obj)`

Longest bounding-box dimension of an object.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Object, or None. |

**Returns** (float): Length in Blender units (0.0 for None).

### `get_root(create=False, scene=None)`

The MyoGen root collection (`'muscles'`), tagged with `myo_root` on first use.

| Parameter | Type | Description |
|---|---|---|
| `create` | bool | Create (and link to `scene`) the collection if missing, and tag it. |
| `scene` | `bpy.types.Scene` | Scene to link a new root to (default: the context scene). |

**Returns** (`bpy.types.Collection` or None): The root collection, or None if it does not exist and `create` is False.

### `parse_side(name)`

Side of a muscle from its name suffix.

| Parameter | Type | Description |
|---|---|---|
| `name` | str | Muscle name such as `'temp_sup_left'`. |

**Returns** (str): `'L'`, `'R'`, `'M'` or `''` (no suffix).

### `strip_side(name)`

Muscle name without its side suffix (`'temp_sup_left'` -> `'temp_sup'`).

| Parameter | Type | Description |
|---|---|---|
| `name` | str | Muscle name. |

**Returns** (str): 

### `resolve_objects(coll)`

Objects of a muscle collection, by role.

Uses the `myo_role` tags; falls back to MyoGen's naming convention
(`<M>_origin`, `<M>_muscle`, ...) so scenes made before the schema
existed are still understood.

| Parameter | Type | Description |
|---|---|---|
| `coll` | `bpy.types.Collection` | A muscle collection (child of the root). |

**Returns** (dict): Role (see `ROLES`) -> object; roles without an object are absent.

### `is_muscle_collection(coll)`

Whether a collection is a MyoGen muscle (has a record, or legacy-named objects).

| Parameter | Type | Description |
|---|---|---|
| `coll` | `bpy.types.Collection` | Collection to test. |

**Returns** (bool): 

### `iter_muscle_collections()`

All MyoGen muscle collections of the file.

**Returns** (list of `bpy.types.Collection`): Muscle collections (children of the root); empty if there is no root.

### `iter_all_myo_collections()`

All MyoGen collections in the file (in root and elsewhere).

**Returns** (list of `bpy.types.Collection`): Muscle collections in root, followed by any other MyoGen collections.

### `tag_roles(coll)`

Write `myo_role` on every object `resolve_objects` recognises.

| Parameter | Type | Description |
|---|---|---|
| `coll` | `bpy.types.Collection` | A muscle collection. |

### `write_record(coll, values)`

Store a muscle record on its collection (also sets `myo_schema`).

| Parameter | Type | Description |
|---|---|---|
| `coll` | `bpy.types.Collection` | The muscle collection. |
| `values` | dict | Record keys (see `RECORD_KEYS`) -> values; `myo_qa` may be a list of `(level, message)`, it is stored as JSON. |

**Raises** `KeyError`: If a key is not in `RECORD_KEYS`.

### `read_record(coll)`

Read a muscle record.

| Parameter | Type | Description |
|---|---|---|
| `coll` | `bpy.types.Collection` | The muscle collection. |

**Returns** (dict): Every key of `RECORD_KEYS` (None when missing) plus `objects` (role -> object; stored names first, then tags/names), `collection` (collection name), `qa` (list of `[level, message]`) and `has_pcsa` (True when a positive PCSA is stored). `myo_name` and `myo_side` fall back to the collection name.

### `write_fibres(coll, name, polylines, values, seeding='')`

Create or replace the fibres object of a muscle.

A mesh of `N` polylines with `K` points each, vertex `f * K + k` being
point `k` (0 = origin, `K - 1` = insertion) of fibre `f`, consecutive
points joined by edges; world-space coordinates (Blender units), identity
matrix. Per-fibre values are custom properties (`FIBRE_LIST_KEYS`).
The object gets `myo_role = "fibres"` and is hidden in the viewport.

| Parameter | Type | Description |
|---|---|---|
| `coll` | `bpy.types.Collection` | The muscle collection. |
| `name` | str | Object name (`<M>_fibres`). |
| `polylines` | sequence of sequences of 3 floats | `N` polylines of `K` world-space points each. |
| `values` | dict | Key of `FIBRE_LIST_KEYS` -> list of `N` values. |
| `seeding` | str | How the fibres were seeded (stored as `FIBRE_SEEDING_KEY`). |

**Returns** (`bpy.types.Object`): The fibres object.

**Raises** `ValueError`: If the polylines differ in length or a list has the wrong size.

### `read_fibres(obj)`

Polylines and per-fibre values of a fibres object (`write_fibres`).

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Fibres object. |

**Returns** (tuple): `(polylines, values)`: list of `N` lists of `K` world-space `mathutils.Vector` (Blender units), and key -> list of `N` floats for the keys present.

**Raises** `ValueError`: If the object is not a fibres mesh.

### `check_scene_scale(scene, ref_length_bu, what='Reference bone')`

Check that a reference length is a plausible vertebrate skull size.

| Parameter | Type | Description |
|---|---|---|
| `scene` | `bpy.types.Scene` | Scene (for the unit scale). |
| `ref_length_bu` | float | Reference length in Blender units (e.g. the longest dimension of the cranium). |
| `what` | str | Name of the measured thing, used in the messages. |

**Returns** (tuple): `(ref_length_m or None, findings)`; findings are `(level, message)` with a hint about the Unit Scale that would make the size plausible.

### `check_parameters(density_g_cm3, specific_tension_n_cm2, fiber_length_ratio)`

Check the physiological parameters against literature ranges.

| Parameter | Type | Description |
|---|---|---|
| `density_g_cm3` | float | Muscle density (g/cm³). |
| `specific_tension_n_cm2` | float | Specific tension (N/cm²). |
| `fiber_length_ratio` | float | Fibre / muscle length ratio. |

**Returns** (list of tuple): Findings `(level, message)`; empty when everything is in range.

### `check_muscle(values, ref_length_m, belly_hole_error=0.0, belly_signed_volume=1.0)`

Plausibility findings for one muscle.

All size checks are ratios (to `ref_length_m` or between lengths), so the
same thresholds hold for any body size.

| Parameter | Type | Description |
|---|---|---|
| `values` | dict | Record values of the muscle (SI, keys from `RECORD_KEYS`). |
| `ref_length_m` | float or None | Reference (skull) length in metres, or None to skip size checks. |
| `belly_hole_error` | float | `hole_error` from `mesh_stats`. |
| `belly_signed_volume` | float | Signed volume from `mesh_stats` (negative = inverted normals). |

**Returns** (list of tuple): Findings `(level, message)`.

### `check_bilateral(volumes_by_name)`

Compare the volumes of left/right counterparts.

| Parameter | Type | Description |
|---|---|---|
| `volumes_by_name` | dict | Collection name -> volume (m³). |

**Returns** (dict): Collection name -> findings, only for pairs that differ more than `BILATERAL_VOLUME_RATIO`.

### `check_path_ends(origin_gap_m, insertion_gap_m, path_length_m)`

Findings for path ends that do not lie on their attachment areas.

| Parameter | Type | Description |
|---|---|---|
| `origin_gap_m` | float | Distance from the path's first point to the origin surface (m). |
| `insertion_gap_m` | float | Distance from its last point to the insertion surface (m). |
| `path_length_m` | float | Path length (m). |

**Returns** (list of tuple): WARNING per end farther than `PATH_END_TO_PATH` x the path length.

### `check_overlaps(shared_by_pair, volumes_by_name)`

Findings for muscles that occupy the same space (anatomically impossible).

| Parameter | Type | Description |
|---|---|---|
| `shared_by_pair` | dict | `(name_a, name_b)` -> volume inside both bellies (m³). |
| `volumes_by_name` | dict | Collection name -> belly volume (m³). |

**Returns** (dict): Collection name -> findings: WARNING when the shared volume is at least `MUSCLE_OVERLAP_WARNING` of the smaller muscle, INFO from `MUSCLE_OVERLAP_INFO` (minor interpenetration); nothing below.

### `worst_level(findings)`

Most severe level among findings.

| Parameter | Type | Description |
|---|---|---|
| `findings` | list of tuple | `(level, message)` pairs. |

**Returns** (str): One of `QA_OK`, `QA_INFO`, `QA_WARNING`, `QA_ERROR`.
