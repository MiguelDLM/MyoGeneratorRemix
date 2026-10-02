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

### `compute_muscles(context, write=True)`

Measure every muscle, run the plausibility checks and write the records.

Per muscle: volume and mass (belly; the voxel-enclosed volume replaces the
signed-sum volume when a closed belly overlaps itself by more than
`myo_record.OVERLAP_VOLUME_TOLERANCE`), path and straight lengths, fibre length
and PCSA (`myo_record.pcsa_from_volume` with the scene's ratio and
pennation), force, attachment areas and centroids, then
`myo_record.check_muscle` and the left/right comparison.

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
