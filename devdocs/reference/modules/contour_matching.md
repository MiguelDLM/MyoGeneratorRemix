# `contour_matching`

Source: `contour_matching.py`

Point correspondence between the origin and insertion contours of a loft.

The muscle belly is lofted between two closed contours (the boundaries of the
attachment areas). The loft joins point `j` of one contour to point `j`
of the other, so the result depends on where each contour starts, which way
it runs and how many vertices it has. Matching by vertex index produced
twisted, hourglass-shaped bellies unless the index was rotated by hand.

This module removes that dependence:

1. `resample_closed_loop` - both contours are resampled to the same
   number of points, evenly spaced by arc length (independent of the original
   vertex count and density).
2. Both contours are centred on their centroids. By default they are compared
   in 3D (they are rarely planar: a temporal fossa boundary is strongly
   curved); `local_coordinates` can instead express them in 2D frames,
   for lofts that rotate their sections with the path.
3. Direction: both contours must circulate the same way, i.e. their vector
   areas (`vector_area`, the contours' own normals) must point to the
   same side. Elongated contours otherwise "match" just as well backwards,
   and the loft folds into a figure-eight with almost no area in the middle
   (its RMS size looks fine, its volume does not). This also holds for
   sheet-like muscles such as the temporalis, whose attachment contours are
   seen edge-on from the origin-insertion axis. Only when the two normals are
   nearly perpendicular is the direction left to the search.
4. `best_cyclic_match` - the starting point is chosen to minimise the
   sum of squared distances between corresponding centred points, i.e. to
   maximise `sum a_j . b_j`, the size of the loft's mid-way section
   `(a + b) / 2`. The cost is invariant to translation and scale.

Diagnostics: `waist_index` (RMS size of the mid-way section relative to
the ends; < 1 = hourglass) and `section_area_ratio` (area of the mid-way
section relative to the ends; near 0 = folded or twisted).

No dependency on `bpy`: works on sequences of 3-vectors and is unit-tested
outside Blender (`tests/test_contour_matching.py`).

## Functions

### `resample_closed_loop(points, n)`

Resample a closed polyline to `n` points evenly spaced by arc length.

| Parameter | Type | Description |
|---|---|---|
| `points` | sequence of 3-vectors | Contour points in order (the last point is joined to the first). |
| `n` | int | Number of output points (>= 3). |

**Returns** (numpy.ndarray of shape (n, 3)): `n` points; starts at `points[0]`.

**Raises** `ValueError`: With fewer than 3 points or a zero-length contour.

### `local_coordinates(points, normal, binormal)`

2D coordinates of a contour around its centroid in a frame.

| Parameter | Type | Description |
|---|---|---|
| `points` | array-like of shape (n, 3) | Contour points. |
| `normal` | 3-vector | First in-plane axis (e.g. the path normal at that end). |
| `binormal` | 3-vector | Second in-plane axis (the path binormal at that end). |

**Returns** (numpy.ndarray): `(n, 2)` coordinates; the component along the path tangent is dropped.

### `best_cyclic_match(a, b, directions=(False, True))`

Cyclic shift and direction of `b` that best matches `a`.

Minimises `sum_j |a[j] - b[(s + d*j) mod n]|^2` over shifts `s` and
directions `d` in {+1, -1}.

| Parameter | Type | Description |
|---|---|---|
| `a` | array-like of shape (n, k) | Reference contour (e.g. origin), any dimension. |
| `b` | array-like of shape (n, k) | Contour to re-index (e.g. insertion), same shape. |
| `directions` | tuple of bool | Directions to try: `False` = as given, `True` = reversed. |

**Returns** (tuple of (int, bool, float)): `(shift, reversed, mean_distance)`; apply with `apply_match`. `mean_distance` is the RMS distance between matched points.

**Raises** `ValueError`: If the shapes differ.

### `apply_match(points, shift, reverse)`

Re-index a contour with the result of `best_cyclic_match`.

| Parameter | Type | Description |
|---|---|---|
| `points` | sequence | Contour points (`n` of them). |
| `shift` | int | Index of the point matched to reference point 0. |
| `reverse` | bool | Whether the contour runs backwards. |

**Returns** (list): Re-indexed points (same element type as the input).

### `waist_index(origin, insertion)`

Hourglass diagnostic of a straight loft between matched contours.

| Parameter | Type | Description |
|---|---|---|
| `origin` | array-like of shape (n, 3) | Origin contour points, matched order. |
| `insertion` | array-like of shape (n, 3) | Insertion contour points, same order. |

**Returns** (float): RMS radius of the mid-way contour divided by the mean RMS radius of the two ends: 1 = no narrowing, values well below 1 = hourglass (twist).

### `vector_area(points)`

Vector area of a closed contour (around its centroid).

Its direction is the contour's circulation axis (right-hand rule) and its
length the area of a planar contour.

| Parameter | Type | Description |
|---|---|---|
| `points` | array-like of shape (n, 3) | Contour points in order. |

**Returns** (numpy.ndarray of shape (3,)): 

### `section_area_ratio(origin, insertion)`

Area of the mid-way loft section relative to the ends.

| Parameter | Type | Description |
|---|---|---|
| `origin` | array-like of shape (n, 3) | Origin contour points, matched order. |
| `insertion` | array-like of shape (n, 3) | Insertion contour points, same order. |

**Returns** (float): `|A_mid| / mean(|A_origin|, |A_insertion|)` with `A` the vector areas; about 1 for a well-formed loft (can exceed 1 when the end contours are differently oriented), near 0 when the middle section folds into a figure-eight.

### `circulation_directions(origin, insertion, perpendicular=0.2)`

Directions of the insertion contour worth trying.

| Parameter | Type | Description |
|---|---|---|
| `origin` | array-like of shape (n, 3) | Origin contour points (resampled). |
| `insertion` | array-like of shape (n, 3) | Insertion contour points (resampled). |
| `perpendicular` | float | If the cosine between the two contour normals is below this value they count as perpendicular (direction undetermined). |

**Returns** (tuple of bool): `(False,)` if both circulate the same way (normals on the same side), `(True,)` if oppositely, `(False, True)` if undetermined.

### `match_contours(origin_points, insertion_points, n, origin_frame=None, insertion_frame=None)`

Resample both contours to `n` points and re-index the insertion one.

| Parameter | Type | Description |
|---|---|---|
| `origin_points` | sequence of 3-vectors | Origin contour, in order. |
| `insertion_points` | sequence of 3-vectors | Insertion contour, in order (any start, direction, count). |
| `n` | int | Points per contour in the loft. |
| `origin_frame` | tuple of 3-vectors or None | `(normal, binormal)` of the path at the origin end, to compare the contours in 2D path frames; None (default) compares the centred contours in 3D, which suits lofts that interpolate in world space. |
| `insertion_frame` | tuple of 3-vectors or None | `(normal, binormal)` of the path at the insertion end (parallel-transported from the origin, so both frames are consistent). |

**Returns** (tuple): `(origin, insertion, info)`: `(n, 3)` arrays in matched order and a dict with `shift`, `reversed`, `rms_mismatch` (contour units), `waist` (`waist_index`) and `section_area` (`section_area_ratio`) of the matched pair.
