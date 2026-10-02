# `belly_fibres`

Source: `belly_fibres.py`

Fibres of a finished (sculpted) belly from a Laplacian field.

Following Choi & Blemker (2013, *Skeletal muscle fascicle arrangements can be
reconstructed using a Laplacian vector field simulation*, PLoS ONE 8(10):
e77576, https://doi.org/10.1371/journal.pone.0077576):

1. the belly mesh is voxelised (`volume_builder.occupancy`);
2. a scalar field `u` is solved inside it with Laplace's equation,
   `u = 0` on the voxels touching the origin attachment, `u = 1` on those
   touching the insertion and no flux through the rest of the belly surface
   (`laplace_field`, conjugate gradients);
3. fibres are the streamlines of `grad u` from points spread evenly over
   the origin attachment to the insertion **and** from points spread evenly
   over the insertion back to the origin (`trace`), half of the weight
   each: one side alone leaves much of the other without fibres. They fill
   the belly as sculpted, never cross, and fan out or converge with its
   shape. Detours (much longer than the straight distance between their
   ends) are set apart.

Each fibre runs from attachment to attachment (tendon included): its length
is a muscle-belly length, which the fibre/muscle ratio scales to a fascicle
length as for the path (see `devdocs/ARCHITECTURE.md`, *Fibre length*).
Each fibre also gets its share of the belly volume (the voxels nearest to
it), used by the fibre-weighted PCSA (`myo_record.pcsa_from_fibres`).

## Constants

| Name | Value |
|---|---|
| `GRID_ACROSS` | `96` |
| `DEFAULT_FIBRES` | `150` |
| `CONTACT_VOXELS` | `1.5` |
| `FRONT_REACH_VOXELS` | `3.0` |
| `STEP_VOXELS` | `0.4` |
| `REACH_U` | `0.97` |
| `DETOUR_MAX` | `2.0` |
| `CONTACT_REACH_VOXELS` | `2.0` |
| `CONTACT_SAMPLES` | `300` |
| `CG_TOL` | `1e-06` |
| `CG_MAX_ITER` | `4000` |
| `FIBRES_SUFFIX` | `'_belly_fibres'` |
| `DETOURS_SUFFIX` | `'_belly_fibres_detours'` |

## Functions

### `laplace_field(inside, fixed, values, tol=CG_TOL, max_iter=CG_MAX_ITER)`

Solve Laplace's equation on a voxel region.

Dirichlet values on `fixed` voxels, zero flux through the boundary of
`inside` (only neighbours inside count). Free voxels not connected to a
fixed one stay 0.

| Parameter | Type | Description |
|---|---|---|
| `inside` | `numpy.ndarray` | Region, boolean (X, Y, Z). |
| `fixed` | `numpy.ndarray` | Fixed voxels (subset of `inside`). |
| `values` | `numpy.ndarray` | Values of the fixed voxels (read where `fixed`). |
| `tol` | float | Relative residual at which to stop. |
| `max_iter` | int | Iteration limit. |

**Returns** (tuple): `(u, iterations)`: field (0 outside `inside`) and iterations used.

### `trace(grad, u, known, origin, voxel, seeds, max_steps)`

Streamlines of `grad` from `seeds` until `u` reaches `REACH_U`.

| Parameter | Type | Description |
|---|---|---|
| `grad` | `numpy.ndarray` | Gradient field (X, Y, Z, 3). |
| `u` | `numpy.ndarray` | Field (X, Y, Z), extended outside the region. |
| `known` | `numpy.ndarray` | Voxels where `u` is defined. |
| `origin` | `numpy.ndarray` | World position of voxel (0, 0, 0). |
| `voxel` | float | Voxel size. |
| `seeds` | `numpy.ndarray` | Start points (N, 3). |
| `max_steps` | int | Step limit. |

**Returns** (tuple): `(courses, reached)`: list of (K, 3) arrays and boolean (N,).

### `closed_belly(belly, voxel)`

World-space closed copy of a belly, whatever its defects.

Holes are filled and the surface is rebuilt by a temporary voxel Remesh
(as `myo_record.enclosed_volume`): sculpted bellies often have open
or non-manifold edges and self-overlaps, which break inside/outside tests.
The belly is left unchanged.

| Parameter | Type | Description |
|---|---|---|
| `belly` | `bpy.types.Object` | Belly mesh object. |
| `voxel` | float | Remesh voxel size (Blender units). |

**Returns** (`bmesh.types.BMesh`): Closed bmesh (caller frees it).

### `belly_fibres(belly, origin_obj, insertion_obj, count=DEFAULT_FIBRES)`

Fibres of a finished belly between its attachments (Laplacian field).

Fibres are traced **from both attachments**: `count` from points spread
over the origin to the insertion, and `count` from points spread over
the insertion back to the origin (reversed, so every course runs origin
to insertion). Streamlines seeded on one side only gather where the field
is strongest on the other and leave much of it without fibres; the two
sets together cover both attachments, and each set carries half of the
weight, so the mean length no longer depends on the side chosen.

Fibres longer than `DETOUR_MAX` times the straight distance between
their ends are **detours** (the field following a thin curved sheet round
a bend): they are kept apart and left out of the lengths and the volume
shares.

Results are cached until the belly or the attachments change.


   * `courses`: kept fibres, (K, 3) world-space arrays from origin to insertion;
   * `lengths` (Blender units) and `weights` (sum 1: each seeding side
     carries half) of the kept fibres;
   * `shares`: fraction of the belly volume nearest to each kept fibre (sum 1);
   * `detours`: courses of the detoured fibres; `detoured`: their
     fraction of the arrived fibres;
   * `covered` / `covered_insertion`: fraction of the origin /
     insertion points the belly covers (seeded);
   * `reached`: fraction of the seeded fibres that arrived;
   * `origin_contact` / `insertion_contact`: fraction of each
     attachment's area the belly touches;
   * `seeds`, `voxel` and `iterations`.

| Parameter | Type | Description |
|---|---|---|
| `belly` | `bpy.types.Object` | Belly mesh (closed by `closed_belly` first). |
| `origin_obj` | `bpy.types.Object` | Origin attachment surface. |
| `insertion_obj` | `bpy.types.Object` | Insertion attachment surface. |
| `count` | int | Fibres seeded on each attachment. |

**Returns** (dict): dict with

**Raises** `ValueError`: If the belly does not touch an attachment or no fibre arrives.

### `show_fibres(collection, muscle_name, courses, detours=())`

Create (or replace) `<M>_belly_fibres`: a curve with one poly spline per fibre.

Detoured fibres, if given, go to `<M>_belly_fibres_detours` (magenta).

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `courses` | list of `numpy.ndarray` | World-space fibre courses. |
| `detours` | list of `numpy.ndarray` | World-space courses of detoured fibres. |

**Returns** (`bpy.types.Object`): The curve object of the kept fibres.

### `remove_fibres(collection, muscle_name)`

Delete `<M>_belly_fibres` (and its detours) if present.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |

**Returns** (bool): True if something was removed.

### `length_stats(lengths, weights=None)`

Weighted mean and standard deviation, median, min and max of fibre lengths.

| Parameter | Type | Description |
|---|---|---|
| `lengths` | `numpy.ndarray` | Fibre lengths. |
| `weights` | `numpy.ndarray` | Fibre weights (default equal). |

**Returns** (dict): 
