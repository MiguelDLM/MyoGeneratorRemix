# `curve_utilities`

Source: `curve_utilities.py`

Path-curve helpers for the muscle loft: validation, smoothing, Bezier
sampling and twist-free orientation frames along the path.

## Functions

### `validate_curve_object(curve_obj)`

Check that an object can be used as a muscle path.

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Candidate object. |

**Returns** (tuple of (bool, str)): `(is_valid, message)`.

### `smooth_curve_transitions(curve_obj, smoothing_factor=0.5)`

Smooth the control points of a path curve (moves interior points towards
the average of their neighbours).

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Muscle path curve (modified in place). |
| `smoothing_factor` | float | Blend towards the neighbour average (0-1). |

**Returns** (bool): True if the curve was smoothed.

### `get_bezier_point_at_parameter(curve_obj, t)`

Position, tangent and radius on the evaluated Bezier path (not on the
straight lines between control points).

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Muscle path curve (first spline, Bezier). |
| `t` | float | Parameter along the curve, 0 (origin) to 1 (insertion). |

**Returns** (tuple of (`mathutils.Vector`, `mathutils.Vector`, float)): `(position, tangent, radius)` in world space; a default frame for invalid curves.

### `calculate_consistent_orientation_frame(curve_obj, t)`

Twist-free frame along the path by parallel transport.

Keeps the normal orientation consistent along the whole curve, which
prevents mesh inversion in sharp bends. The transported frame is cached on
the function between calls; call `reset_orientation_frame` before each
new loft.

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Muscle path curve (first spline, Bezier). |
| `t` | float | Parameter along the curve, 0 (origin) to 1 (insertion). |

**Returns** (tuple): `(tangent, normal, binormal, radius)`.

### `parallel_transport_frame(prev_tangent, curr_tangent, prev_normal, prev_binormal)`

Transport a normal/binormal pair from one tangent to the next
(rotation-minimising "Bishop" frame).

| Parameter | Type | Description |
|---|---|---|
| `prev_tangent` | `mathutils.Vector` | Tangent at the previous sample. |
| `curr_tangent` | `mathutils.Vector` | Tangent at the current sample. |
| `prev_normal` | `mathutils.Vector` | Normal at the previous sample. |
| `prev_binormal` | `mathutils.Vector` | Binormal at the previous sample. |

**Returns** (tuple of `mathutils.Vector`): `(normal, binormal)` at the current sample.

### `reset_orientation_frame()`

Clear the cached frame of `calculate_consistent_orientation_frame` (call before each new loft).


### `calculate_frenet_frame_from_bezier(curve_obj, t, smoothing=0.5)`

Frenet-like frame from the Bezier tangent, used to seed the parallel transport.

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Muscle path curve (first spline, Bezier). |
| `t` | float | Parameter along the curve, 0 (origin) to 1 (insertion). |
| `smoothing` | float | Blend factor for the normal estimate. |

**Returns** (tuple of `mathutils.Vector`): `(tangent, normal, binormal)`.

### `get_bezier_tangent_at_parameter(curve_obj, t)`

Unit tangent of the Bezier path (see `get_bezier_point_at_parameter`).

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Muscle path curve (first spline, Bezier). |
| `t` | float | Parameter along the curve, 0 (origin) to 1 (insertion). |

**Returns** (`mathutils.Vector`): 

### `verify_frame_consistency(tangent, normal, binormal, prev_normal=None, prev_binormal=None)`

Re-orthogonalise a frame and flip it if it inverted relative to the previous one.

| Parameter | Type | Description |
|---|---|---|
| `tangent` | `mathutils.Vector` | Current tangent. |
| `normal` | `mathutils.Vector` | Current normal. |
| `binormal` | `mathutils.Vector` | Current binormal. |
| `prev_normal` | `mathutils.Vector` | Previous normal, or None. |
| `prev_binormal` | `mathutils.Vector` | Previous binormal, or None. |

**Returns** (tuple of `mathutils.Vector`): `(normal, binormal)` corrected.

### `detect_global_inversions(curve_obj, num_samples=20)`

Sample the path and report frame inversions to the console (diagnostic).

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Muscle path curve. |
| `num_samples` | int | Number of samples along the curve. |

**Returns** (bool): Whether the curve needs special inversion handling (currently always False).
