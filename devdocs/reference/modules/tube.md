# `tube`

Source: `tube.py`

Tube of a muscle: an elliptical section swept along the muscle path.

The path `<M>_curve` (edited by the user) gives the course; the section
size and turn along it come either from the muscle type's default profile
(`default_profile`) or from the section rings placed on the path
(`rings`). The tube guarantees that the solid belly joins both
attachments (e.g. a fusiform muscle between two long bones).

## Constants

| Name | Value |
|---|---|
| `ATTACHMENT_RADIUS_FRACTION` | `0.6` |
| `TYPE_PROFILES` | `{'FUSIFORM': (0.8, 1.0), 'PARALLEL': (0.0, 0.6), 'FAN': (0.0, 0.8)}` |
| `DEFAULT_SECTIONS` | `5` |
| `ELLIPSE_POINTS` | `32` |
| `CURVE_RESOLUTION` | `32` |
| `PATH_SAMPLES` | `96` |

## Functions

### `frames(points)`

Unit tangents and parallel-transported normals along `points`.

| Parameter | Type | Description |
|---|---|---|
| `points` | list of `mathutils.Vector` | Course points. |

**Returns** (tuple): `(tangents, normals)`.

### `attachment_radius(surface_obj)`

Radius used for the tube end at an attachment.

| Parameter | Type | Description |
|---|---|---|
| `surface_obj` | `bpy.types.Object` | Attachment surface. |

**Returns** (float): `ATTACHMENT_RADIUS_FRACTION` x radius of a disc of the same area.

### `sample_path(curve_obj, samples=PATH_SAMPLES)`

Points along the evaluated path, evenly spaced by arc length (world space).

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Path curve (first spline; Bezier, poly or NURBS points). |
| `samples` | int | Number of points (≥ 2). |

**Returns** (list of `mathutils.Vector`): `samples` points from the first to the last control point.

**Raises** `ValueError`: If the curve has fewer than 2 points.

### `project_on_path(points, location)`

Arc-length fraction (0-1) of the point of a sampled path nearest to `location`.

| Parameter | Type | Description |
|---|---|---|
| `points` | list of `mathutils.Vector` | Arc-length samples (`sample_path`). |
| `location` | `mathutils.Vector` | World-space point. |

**Returns** (float): 

### `default_profile(origin_surface, insertion_surface, shape)`

Default sections `(u, width, thickness, twist)` of a muscle type.

| Parameter | Type | Description |
|---|---|---|
| `origin_surface` | `bpy.types.Object` | Origin attachment surface. |
| `insertion_surface` | `bpy.types.Object` | Insertion attachment surface. |
| `shape` | str | Muscle type (`TYPE_PROFILES` key). |

**Returns** (list of tuple): 

### `path_tube(points, sections, ellipse=ELLIPSE_POINTS)`

Closed tube along a sampled path, sized and turned by `sections`.

| Parameter | Type | Description |
|---|---|---|
| `points` | list of `mathutils.Vector` | Arc-length samples of the path (`sample_path`). |
| `sections` | list of tuple | `(u, width, thickness, twist)` with `u` the arc-length fraction (0 = origin end, 1 = insertion end) and `twist` the turn of the width direction about the path (radians, from the path's parallel-transported normal). |
| `ellipse` | int | Points per section. |

**Returns** (`bmesh.types.BMesh`): New world-space bmesh with outward normals (caller frees it).

**Raises** `ValueError`: With fewer than 2 path points or no section.
