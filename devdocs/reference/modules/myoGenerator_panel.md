# `myoGenerator_panel`

Source: `myoGenerator_panel.py`

The MyoGeneratorRemix sidebar panel (View3D > Sidebar > MyoGeneratorRemix).

Drawing only. Sections: units/scale status, data location, muscle ID,
origin and insertion areas, path and loft, finish, parameters (specific
tension, density, fibre ratio, pennation) with Check / Calculate & Export,
the per-muscle QA box, and the experimental tools.

## Functions

### `draw_units_box(layout, context)`

Draw the scene scale (1 BU = ... mm), the result of the last scale check and
the "Set" unit-scale menu.

| Parameter | Type | Description |
|---|---|---|
| `layout` | `bpy.types.UILayout` | Layout to draw into. |
| `context` | `bpy.types.Context` | Draw context. |

### `draw_qa_box(layout, context)`

Draw one line per muscle record with its PCSA and worst finding (details on demand).

| Parameter | Type | Description |
|---|---|---|
| `layout` | `bpy.types.UILayout` | Layout to draw into. |
| `context` | `bpy.types.Context` | Draw context. |

### `draw_muscle_creation(layout, context)`

Preview first, then the muscle type, the controls and the settings, then the final mesh.

The preview is the belly as it will be generated (draft resolution); its
ring controls deform it in real time.

| Parameter | Type | Description |
|---|---|---|
| `layout` | `bpy.types.UILayout` | Layout to draw into. |
| `context` | `bpy.types.Context` | Draw context. |

## Blender classes

Operators, property groups and panels of this module are listed in [operators](../operators.md) and [properties](../properties.md): `MYOGENERATOR_PT_panel`.
