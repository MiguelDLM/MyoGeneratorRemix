# `fan`

Source: `fan.py`

Fan-shaped (convergent) muscles built from fibres.

A fan muscle (temporalis, pectoralis major, …) spreads over a broad origin
and converges on a narrow insertion. Its belly is the union of fibres: one
from every part of the origin attachment to the matching part of the
insertion, all following the muscle path `<M>_curve`, each with a radius
equal to the local half-thickness of the muscle.

* Fibre starts are spread evenly over the origin attachment
  (`sample_surface`) and lifted off the bone by the half-thickness;
  each fibre ends at the point of the insertion with the same relative
  position (the two footprints are matched in one fixed frame, scaled to
  each other's extent).
* Each fibre runs straight from its start to its end plus the path's bend
  (the path's offset from its chord), so the fibres curve with the path,
  converge on the insertion and never twist around each other.
* Section rings (`rings`), when used, set at their place the width of
  the fan (X, along its widest direction), its half-thickness (Y) and its
  turn (R). Without rings the fan has its natural width and the default
  thickness (`default_thickness`).

`occupancy` rasterises the fibres (capsules) into the voxel grid of
`volume_builder`.

## Constants

| Name | Value |
|---|---|
| `FIBRES` | `240` |
| `DRAFT_FIBRES` | `120` |
| `FIBRE_SAMPLES` | `40` |
| `RADIUS_STEP` | `0.5` |
| `STAMP_CHUNK` | `2000` |
| `THICKNESS_FRACTION` | `0.08` |
| `THICKNESS_BELLY` | `0.3` |
| `NATURAL_FIBRES` | `60` |

## Functions

### `sample_surface(surface_obj, count)`

About `count` points spread evenly over a surface, with outward normals' faces.

One point per cell of a grid whose spacing gives `count` cells over the
surface's area (the face centre nearest to the cell's centre of mass).

| Parameter | Type | Description |
|---|---|---|
| `surface_obj` | `bpy.types.Object` | Attachment surface. |
| `count` | int | Target number of points. |

**Returns** (tuple of list of `mathutils.Vector`): `(points, normals)`: world-space face centres and face normals.

### `default_thickness(path_points)`

Default half-thickness profile `h(u)` of a fan muscle (Blender units).

| Parameter | Type | Description |
|---|---|---|
| `path_points` | list of `mathutils.Vector` | Arc-length samples of the path. |

**Returns** (callable): Function of `u` (0-1).

### `fibres(path_points, origin_surface, insertion_surface, bones, count, thickness=None, sections=None)`

Fibre courses of a fan muscle and their radii.

Each fibre runs straight from its start on the origin to its end on the
insertion, plus the path's own bend (its offset from the straight chord
between its ends), so all fibres curve like the path without twisting.
Starts and ends are matched in one fixed frame (the chord and two axes
perpendicular to it), scaling the origin footprint to the insertion's
extent axis by axis.

| Parameter | Type | Description |
|---|---|---|
| `path_points` | list of `mathutils.Vector` | Arc-length samples of the muscle path (origin to insertion). |
| `origin_surface` | `bpy.types.Object` | Origin attachment surface. |
| `insertion_surface` | `bpy.types.Object` | Insertion attachment surface. |
| `bones` | sequence of `bpy.types.Object` | `(origin_bone, insertion_bone)` (orient the normals; None allowed). |
| `count` | int | Number of fibres (approximate). |
| `thickness` | callable | Half-thickness `h(u)`; default `default_thickness`. |
| `sections` | list of tuple | Ring sections `(u, width, thickness, twist)`, or None for the natural fan. `width` is the fan's half-width along its widest direction, `twist` the angle of that direction about the path from the path's transported normal. |

**Returns** (tuple): `(courses, radii, natural)`: `courses` is an array (fibres, `FIBRE_SAMPLES`, 3) of world-space points, `radii` an array (`FIBRE_SAMPLES`,) of half-thicknesses, and `natural` a list of `(u, half_width, angle)` of the natural fan (for default rings).

**Raises** `ValueError`: If an attachment has no faces.

### `natural_profile(path_points, origin_surface, insertion_surface, bones)`

The fan's natural section along the path, as used by the rings.

| Parameter | Type | Description |
|---|---|---|
| `path_points` | list of `mathutils.Vector` | Arc-length samples of the path. |
| `origin_surface` | `bpy.types.Object` | Origin attachment surface. |
| `insertion_surface` | `bpy.types.Object` | Insertion attachment surface. |
| `bones` | sequence of `bpy.types.Object` | `(origin_bone, insertion_bone)`. |

**Returns** (callable): `natural(u) -> (half_width, half_thickness, angle)`: the fan's half-width along its widest direction, the default half-thickness and the angle of the widest direction about the path.

### `occupancy(courses, radii, xs, ys, zs)`

Voxels within each fibre's radius of its course (union of capsules).

Each fibre is sampled densely enough (spacing ≤ half the radius) and a
sphere is stamped at every sample. Samples are grouped by radius
(quantised to `RADIUS_STEP` voxel) so each group is written at once with
a precomputed spherical stencil.

| Parameter | Type | Description |
|---|---|---|
| `courses` | `numpy.ndarray` | Fibre courses (fibres, samples, 3). |
| `radii` | `numpy.ndarray` | Radius at each sample (samples,). |
| `xs` | `numpy.ndarray` | Voxel-centre X coordinates (evenly spaced). |
| `ys` | `numpy.ndarray` | Voxel-centre Y coordinates. |
| `zs` | `numpy.ndarray` | Voxel-centre Z coordinates. |

**Returns** (`numpy.ndarray`): Boolean array (len(xs), len(ys), len(zs)).
