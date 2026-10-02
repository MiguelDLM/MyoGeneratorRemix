# `preview`

Source: `preview.py`

Loft construction and attachment/bone geometry helpers.

The loft (`build_loft`) is the raw material of the *Along the path*
belly: it is built in memory from the path curve and the two attachment
contours and never shown; `volume_builder` turns it into the solid
belly that the preview and the final mesh show.

Loft construction
-----------------
Both contours are resampled and matched (`contour_matching`); for
`FOLLOW_PATH` each section keeps the interpolated contour's principal axes
and is placed on the path with the muscle-shape profile
(`shape_section`); `DIRECT_CONNECTION` interpolates the contours along
the straight segment. The end sections lie exactly on the attachment
contours and the caps are draped over the attachment surfaces; the path only
acts away from the ends (`anchor_weight`). The final belly keeps
`ANCHORED_GROUP` plus a sculpt mask on the vertices lying on the attachments.

## Constants

| Name | Value |
|---|---|
| `PREVIEW_MATERIAL` | `'MyoGen preview'` |
| `DEFORM_GROUP` | `'myo_deform'` |
| `ANCHORED_GROUP` | `'myo_anchored'` |
| `SHAPE_PRESETS` | `{'FUSIFORM': (0.35, 0.5, 0.75), 'PARALLEL': (0.0, 0.5, 0.5), 'FAN': (0.15, 0.65, 0.35),...` |
| `FLATNESS_RAMP` | `0.3` |
| `_RAY` | `Vector((0.31, 0.57, 0.76)).normalized()` |
| `_RAYS` | `(_RAY, Vector((-0.83, 0.21, 0.52)).normalized(), Vector((0.17, -0.94, 0.29)).normalized...` |
| `DIAGNOSIS_CONTACT_MM` | `0.05` |
| `PATH_LIFT` | `0.25` |
| `PATH_BEND` | `0.15` |
| `AUTO_PATH_KEY` | `'myo_path_auto'` |

## Functions

### `contour_points(contour_obj)`

World-space points of a contour curve (first spline).

| Parameter | Type | Description |
|---|---|---|
| `contour_obj` | `bpy.types.Object` | Contour curve. |

**Returns** (list of `mathutils.Vector`): Points in order; empty for anything that is not a curve.

### `anchor_weight(t, falloff)`

How free a loft section is to move, from 0 (anchored) to 1 (free).

Sections at the attachments (`t` = 0 or 1) are anchored; the weight rises
smoothly (smoothstep) over `falloff` of the length from each end.

| Parameter | Type | Description |
|---|---|---|
| `t` | float | Position along the loft, 0 (origin) to 1 (insertion). |
| `falloff` | float | Fraction of the length over which the anchoring fades. |

**Returns** (float): 

### `push_out_of_bones(points, bones, clearance, max_depth=None)`

Move points that lie inside a bone to just outside its surface.

Inside/outside is decided by ray parity (`inside_bone`), which needs
a closed bone mesh but not consistent normals (scans often have unreliable
normals). With `max_depth`, a point whose nearest bone surface is
farther than that is left alone: it cannot be a vertex that slipped into
the bone, so the inside test must be wrong (this used to pull vertices
tens of millimetres onto the bone).

| Parameter | Type | Description |
|---|---|---|
| `points` | list | Points to correct in place (`mathutils.Vector`-like with `co` or plain vectors in a list). |
| `bones` | list of `bpy.types.Object` | Bone objects. |
| `clearance` | float | Distance kept from the surface (Blender units). |
| `max_depth` | float | Largest plausible depth inside the bone (Blender units), or None. |

**Returns** (int): Number of points moved.

### `belly_bump(t, peak)`

Belly profile: 0 at both ends, 1 at `peak`, smooth in between.

| Parameter | Type | Description |
|---|---|---|
| `t` | float | Position along the path, 0 (origin) to 1 (insertion). |
| `peak` | float | Position of the maximum, 0 to 1. |

**Returns** (float): 

### `flatness_ramp(t)`

Weight of the flatness setting along the path: 0 at both ends, 1 in the middle.

| Parameter | Type | Description |
|---|---|---|
| `t` | float | Position along the path, 0 to 1. |

**Returns** (float): 

### `curve_tilt(curve_obj, t)`

Tilt (radians) of the path at `t`, interpolated between control points.

Uses the same parameterisation as
`curve_utilities.get_bezier_point_at_parameter`.

| Parameter | Type | Description |
|---|---|---|
| `curve_obj` | `bpy.types.Object` | Muscle path (first spline, Bezier). |
| `t` | float | Parameter along the path, 0 to 1. |

**Returns** (float): 

### `shape_section(points, position, tangent, scale, tilt=0.0, flatness=None, flatness_weight=1.0)`

Place an interpolated section on the path with the muscle-shape profile.

