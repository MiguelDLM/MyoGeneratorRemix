# `muscle_texture`

Source: `muscle_texture.py`

Procedural muscle material applied to the final belly mesh (visual only).

Node set-up after Ned Poreyra (https://www.artstation.com/artwork/Rb8LO).

## Functions

### `create_muscle_material()`

Create or get the procedural muscle material based on the method described by Ned Poreyra (https://www.artstation.com/artwork/Rb8LO)
Returns the material object, creating it only if it doesn't exist.


### `apply_muscle_material(mesh_obj)`

Assign the muscle material to a mesh, creating the material if needed.

| Parameter | Type | Description |
|---|---|---|
| `mesh_obj` | `bpy.types.Object` | Muscle belly. |

**Returns** (bool): True on success.
