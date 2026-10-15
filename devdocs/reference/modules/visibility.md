# `visibility`

Source: `visibility.py`

Show and hide MyoGen objects by type, for every muscle of the scene.

Types (`KINDS`): origin areas, insertion areas (each with its contour),
bellies, paths and fibres (`<M>_fibres` and `<M>_fibre_detours`, written by
*Check Muscles* / *Calculate* with *Fibre length from: Belly fibres*). The
construction helpers of the muscle being built (preview, rings) are not
types: they exist for one muscle at a time and are removed by *Generate
Final Mesh*. **Toggle** shows or hides one type in every muscle, **Only** shows one
type and hides the others, **Show All** shows everything. Fine control of single
muscles is left to Blender's outliner.

## Constants

| Name | Value |
|---|---|
| `KINDS` | `{'ORIGIN': ('Origins', 'TRIA_UP'), 'INSERTION': ('Insertions', 'TRIA_DOWN'), 'BELLY': (...` |
| `_ROLE_KIND` | `{'origin': 'ORIGIN', 'origin_contour': 'ORIGIN', 'insertion': 'INSERTION', 'insertion_c...` |

## Functions

### `kind_of(obj, muscle_name, roles)`

Type of an object of a muscle collection, or None for other objects.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Object of the muscle collection. |
| `muscle_name` | str | Muscle (collection) name. |
| `roles` | dict | Object -> role, from `myo_record.resolve_objects`. |

**Returns** (str or None): 

### `objects_by_kind()`

Every MyoGen object of the scene, grouped by type.

**Returns** (dict): Kind (see `KINDS`) -> list of objects (every kind present).

### `is_visible(obj)`

True if the object is shown in the viewport (neither hidden nor disabled).

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Any object. |

**Returns** (bool): 

### `set_visible(objs, visible)`

Show or hide objects in the viewport.

| Parameter | Type | Description |
|---|---|---|
| `objs` | iterable of `bpy.types.Object` | Objects. |
| `visible` | bool | True to show. |

### `kind_items(context)`

Enum items of `KINDS` (for operator properties).

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `self` | `bpy.types.Operator` | The operator. |

**Returns** (list of tuple): 

### `draw_visibility(layout)`

Draw the visibility buttons: per type a toggle (pressed = visible) and *Only*.

| Parameter | Type | Description |
|---|---|---|
| `layout` | `bpy.types.UILayout` | Panel layout. |

## Blender classes

Operators, property groups and panels of this module are listed in [operators](../operators.md) and [properties](../properties.md): `MYOGEN_OT_toggle_kind`, `MYOGEN_OT_solo_kind`, `MYOGEN_OT_show_all_kinds`, `MYOGENERATOR_PT_visibility`.
