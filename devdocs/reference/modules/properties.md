# `properties`

Source: `properties.py`

Scene settings of MyoGeneratorRemix, stored at `scene.myogen`.

Measured results are not stored here: they go to the muscle records on each
muscle collection (see `myo_record`).

## Functions

### `on_section_cut_toggled(context)`

Callback when section_cut_active is toggled.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |

### `on_section_cut_changed(context)`

Callback when section cut parameters change.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |

### `update_muscles_visibility(context)`

Update callback of `show_muscles`: show/hide every muscle belly.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `self` | `MyoGeneratorProperties` | The property group. |

### `update_attachments_visibility(context)`

Update callback of `show_attachments`: show/hide attachment surfaces and contours.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `self` | `MyoGeneratorProperties` | The property group. |

### `update_curves_visibility(context)`

Update callback of `show_curves`: show/hide every path curve.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `self` | `MyoGeneratorProperties` | The property group. |

## Blender classes

Operators, property groups and panels of this module are listed in [operators](../operators.md) and [properties](../properties.md): `MyoGeneratorProperties`.
