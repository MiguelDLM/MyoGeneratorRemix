# `muscle_texture`

Source: `muscle_texture.py`

Procedural muscle material applied to the final belly mesh (visual only).

Node set-up after Ned Poreyra (https://www.artstation.com/artwork/Rb8LO).

## Constants

| Name | Value |
|---|---|
| `FIBRE_MATERIAL` | `'Muscle (fibres)'` |
| `FIBRE_MATERIAL_VERSION` | `3` |
| `BUMP_MM` | `4.0` |

## Functions

### `create_muscle_material()`

Create or get the procedural muscle material based on the method described by Ned Poreyra (https://www.artstation.com/artwork/Rb8LO)
Returns the material object, creating it only if it doesn't exist.


### `create_fibre_material(scene)`

Get or create the muscle material laid out along the fibres.

The node set-up of `create_muscle_material` (Ned Poreyra's), with
two inputs replaced:

* its texture coordinates come from the `myo_fibre` point attribute
  (along the muscle, across its fibres, through its thickness, each
  normalised 0-1 like the object coordinates it replaces; see
  `fibre_texture`) instead of the object's generated coordinates,
  so the bundles follow the fibre arrangement;
* the pale tendon colour comes from the `myo_tendon` point attribute
  (0-1), whose extent at each end is set per belly, instead of a fixed
  band at both ends of the object's X axis;
* the relief depth comes from the `myo_bump` point attribute (a fraction
  of the bundle size), so it suits muscles of any size and unit.

| Parameter | Type | Description |
|---|---|---|
| `scene` | `bpy.types.Scene` | Scene (its unit scale sets the bump distance). |

**Returns** (`bpy.types.Material`): 

### `apply_muscle_material(mesh_obj)`

Assign the muscle material to a mesh, creating the material if needed.

| Parameter | Type | Description |
|---|---|---|
| `mesh_obj` | `bpy.types.Object` | Muscle belly. |

**Returns** (bool): True on success.
