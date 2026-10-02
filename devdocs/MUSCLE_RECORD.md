# Muscle record — data contract (schema 1)

The muscle record is how MyoGeneratorRemix publishes its results inside a
`.blend` file so that other tools (MUFIS, scripts, exporters) can use them
without importing MyoGeneratorRemix. It is implemented in
`AddonFolder/myo_record.py`, which is **owned by this repository**; MUFIS keeps
a byte-identical copy (`MUFIS/tools/sync_shared.py` copies and checks it).

## Where it lives

```
<scene collection>
└── muscles/                         tag myo_root = True
    └── <M>/                         one collection per muscle; record = custom properties
        ├── <M>_origin               myo_role = "origin"             (mesh, world coordinates)
        ├── <M>_origin_contour       myo_role = "origin_contour"     (closed curve)
        ├── <M>_insertion            myo_role = "insertion"
        ├── <M>_insertion_contour    myo_role = "insertion_contour"
        ├── <M>_curve                myo_role = "path"               (Bezier path)
        └── <M>_muscle               myo_role = "belly"              (closed mesh)
```

`<M>` should end in `_left` / `_right` (or `_l`, `_r`, `.l`, `.r`, `_mid`) for
bilateral muscles; the side is parsed from it. Readers must find objects by
`myo_role` and fall back to the names above (scenes made before the schema),
which `myo_record.resolve_objects` does.

## Keys (custom properties on `<M>`)

All values are SI. Written by *Check Muscles* and *Calculate Muscle
Parameters* (`muscle_metrics.compute_muscles`).

| key | type | meaning |
|---|---|---|
| `myo_schema` | int | schema version (1) |
| `myo_name` | str | muscle name |
| `myo_side` | str | `L`, `R`, `M` or empty |
| `myo_origin_obj`, `myo_insertion_obj`, `myo_path_obj`, `myo_belly_obj` | str | object names (ID properties cannot hold pointers; resolve on read) |
| `myo_volume_m3` | float | belly volume actually enclosed (see `myo_volume_method`) |
| `myo_volume_raw_m3` | float | signed-sum volume of the belly mesh (differs from the above only for defective meshes) |
| `myo_volume_method` | str | `mesh`, `voxel union (defective mesh)` or `winding number (defective mesh)` |
| `myo_mass_kg` | float | volume × density |
| `myo_path_length_m` | float | evaluated length of the path curve |
| `myo_linear_length_m` | float | straight distance between the attachment centroids |
| `myo_fiber_length_m` | float | `path_length × fiber_length_ratio` |
| `myo_pcsa_m2` | float | `volume × cos(pennation) / fiber_length` |
| `myo_pcsa_method` | str | human-readable assumptions behind the PCSA |
| `myo_fiber_length_ratio` | float | fibre / muscle length used (1.0 = Herbst et al. 2022) |
| `myo_pennation_deg` | float | pennation angle used (0 = parallel fibres) |
| `myo_density_g_cm3` | float | density used for the mass |
| `myo_specific_tension_n_cm2` | float | specific tension used for the force |
| `myo_force_n` | float | `PCSA × tension` |
| `myo_origin_area_m2`, `myo_insertion_area_m2` | float | attachment areas |
| `myo_qa` | str | JSON list of `[level, message]`, levels `OK`/`INFO`/`WARNING`/`ERROR` |
| `myo_updated` | str | ISO-8601 UTC time of the last measurement |

A record may be partial (e.g. only `myo_schema`, `myo_name`, `myo_side` right
after *Submit Muscle*). Readers must treat missing keys as unknown:
`myo_record.read_record` returns None for them and `has_pcsa` tells whether a
usable PCSA exists.

## Reading a record (any tool)

```python
from . import myo_record                      # the verbatim copy

for coll in myo_record.iter_muscle_collections():
    rec = myo_record.read_record(coll)
    if rec["has_pcsa"]:
        force_n = myo_record.force_from_pcsa(rec["myo_pcsa_m2"], 30.0)
    origin_surface = rec["objects"].get("origin")
```

Readers must not write to the record or rename MyoGen objects.

## Changing the contract

* Adding an optional key is backwards compatible: add it to `RECORD_KEYS`,
  write it in `muscle_metrics.compute_muscles`, document it here, run
  `tools/sync_shared.py --update` from MUFIS.
* Renaming or removing a key, or changing a unit, is a new schema: bump
  `SCHEMA_VERSION`, keep `read_record` able to read version 1, and document
  the migration here.
