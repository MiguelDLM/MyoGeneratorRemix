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
| `SEEDINGS` | `('ORIGIN', 'INSERTION', 'BOTH', 'PAIRED')` |
| `DEFAULT_SEEDING` | `'BOTH'` |
| `PAIRED_SAMPLES` | `64` |
| `PAIRED_OUTSIDE_MAX` | `0.1` |
| `CG_TOL` | `1e-06` |
| `CG_MAX_ITER` | `4000` |
| `EXPORT_SEGMENTS` | `15` |
| `DETOURS_SUFFIX` | `'_fibre_detours'` |
| `LEGACY_DISPLAY_SUFFIXES` | `('_belly_fibres', '_belly_fibres_detours')` |
| `FIBRE_COLOR` | `(1.0, 0.85, 0.3, 1.0)` |
| `DETOUR_COLOR` | `(1.0, 0.0, 1.0, 1.0)` |

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

### `assignment(cost)`

Minimum-cost assignment of every row to a distinct column (Hungarian
algorithm with potentials, `O(n^2 m)`; `n` rows <= `m` columns).

| Parameter | Type | Description |
|---|---|---|
| `cost` | `numpy.ndarray` | Cost matrix, (n, m) with n <= m. |

**Returns** (`numpy.ndarray`): Column of each row.

**Raises** `ValueError`: If there are more rows than columns.

### `paired_courses(forward, backward, grid, samples=PAIRED_SAMPLES)`

One fibre per pair of seeds, the seeds spread over both attachments.

`forward` (seeded on the origin) and `backward` (seeded on the
insertion, reversed) streamlines are paired by optimal transport with
cost `|end(f) - insertion seed(b)|^2 + |start(b) - origin seed(f)|^2`:
each fibre joins two seeds the field would nearly join, and fibres do
not cross. The fibre is the forward streamline near its origin blending
smoothly (by field value) into the backward one near its insertion, so it
ends exactly on both seeds and follows the belly in between. With unequal
counts, the smaller set is paired completely.

| Parameter | Type | Description |
|---|---|---|
| `forward` | list of `numpy.ndarray` | Courses from origin seeds (origin to insertion). |
| `backward` | list of `numpy.ndarray` | Courses from insertion seeds, reversed (origin to insertion). |
| `grid` | tuple | Field grid (internal). |
| `samples` | int | Points per fibre. |

**Returns** (list of `numpy.ndarray`): Paired fibres, (samples, 3) each.

### `belly_fibres(belly, origin_obj, insertion_obj, count=DEFAULT_FIBRES, seeding=DEFAULT_SEEDING)`

Fibres of a finished belly between its attachments (Laplacian field).

`seeding` (`SEEDINGS`) chooses where fibres start:

* `ORIGIN`: `count` points spread over the origin, traced to the
  insertion. They gather where the field is strongest on the insertion
  and may leave much of it without fibres.
* `INSERTION`: the same from the insertion back to the origin.
* `BOTH` (default): both sets, each carrying half of the weight: both
  attachments are covered and the mean length does not depend on the
  side chosen, but each set bunches up on the other attachment.
* `PAIRED`: one fibre per pair of points, the points spread evenly over
  both attachments and paired by optimal transport so that each fibre
  joins where the field would take each of its ends
  (`paired_courses`); uniform coverage of both, equal weights.

Every course runs origin to insertion.

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
   * `seeding`: the seeding used;
   * `covered` / `covered_insertion`: fraction of the origin /
     insertion points the belly covers (seeded), None for a side not seeded;
   * `reached`: fraction of the seeded streamlines that arrived;
   * `origin_contact` / `insertion_contact`: fraction of each
     attachment's area the belly touches;
   * `seeds`, `voxel` and `iterations`.

| Parameter | Type | Description |
|---|---|---|
| `belly` | `bpy.types.Object` | Belly mesh (closed by `closed_belly` first). |
| `origin_obj` | `bpy.types.Object` | Origin attachment surface. |
| `insertion_obj` | `bpy.types.Object` | Insertion attachment surface. |
| `count` | int | Points seeded on each seeded attachment. |
| `seeding` | str | One of `SEEDINGS`. |

**Returns** (dict): dict with

**Raises** `ValueError`: If the belly does not touch an attachment or no fibre arrives.

### `remove_legacy_display(collection, muscle_name)`

Delete the fibre curves made by the former *Show Belly Fibres* operator.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |

### `length_stats(lengths, weights=None)`

Weighted mean and standard deviation, median, min and max of fibre lengths.

| Parameter | Type | Description |
|---|---|---|
| `lengths` | `numpy.ndarray` | Fibre lengths. |
| `weights` | `numpy.ndarray` | Fibre weights (default equal). |

**Returns** (dict): 

### `resample(course, segments=EXPORT_SEGMENTS)`

A polyline resampled to `segments + 1` points evenly spaced along it.

| Parameter | Type | Description |
|---|---|---|
| `course` | `numpy.ndarray` | Polyline, (K, 3). |
| `segments` | int | Number of segments. |

**Returns** (`numpy.ndarray`): 

### `export_fibres(collection, muscle_name, fibres, volume_m3, metres_per_unit, fiber_length_ratio, pennation_deg, segments=EXPORT_SEGMENTS)`

Write the fibres of a belly for simulators (`<M>_fibres`, `myo_record.write_fibres`).

Each kept fibre is resampled to `segments` segments; its rest length,
area weight, volume share and PCSA by both sharing rules
(`myo_record.fibre_pcsa`) are stored with it.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `fibres` | dict | Result of `belly_fibres`. |
| `volume_m3` | float | Belly volume (m³). |
| `metres_per_unit` | float | Metres per Blender unit. |
| `fiber_length_ratio` | float | Fascicle / fibre-line length. |
| `pennation_deg` | float | Pennation angle (degrees). |
| `segments` | int | Segments per fibre. |

**Returns** (`bpy.types.Object`): The fibres object.
