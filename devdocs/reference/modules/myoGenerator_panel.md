# `myoGenerator_panel`

Source: `myoGenerator_panel.py`

The MyoGeneratorRemix sidebar panel (View3D > Sidebar > MyoGeneratorRemix).

Drawing only. Sections in working order: units/scale status, muscle name,
attachments (origin and insertion), muscle creation (preview, type, path,
rings, settings, final mesh, next muscle), measurements (parameters, fibres,
CSV location, Check / Calculate & Export), the muscle list (QA and texture)
and the experimental tools. Showing/hiding objects by type is the separate
*Show in Scene* panel (`visibility`).

## Constants

| Name | Value |
|---|---|
| `SHORT_FINDINGS` | `(("Overlaps '([^']+)'.*?\\(([\\d.]+)% of the smaller", 'Overlap {0} {1}%'), ('Overlap w...` |
| `SHORT_FINDING_MAX` | `32` |

## Functions

### `draw_units_box(layout, context)`

Draw the scene scale (1 BU = ... mm), the result of the last scale check and
the "Set" unit-scale menu.

| Parameter | Type | Description |
|---|---|---|
| `layout` | `bpy.types.UILayout` | Layout to draw into. |
| `context` | `bpy.types.Context` | Draw context. |

### `short_finding(message)`

A few words for a QA finding (its full text is the tooltip).

| Parameter | Type | Description |
|---|---|---|
| `message` | str | Full finding text. |

**Returns** (str): 

### `draw_qa_box(layout, context)`

The muscle list: one collapsible row per muscle (status icon, name,
number of errors and warnings); expanded: volume · PCSA · force, a short
label per finding (full text on hover; errors, warnings, then notes) and
the texture.

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

Operators, property groups and panels of this module are listed in [operators](../operators.md) and [properties](../properties.md): `MYOGEN_OT_qa_finding`, `MYOGENERATOR_PT_panel`.
