# `volume_builder`

Source: `volume_builder.py`

Solid muscle belly: (tube or fibres along the path ∪ attachment layers) − bones.

The belly follows the user's path `<M>_curve`: a tube (`tube`) sized
and turned by the section rings on the path (`rings`) or by the muscle
type's profile, or, for fan-shaped muscles, the union of fibres from the
whole origin attachment to the insertion (`fan`). Built on a voxel
grid, so it is always closed, lies on the outer face of the bones and never
crosses itself:

1. occupancy of the tube by +Z scanlines (winding number: overlapping parts
   are a union) or of the fibres (capsules), Gaussian-smoothed;
2. a layer over each attachment, up to the minimum thickness outwards from
   its bone (`attachment_layer`), so the whole attachment is covered;
3. minus the origin and insertion bones (ray parity);
4. surface nets + voxel remesh (closed, manifold);
5. vertices next to an attachment are snapped onto it and anchored
   (weight 0 in `preview.DEFORM_GROUP`); the rest are smoothed and kept
   outside the bones.

The live preview (`start_live`) is this belly at draft resolution; a
wire tube (`<M>_tube`) follows the path and the rings at once and the
solid follows after `LIVE_DELAY` s.

## Constants

| Name | Value |
|---|---|
| `AUTO_VOXELS_ACROSS` | `110` |
| `MAX_VOXELS_ACROSS` | `400` |
| `VOXELS_PER_RADIUS` | `6.0` |
| `VOXELS_PER_FIBRE_RADIUS` | `3.0` |
| `MAX_CELLS` | `8000000` |
| `AUTO_THICKNESS_VOXELS` | `3.0` |
| `SIDE_MIN_COS` | `0.0` |
| `SMOOTH_PASSES` | `3` |
| `LAYER_CONE_COS` | `0.5` |
| `REMESH_FACTOR` | `0.75` |
| `MAX_PUSH_VOXELS` | `3.0` |
| `SNAP_VOXELS` | `1.0` |
| `_UP` | `Vector((0.0, 0.0, 1.0))` |
| `_CORNERS` | `[(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]` |
| `_EDGES` | `[(a, b) for a in range(8) for b in range(a + 1, 8) if sum((x != y for x, y in zip(_CORN...` |
| `FAN_SHAPES` | `{'FAN'}` |
| `PREVIEW_SUFFIX` | `'_preview'` |
| `TUBE_SUFFIX` | `'_tube'` |
| `DRAFT_VOXEL_SCALE` | `1.8` |
| `LIVE_DELAY` | `0.6` |
| `WIRE_FIBRES` | `40` |
| `TUBE_DELAY` | `0.02` |

## Functions

### `occupancy(tree, xs, ys, zs, z_start, signed, columns=None)`

Voxel occupancy of a closed mesh by +Z scanlines.

| Parameter | Type | Description |
|---|---|---|
| `tree` | `mathutils.bvhtree.BVHTree` | World-space BVH of the mesh. |
| `xs` | `numpy.ndarray` | Voxel-centre X coordinates. |
| `ys` | `numpy.ndarray` | Voxel-centre Y coordinates. |
| `zs` | `numpy.ndarray` | Voxel-centre Z coordinates (ascending). |
| `z_start` | float | Z where rays start; must be below the mesh (outside it). |
| `signed` | bool | True: inside = positive winding number (needs consistent outward normals; overlapping parts are a union). False: ray parity (needs a closed mesh only). |
| `columns` | `numpy.ndarray` | Optional boolean (len(xs), len(ys)) mask of columns to test. |

**Returns** (`numpy.ndarray`): Boolean array (len(xs), len(ys), len(zs)).

### `attachment_layer(surface_obj, bone_obj, thickness, xs, ys, zs)`

Voxels of the muscle layer over an attachment, up to `thickness` outwards.

A voxel belongs to the layer when its nearest point on the attachment is
closer than `thickness` and it lies on the outer side of the surface
(within `LAYER_CONE_COS` of the outward normal there) or within one voxel
of it. Unlike offsetting the surface as a mesh, this never folds, however
thick the layer or rough the scanned surface; the edges stay at the
attachment's border instead of spreading sideways.

| Parameter | Type | Description |
|---|---|---|
| `surface_obj` | `bpy.types.Object` | Attachment surface. |
| `bone_obj` | `bpy.types.Object` | Bone it lies on (orients the normals, `preview.outward_sign`). |
| `thickness` | float | Layer thickness (Blender units). |
| `xs` | `numpy.ndarray` | Voxel-centre X coordinates (evenly spaced). |
| `ys` | `numpy.ndarray` | Voxel-centre Y coordinates. |
| `zs` | `numpy.ndarray` | Voxel-centre Z coordinates. |

