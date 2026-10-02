# `MyoGeneratorRemix`

Source: `__init__.py`

MyoGeneratorRemix: volumetric reconstruction of muscles and their parameters.

Package layout (see `devdocs/ARCHITECTURE.md`):

* `properties.py`                - scene settings (`scene.myogen`)
* `core_operators.py`            - attachments, mirroring, checks, export operators
* `improved_muscle_workflow.py`  - preview, path, ring and final mesh operators
* `tube.py`                      - path sampling and the tube swept along it
* `rings.py`                     - section rings sliding on the path (size, turn)
* `preview.py`                   - loft construction, path and attachment/bone geometry
* `volume_builder.py`            - solid belly (tube or fan fibres along the path), live preview, final mesh
* `fan.py`                       - fibres of fan-shaped muscles
* `fibre_texture.py`             - muscle texture oriented by the fibre arrangement
* `belly_fibres.py`              - fibres of a finished belly (Laplacian field) for the fibre length
* `curve_utilities.py`           - path-curve validation, sampling and orientation frames
* `muscle_utilities.py`          - selection helpers and contour alignment
* `muscle_texture.py`            - procedural muscle material
* `muscle_metrics.py`            - measurements, plausibility checks, CSV export
* `myo_record.py`                - the muscle-record contract shared with MUFIS
* `myoGenerator_panel.py`        - the sidebar UI

## Functions

### `get_preferences(context=None)`

MyoGeneratorRemix add-on preferences.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context (default: `bpy.context`). |

**Returns** (`MyoGeneratorPreferences` or None): The preferences, or None when the add-on is loaded under another module name.

## Blender classes

Operators, property groups and panels of this module are listed in [operators](../operators.md) and [properties](../properties.md): `MyoGeneratorPreferences`.
