# `improved_muscle_workflow`

Source: `improved_muscle_workflow.py`

Operators of the muscle creation workflow: preview, path and final mesh.

The work is done in `volume_builder` (belly, live preview) and
`preview` (loft, path geometry); these operators only call it and
report.

## Blender classes

Operators, property groups and panels of this module are listed in [operators](../operators.md) and [properties](../properties.md): `Muscle_Preview_Update_Op`, `Muscle_Preview_Stop_Op`, `Muscle_Edit_Path_Op`, `Muscle_Reset_Path_Op`, `Muscle_Select_Rings_Op`, `Muscle_Reset_Rings_Op`, `Muscle_Mesh_Generation_Op`.