**Returns** (`numpy.ndarray`): Boolean array (len(xs), len(ys), len(zs)).

### `smoothing_passes(sigma, voxel)`

Box-blur passes giving a Gaussian of standard deviation `sigma`.

| Parameter | Type | Description |
|---|---|---|
| `sigma` | float | Standard deviation (same unit as `voxel`). |
| `voxel` | float | Grid spacing. |

**Returns** (int): 

### `blur(field)`

3-tap box blur along each axis (zero outside).

| Parameter | Type | Description |
|---|---|---|
| `field` | `numpy.ndarray` | Scalar grid. |

**Returns** (`numpy.ndarray`): Blurred grid, same shape.

### `surface_nets(field, iso, origin, voxel)`

Quad mesh of the iso-surface of a scalar grid (naive surface nets).

One vertex per cell crossed by the surface, at the mean of the edge
crossings; one quad per grid edge crossing the surface, oriented outwards
(from values above `iso` to below). The field must be below `iso` on
its border.

| Parameter | Type | Description |
|---|---|---|
| `field` | `numpy.ndarray` | Values at grid points, shape (X, Y, Z). |
| `iso` | float | Iso-value; inside is `field > iso`. |
| `origin` | sequence of 3 float | World position of grid point (0, 0, 0). |
| `voxel` | float | Grid spacing. |

**Returns** (tuple): `(verts, quads)`: (N, 3) float and (M, 4) int arrays.

### `manifold_remesh(verts, quads, voxel)`

Closed manifold mesh from surface-nets output (OpenVDB voxel remesh).

Surface nets can leave a few non-manifold edges where the field is
ambiguous (sharp bone edges); Blender's voxel remesher rebuilds the
surface from its level set, which is always manifold.

| Parameter | Type | Description |
|---|---|---|
| `verts` | `numpy.ndarray` | (N, 3) vertex positions. |
| `quads` | `numpy.ndarray` | (M, 4) quad indices. |
| `voxel` | float | Remesh voxel size. |

**Returns** (`bmesh.types.BMesh`): New bmesh (caller frees it).

### `is_fan(props)`

True if the current muscle type is built from fibres (fan-shaped muscles).

| Parameter | Type | Description |
|---|---|---|
| `props` | `properties.MyoGeneratorProperties` | Scene settings. |

**Returns** (bool): 

### `build_belly(context, tube_bm, origin_surface, insertion_surface, bones, report=None, fibres=None, voxel_scale=1.0, min_radius=None)`

Solid belly from the tube or the fibres, the attachments and the bones.

Body = the tube along the muscle path (`tube.path_tube`) or, for fan
muscles, the fibres from the origin to the insertion (`fan.fibres`,
rasterised by `fan.occupancy`). The body is smoothed by
`surface_smoothing_mm` **before** the bones are cut (so the face on the
bone stays exact), joined to a layer over each attachment
(`attachment_layer`), and the bones are subtracted.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context (scene settings `scene.myogen`; unit scale). |
| `tube_bm` | `bmesh.types.BMesh` | World-space tube along the path, or None when `fibres` is given; not freed. |
| `origin_surface` | `bpy.types.Object` | Origin attachment surface. |
| `insertion_surface` | `bpy.types.Object` | Insertion attachment surface. |
| `bones` | sequence of `bpy.types.Object` | `(origin_bone, insertion_bone)`; None entries are skipped. |
| `report` | dict | Optional dict filled with `voxel` (BU), `grid`, `seconds`, `anchored`, `islands_removed`, `pieces` (kept disconnected parts) and `stages` (seconds per stage). |
| `fibres` | tuple | `(courses, radii)` from `fan.fibres`, or None. |
| `voxel_scale` | float | Multiplies the voxel size (> 1 = faster draft). |
| `min_radius` | float | Smallest section radius (Blender units): the automatic voxel is at most `min_radius / VOXELS_PER_RADIUS`, so thin muscles keep their detail. |

**Returns** (tuple): `(bm, weights)`: world-space bmesh (caller frees it) and per vertex weights (0 = anchored on an attachment, 1 = free).

**Raises** `ValueError`: If an attachment is missing or the solid is empty.

### `ensure_path(context, muscle_name, coll, objs)`

The muscle path `<M>_curve`; the default one is created when missing.

The path is the user's: it is never rewritten here (see the *Reset Path*
operator).

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `muscle_name` | str | Muscle name. |
| `coll` | `bpy.types.Collection` | Muscle collection. |
| `objs` | dict | Muscle objects (`preview.muscle_objects`). |

**Returns** (`bpy.types.Object`): 

### `muscle_sections(context, muscle_name, coll, objs, path, points)`

Sections of the belly along the path: from the rings, or the type's default profile.

