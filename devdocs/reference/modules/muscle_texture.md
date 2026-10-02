# `muscle_texture`

Source: `muscle_texture.py`

Procedural muscle material applied to the final belly mesh (visual only).

Node set-up after Ned Poreyra (https://www.artstation.com/artwork/Rb8LO).

## Constants

| Name | Value |
|---|---|
| `FIBRE_MATERIAL` | `'Muscle (fibres)'` |
| `FIBRES_PER_LENGTH` | `110.0` |
| `FIBRE_ELONGATION` | `9.0` |
| `STRIATIONS_PER_BUNDLE` | `4.0` |
| `STRIATION_DISTORTION` | `0.4` |
| `STRIATION_CONTRAST` | `0.25` |
| `FIBRE_BUMP_MM` | `0.25` |

## Functions

### `create_muscle_material()`

Create or get the procedural muscle material based on the method described by Ned Poreyra (https://www.artstation.com/artwork/Rb8LO)
Returns the material object, creating it only if it doesn't exist.


### `create_fibre_material(scene)`

Get or create the muscle material oriented by the fibre coordinates.

Reads the `myo_fibre` point attribute (phase, along, depth; see
`fibre_texture`): elongated fibre bundles (Voronoi cells stretched
along the fibres), fine striations along each fibre (bands of the phase,
slightly distorted), a bump from both, and a pale tendon tint at both
ends from `myo_fibre_u`.

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
