# `cross_section`

Source: `cross_section.py`

Non-destructive cross-section slicing for visual inspection of internal anatomy.

Allows cutting through muscle bellies, bones and other scene meshes using a
transformable wireframe cutter cube in the 3D viewport. The underlying geometry
is never modified; disabling the cut restores all original meshes immediately.

## Constants

| Name | Value |
|---|---|
| `CUTTER_NAME` | `'MyoGen_Cutter'` |
| `MODIFIER_NAME` | `'MyoGen_CrossSection'` |

## Functions

### `best_solver(obj, preferred='AUTO')`

Determine the most appropriate Boolean solver for a target object.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | The target mesh object. |
| `preferred` | str | Preferred solver ('AUTO' or 'EXACT'). |

**Returns** (str): Solver identifier supported by Blender ('MANIFOLD', 'FLOAT', 'FAST', or 'EXACT').

### `find_cutter(context=None)`

Find the existing cross-section cutter object in the scene.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` or None | Blender context. |

**Returns** (`bpy.types.Object` or None): The cutter object, or None if not present.

### `ensure_cutter(context)`

Ensure the cross-section cutter cube exists, is linked and styled.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Blender context. |

**Returns** (`bpy.types.Object`): The cutter object.

### `get_target_objects(context, scope='SCENE')`

Retrieve all mesh objects that should participate in the cross-section cut.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Blender context. |
| `scope` | str | Target scope ('SCENE', 'MUSCLES_BONES', 'MUSCLES', or 'ACTIVE'). |

**Returns** (list of `bpy.types.Object`): List of target mesh objects.

### `compute_bounds(objects)`

Compute the combined axis-aligned world bounding box for a set of objects.

| Parameter | Type | Description |
|---|---|---|
| `objects` | sequence of `bpy.types.Object` | Sequence of Blender objects. |

**Returns** (tuple): Tuple of `(center, dimensions, min_corner, max_corner)`.

### `fit_cutter(context, alignment='TRANSVERSE', scope='SCENE')`

Position and scale the cutter cube according to an anatomical plane or target.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Blender context. |
| `alignment` | str | Plane alignment ('TRANSVERSE', 'SAGITTAL', 'CORONAL', 'ACTIVE', or 'FIT_ALL'). |
| `scope` | str | Target scope to measure bounds from if not 'ACTIVE'. |

### `flip_cutter(context)`

Invert the cutting side of the cutter cube relative to scene bounds.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Blender context. |

### `apply_cut(context)`

Apply or update the non-destructive Boolean modifier on all target meshes.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Blender context. |

**Returns** (int): Number of objects affected.

### `remove_cut(context)`

Remove the cross-section Boolean modifier from all scene meshes and hide cutter.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Blender context. |

**Returns** (int): Number of modifiers removed.

### `on_cut_toggled(context)`

Property update callback when `section_cut_active` is toggled.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Blender context. |
| `self` | `bpy.types.PropertyGroup` | Property group. |

### `on_cut_changed(context)`

Property update callback when cutting parameters change.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Blender context. |
| `self` | `bpy.types.PropertyGroup` | Property group. |

## Blender classes

Operators, property groups and panels of this module are listed in [operators](../operators.md) and [properties](../properties.md): `MYOGEN_OT_toggle_section_cut`, `MYOGEN_OT_align_section_cut`, `MYOGEN_OT_flip_section_cut`, `MYOGEN_OT_refresh_section_cut`, `MYOGEN_OT_select_cutter`, `MYOGENERATOR_PT_cross_section`.
