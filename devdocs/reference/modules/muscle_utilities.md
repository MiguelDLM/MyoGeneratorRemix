# `muscle_utilities`

Source: `muscle_utilities.py`

Selection helpers and contour alignment used while reconstructing a muscle.

Measurements (volume, lengths, areas) live in `myo_record` and
`muscle_metrics`.

## Functions

### `select_and_edit_object(obj)`

Make a bone the only selected, active object and enter Edit Mode with face
selection and the lasso tool, ready to paint an attachment area.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Bone mesh (anything else is ignored). |

### `with_temp_object_active(context, obj, action)`

Run `action` with `obj` active in Object Mode, then restore the previous
active object and mode.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `obj` | `bpy.types.Object` | Object to make active. |
| `action` | callable | Callable without arguments. |

### `get_contour_direction_vector(contour_obj, reference_point)`

Circulation direction of a contour loop relative to a reference point.

| Parameter | Type | Description |
|---|---|---|
| `contour_obj` | `bpy.types.Object` | Contour curve (first spline used). |
| `reference_point` | `mathutils.Vector` | Point the contour faces (e.g. the other contour's centroid). |

**Returns** (tuple of (`mathutils.Vector`, float)): `(flow_vector, alignment)`: unit circulation axis and its dot product with the direction to `reference_point`; `(zero vector, 0.0)` for invalid contours.

### `align_contour_directions(origin_contour, insertion_contour)`

Make origin and insertion contours circulate in compatible directions so the
loft does not twist (reverses the insertion contour if needed).

| Parameter | Type | Description |
|---|---|---|
| `origin_contour` | `bpy.types.Object` | Origin contour curve. |
| `insertion_contour` | `bpy.types.Object` | Insertion contour curve (may be modified). |

**Returns** (bool): True if the contours are (now) aligned.

### `calculate_curve_centroid(curve_obj)`

Mean of the control points of a curve, world space.

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Curve object. |

**Returns** (`mathutils.Vector`): Centroid; zero vector for invalid curves.

### `reverse_contour_direction(contour_obj)`

Reverse the point order of a contour's first spline (handles swapped for Bezier).

| Parameter | Type | Description |
|---|---|---|
| `contour_obj` | `bpy.types.Object` | Contour curve (modified in place). |

**Returns** (bool): True on success.