With *Shape with rings* on, the rings are created when missing: for a
belly from the type's profile (`tube.default_profile`), for a fan
from its natural width, thickness and orientation (`fan.fibres`).

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `muscle_name` | str | Muscle name. |
| `coll` | `bpy.types.Collection` | Muscle collection. |
| `objs` | dict | Muscle objects. |
| `path` | `bpy.types.Object` | The muscle path. |
| `points` | list of `mathutils.Vector` | Arc-length samples of the path. |

**Returns** (tuple): `(sections, rings)`; `sections` is None for a fan without rings (natural fan); `rings` is empty when rings are off.

### `natural_fan_sections(context, objs, points)`

Ring sections `(u, half_width, half_thickness, angle)` of the natural fan.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context (`scene.myogen`: bones, ring count). |
| `objs` | dict | Muscle objects (attachments). |
| `points` | list of `mathutils.Vector` | Arc-length samples of the path. |

**Returns** (list of tuple): 

### `solid_mesh(context, muscle_name, report=None, voxel_scale=1.0)`

Build the solid belly of a muscle into a new mesh datablock (world space).

Body = the tube along the path (`tube.path_tube`, sections from the
rings or the type's profile) or, for fan muscles, the fibres from the
origin to the insertion (`fan.fibres`). The rings are put back
perpendicular to the path afterwards.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `muscle_name` | str | Muscle (collection `muscles/<muscle_name>`). |
| `report` | dict | Optional dict, see `build_belly`. |
| `voxel_scale` | float | See `build_belly`; > 1 also uses fewer fibres. |

**Returns** (tuple): `(mesh, weights)`.

**Raises** `ValueError`: If the muscle or its inputs are missing, or the solid is empty.

### `update_tube(context, muscle_name)`

Rewrite the wire `<M>_tube` from the current path and rings (instant feedback).

A belly shows its tube; a fan shows a subset of its fibres (their courses).

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `muscle_name` | str | Muscle name. |

**Returns** (`bpy.types.Object`): The tube object.

**Raises** `ValueError`: See `solid_mesh`.

### `update_preview(context, muscle_name, report=None)`

Create or replace `<M>_preview`: the solid belly at draft resolution.

The preview *is* the final shape, only coarser (`DRAFT_VOXEL_SCALE`).

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `muscle_name` | str | Muscle name. |
| `report` | dict | Optional dict, see `build_belly`; `object` is added. |

**Returns** (`bpy.types.Object`): The preview object.

**Raises** `ValueError`: See `solid_mesh`.

### `remove_preview(muscle_name)`

Delete `<M>_preview` and the wire tube if they exist.

| Parameter | Type | Description |
|---|---|---|
| `muscle_name` | str | Muscle name. |

### `generate_final(context, muscle_name)`

Build the final belly `<M>_muscle` at full resolution.

Replaces an existing belly, removes the construction helpers (preview,
wire tube and rings) and writes the anchored vertex group and sculpt mask
(`preview.protect_anchored`). The path `<M>_curve` is kept: it is
the muscle path used for the measurements.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `muscle_name` | str | Muscle name. |

**Returns** (tuple): `(belly, report)`; `report["anchored_count"]` is added.

**Raises** `ValueError`: See `solid_mesh`.

### `describe_report(context, report)`

One-line summary of a `build_belly` report for the panel.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context (unit scale). |
| `report` | dict | Report dict (with `object`). |

**Returns** (str): 

### `on_controls_toggled(context)`

*Shape with rings* switched: create or show the rings (on), hide them (off), and rebuild.

The rings are kept when switched off, with their positions and sizes.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `self` | `properties.MyoGeneratorProperties` | Scene settings (`scene.myogen`). |

### `start_live(context)`

Build the preview and keep it updated while the path, the rings, the
settings or the attachments change.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |

**Returns** (`bpy.types.Object`): The preview object.

**Raises** `ValueError`: See `solid_mesh`.

### `stop_live(context)`

Stop updating the preview (the object is kept).

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |

### `schedule_rebuild(context)`

Refresh the wire tube now and rebuild the live preview after `LIVE_DELAY` s
without further changes.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |

### `on_setting_changed(context)`

Update callback of every belly setting: schedule a live rebuild.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `self` | `properties.MyoGeneratorProperties` | Scene settings (`scene.myogen`). |

### `on_shape_changed(context)`

Muscle type changed: rebuild the live preview (Fan builds the belly from fibres).

The path and the rings are kept; *Reset Rings* sizes the rings with the
new type's profile.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `self` | `properties.MyoGeneratorProperties` | Scene settings (`scene.myogen`). |

### `flush_live(context)`

Run a pending live rebuild now (tests; before generating).

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |

**Returns** (bool): True if a rebuild ran.