The section's own principal axes in the plane normal to the path (major =
width, minor = thickness) are kept; the section is centred on `position`,
scaled by `scale` and rotated by `tilt` about the tangent. With
`flatness` the thickness is set to `flatness` x width (clamped to a
factor 0.2-5 of the interpolated thickness).

| Parameter | Type | Description |
|---|---|---|
| `points` | list of `mathutils.Vector` | Interpolated section points (world space). |
| `position` | `mathutils.Vector` | Point on the path. |
| `tangent` | `mathutils.Vector` | Path tangent at `position`. |
| `scale` | float | Size factor (curve radius x belly bulge). |
| `tilt` | float | Rotation about the tangent (radians). |
| `flatness` | float or None | Thickness/width ratio, or None to keep the interpolated one. |
| `flatness_weight` | float | 0-1, how much of the flatness change is applied (it fades out towards the attachments, `flatness_ramp`). |

**Returns** (list of `mathutils.Vector`): New section points, same order.

### `build_loft(props, curve_obj, origin_contour, insertion_contour, origin_surface=None, insertion_surface=None, shape=None)`

Loft a muscle belly between two contours, anchored to the attachments.

The first and last sections are exactly the (matched) contour points,
closed by caps draped over the attachment surfaces. Away from the ends the
sections follow the path and the muscle-shape profile (`shape_section`:
curve radius and tilt, belly bulge, flatness), blended in over
`props.anchor_falloff` of the length (`anchor_weight`); smoothing
never touches anchored vertices. This loft is the live preview and the
input of `volume_builder.build_belly`, which makes the final belly.

| Parameter | Type | Description |
|---|---|---|
| `props` | `properties.MyoGeneratorProperties` | Scene settings (`scene.myogen`): connection mode, matching, contour resolution, curve subdivisions, offsets. |
| `curve_obj` | `bpy.types.Object` | Muscle path (needed for `FOLLOW_PATH`). |
| `origin_contour` | `bpy.types.Object` | Origin contour curve. |
| `insertion_contour` | `bpy.types.Object` | Insertion contour curve. |
| `origin_surface` | `bpy.types.Object` | Origin attachment surface, for the draped cap (None: flat cap). |
| `insertion_surface` | `bpy.types.Object` | Insertion attachment surface, for the draped cap. |
| `shape` | str | Muscle shape for the profile (default `props.muscle_shape`); `'NATURAL'` = plain interpolation. |

**Returns** (tuple): `(bm, construction)`: a new bmesh (caller frees it) and a dict with `origin`/`insertion` (matched contour points), `sections` (list of point lists, origin to insertion), `weights` (per vertex, in bmesh order: 0 = anchored, 1 = free; see `anchor_weight`) and `info` (matching diagnostics, see `contour_matching.match_contours`).

**Raises** `ValueError`: If a contour has fewer than 3 points.

### `prepare_contour_loops(props, origin_loop, insertion_loop, n)`

Resample and match the two contours of a loft.

Both contours are resampled to `n` points evenly spaced by arc length.
With `props.contour_matching == 'AUTO'` the insertion contour is
re-indexed by `contour_matching.match_contours`; with `'INDEX'`
points are joined by index as in earlier versions. The manual offsets and
reversals in `props` are applied afterwards as fine-tuning.

| Parameter | Type | Description |
|---|---|---|
| `props` | `properties.MyoGeneratorProperties` | Scene settings (`scene.myogen`). |
| `origin_loop` | sequence of `mathutils.Vector` | Origin contour points. |
| `insertion_loop` | sequence of `mathutils.Vector` | Insertion contour points. |
| `n` | int | Points per contour. |

**Returns** (tuple): `(origin, insertion, info)`: lists of `n` vectors in matched order, and `info` with `mode`, `shift`, `reversed`, `waist` (1 = no hourglass) and `section_area` (mid-section area / end areas; ~0 = folded).

### `describe_match(info)`

One-line summary of a contour match for the panel and the overlay.

| Parameter | Type | Description |
|---|---|---|
| `info` | dict | `info` returned by `prepare_contour_loops`. |

**Returns** (str): 

### `is_twisted(info)`

Whether the matching diagnostics indicate a twisted or hourglass loft.

| Parameter | Type | Description |
|---|---|---|
| `info` | dict | Matching diagnostics. |

**Returns** (bool): 

### `muscle_objects(context, muscle_name=None)`

Collection and objects of the muscle being reconstructed.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `muscle_name` | str | Muscle (default: `scene.myogen.muscle_name`). |

**Returns** (tuple): `(collection, objects)` with `objects` from `myo_record.resolve_objects`; `(None, {})` if the muscle collection does not exist.

### `write_deform_weights(obj, weights)`

Store per-vertex freedom in the `DEFORM_GROUP` vertex group.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Mesh object. |
| `weights` | sequence of float | One weight per vertex (0 = anchored, 1 = free). |

### `bone_targets(props)`

