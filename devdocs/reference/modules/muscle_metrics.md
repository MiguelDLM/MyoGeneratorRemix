# `muscle_metrics`

Source: `muscle_metrics.py`

Muscle measurements, plausibility checks and CSV export.

`compute_muscles` is the single place where MyoGeneratorRemix measures
its muscles: it reads every muscle collection (via `myo_record`),
computes volume, mass, lengths, areas, PCSA and force in SI units, runs the
plausibility checks and writes the muscle records that other tools (MUFIS)
read. Operators in `core_operators` only call it and report.

## Constants

| Name | Value |
|---|---|
| `OVERLAP_CELLS_ACROSS` | `64` |
| `OVERLAP_REMESH` | `1.0 / 192` |
| `OVERLAP_MIN_CLOSED` | `0.25` |
| `CSV_FIELDS` | `[('name', lambda r: r['collection']), ('side', lambda r: r['myo_side']), ('volume_cm3',...` |

## Functions

### `scene_scale_findings(context, collections)`

Scale check of the current scene.

The reference is the longest bone picked as origin/insertion bone; without
them, the joint extent of the attachment surfaces (which spans most of the
skull) is used instead.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `collections` | list of `bpy.types.Collection` | Muscle collections (for the attachment extent). |

**Returns** (tuple): `(reference length in m or None, findings)`.

### `measure_fibres(props, belly, origin, insertion, path_m, mpu)`

Belly fibres of one muscle for the fibre length, with their QA findings.

| Parameter | Type | Description |
|---|---|---|
| `props` | `bpy.types.PropertyGroup` | Scene settings (`scene.myogen`). |
| `belly` | `bpy.types.Object` | Belly mesh, or None. |
| `origin` | `bpy.types.Object` | Origin attachment, or None. |
| `insertion` | `bpy.types.Object` | Insertion attachment, or None. |
| `path_m` | float | Path length (m), for the plausibility check. |
| `mpu` | float | Metres per Blender unit. |

**Returns** (tuple): `(fibres, findings)`; `fibres` (`belly_fibres.belly_fibres`) is None when they cannot be traced (the path is then used).

### `belly_overlaps(collections, metres_per_unit)`

Volume shared by every pair of bellies whose bounding boxes intersect.

Each belly is closed first (temporary voxel remesh,
`belly_fibres.closed_belly`: sculpted bellies may have holes or
self-overlaps); both are rasterised on one grid over the intersection of
their boxes (`OVERLAP_CELLS_ACROSS` cells across) and the cells inside
both are counted.

| Parameter | Type | Description |
|---|---|---|
| `collections` | list of `bpy.types.Collection` | Muscle collections. |
| `metres_per_unit` | float | Metres per Blender unit. |

**Returns** (tuple): `(shared, unchecked)`: `(name_a, name_b)` -> shared volume (m³) for pairs that share any, and the names of bellies whose closed copy collapsed (less than `OVERLAP_MIN_CLOSED` of their own volume: their overlaps cannot be measured).

### `compute_muscles(context, write=True)`

Measure every muscle, run the plausibility checks and write the records.

Per muscle: volume and mass (belly; the voxel-enclosed volume replaces the
signed-sum volume when a closed belly overlaps itself by more than
`myo_record.OVERLAP_VOLUME_TOLERANCE`), path length and straight length
(between the path's terminal vertices, `myo_record.curve_ends`; the
attachment centroids without a path) with a check that the path ends lie
on their attachment areas, fibre length
and PCSA (`myo_record.pcsa_from_volume` with the scene's ratio and
pennation, or `myo_record.pcsa_from_fibres` from the belly fibres
when `fiber_length_source` is `BELLY_FIBRES`; with `write` the fibres
are then also exported as `<M>_fibres` for simulators,
`belly_fibres.export_fibres`), force, attachment areas and centroids, then
`myo_record.check_muscle`, the left/right comparison and the
overlap between muscles (`belly_overlaps`,
`myo_record.check_overlaps`).

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context (reads `scene.myogen`). |
| `write` | bool | Tag the objects' roles and store the muscle records on the collections. |

**Returns** (tuple): `(rows, scene_findings)`; each row holds the record values (SI) plus `collection`, `origin_centroid`, `insertion_centroid` (Blender units) and `qa` (list of `(level, message)`). The scene findings are also stored in `scene.myogen.scene_qa`.

### `write_csv(path, rows)`

Write muscle rows to a CSV file (columns from `CSV_FIELDS`).

| Parameter | Type | Description |
|---|---|---|
| `path` | str | Destination file. |
| `rows` | list of dict | Rows returned by `compute_muscles`. |

**Raises** `OSError`: If the file cannot be written.
