# `core_operators`

Source: `core_operators.py`

Core operators for the MyoGeneratorRemix addon.
Contains essential operators that support the old workflow interface.

## Constants

| Name | Value |
|---|---|
| `_SIDE_SWAP` | `(('_left', '_right'), ('_right', '_left'), ('_l', '_r'), ('_r', '_l'))` |

## Functions

### `create_mesh_from_selected_faces(operator, mesh_name)`

Turn the faces selected on a bone into an attachment surface and its contour.

Creates `<M>_<mesh_name>` (the faces, world space, `myo_role` =
`mesh_name`) and `<M>_<mesh_name>_contour` (its boundary as a closed
curve, role `<mesh_name>_contour`) inside `muscles/<M>`, where `M` is
`scene.myogen.muscle_name`.

| Parameter | Type | Description |
|---|---|---|
| `operator` | `bpy.types.Operator` | Calling operator (for reports). |
| `mesh_name` | str | `'origin'` or `'insertion'`. |

## Blender classes

Operators, property groups and panels of this module are listed in [operators](../operators.md) and [properties](../properties.md): `Muscle_Name_Submition`, `Estimate_Selected_Volumes_Op`, `MYOGENERATOR_OT_mirror_duplicate`, `Select_Origin_Op`, `Select_Insertion_Op`, `Submit_Origin_Op`, `Submit_Insertion_Op`, `Next_Muscle_Op`, `Check_Muscles_Op`, `Show_Belly_Fibres_Op`, `Set_Unit_Scale_Op`, `Calculate_Muscle_Parameters_Op`.