Bones the belly must stay outside of (the origin and insertion bones).

| Parameter | Type | Description |
|---|---|---|
| `props` | `properties.MyoGeneratorProperties` | Scene settings (`scene.myogen`). |

**Returns** (list of `bpy.types.Object`): Distinct mesh objects (may be empty).

### `inside_bone(tree, point)`

True if `point` is inside the closed mesh of `tree` (ray parity).

Parity needs a closed mesh but not consistent normals, which scans often
lack. A single ray that passes exactly through an edge or a vertex counts
that crossing twice and flips the answer, so the majority of three rays
in independent directions (`_RAYS`) decides.

| Parameter | Type | Description |
|---|---|---|
| `tree` | `mathutils.bvhtree.BVHTree` | World-space BVH of the bone (`_bone_tree`). |
| `point` | `mathutils.Vector` | World-space point. |

**Returns** (bool): 

### `outward_sign(surface_obj, bone_obj, samples=200)`

+1 if the attachment's face normals point out of the bone, -1 if into it.

Decided by majority over sampled faces: a point just off each face along
its normal is tested with `inside_bone`.

| Parameter | Type | Description |
|---|---|---|
| `surface_obj` | `bpy.types.Object` | Attachment surface. |
| `bone_obj` | `bpy.types.Object` | Bone it lies on (None: +1). |
| `samples` | int | Faces to test. |

**Returns** (int): 

### `attachment_anchor(surface_obj, bone_obj=None, toward=None)`

Where the muscle path should start on an attachment, outside the bone.

The area centroid of a concave or wrapping attachment (a fossa, a sleeve
around a process) lies inside the bone. The anchor is the point of the
surface nearest to the area centroid moved towards the other attachment
(`toward`) by the surface's RMS size: on a flat patch that is about the
centroid, on a sleeve the face of the process that looks at the other
attachment. The normal is that of the nearest face, oriented out of the
bone (`outward_sign`).

| Parameter | Type | Description |
|---|---|---|
| `surface_obj` | `bpy.types.Object` | Attachment surface. |
| `bone_obj` | `bpy.types.Object` | Bone the attachment lies on (orients the normal). |
| `toward` | `mathutils.Vector` | World position of the other attachment (e.g. its centroid). |

**Returns** (tuple): `(point, normal, size)`: world-space point on the surface, unit outward normal and the RMS distance of the surface from its centroid (Blender units).

### `area_centroid(surface_obj)`

Area-weighted centroid of a surface (world space).

| Parameter | Type | Description |
|---|---|---|
| `surface_obj` | `bpy.types.Object` | Mesh object. |

**Returns** (`mathutils.Vector`): 

### `diagnose(context, preview)`

Self-intersections and bone penetration of the (deformed) preview.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `preview` | `bpy.types.Object` | Preview object. |

**Returns** (dict): `crossing_faces` (faces that intersect another non-adjacent face), `faces`, `inside_bone` (fraction of free vertices inside a bone, by ray parity, deeper than `DIAGNOSIS_CONTACT_MM`; anchored vertices lie on the bone by design and are not counted) and `inside_by_bone` (bone name -> fraction).

### `describe_diagnosis(d)`

One-line summary of `diagnose` for the panel.

| Parameter | Type | Description |
|---|---|---|
| `d` | dict | Output of `diagnose`. |

**Returns** (str): 

### `protect_anchored(obj)`

Mark the vertices lying on the attachments of a final belly.

Creates the `ANCHORED_GROUP` vertex group (from `DEFORM_GROUP` weights
of 0) and a sculpt mask on the same vertices, so sculpting and smoothing
leave them in place.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Final belly (still carrying `DEFORM_GROUP`). |

**Returns** (int): Number of anchored vertices.

### `write_path(collection, muscle_name, points, auto=False)`

Create or replace `<M>_curve`: a Bezier through `points` (AUTO handles, radius 1).

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `points` | sequence of `mathutils.Vector` | World-space points, origin to insertion (≥ 2). |
| `auto` | bool | Mark the path as computed (`AUTO_PATH_KEY`). |

**Returns** (`bpy.types.Object`): The path object.

### `default_path_points(props, origin_surface, insertion_surface)`

Five path points leaving each attachment along its outward normal, outside the bone.

The ends are `attachment_anchor` points (not the centroids, which lie
inside the bone for concave or wrapping attachments), lifted by
`PATH_LIFT` x the attachment size; the 2nd and 4th points bulge along the
normals by `PATH_BEND` x the origin-insertion distance.

| Parameter | Type | Description |
|---|---|---|
| `props` | `properties.MyoGeneratorProperties` | Scene settings (`origin_object`, `insertion_object`). |
| `origin_surface` | `bpy.types.Object` | Origin attachment surface. |
| `insertion_surface` | `bpy.types.Object` | Insertion attachment surface. |

**Returns** (list of `mathutils.Vector`): 
