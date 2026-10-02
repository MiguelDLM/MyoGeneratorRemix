# Operators

All operators of MyoGeneratorRemix, as callable from Python. Generated from the source; do not edit by hand.

## `core_operators`

### `bpy.ops.myogen.submit_muscle()`

**Submit Muscle Name** — Submit Muscle Name

Submit muscle name and create collection

class `Muscle_Name_Submition` · `core_operators.py`

_No parameters._

### `bpy.ops.myogen.estimate_selected_volumes()`

**Estimate Selected Volumes** — Estimate the total volume, mass and PCSA of the selected mesh objects

Estimate summed volume of selected mesh objects

class `Estimate_Selected_Volumes_Op` · `core_operators.py`

_No parameters._

### `bpy.ops.myogen.mirror_duplicate(axis='X')`

**Mirror Duplicate** — Duplicate the selected objects mirrored across the chosen axis. Objects of a muscle named *_left/*_right go to the opposite-side muscle collection, which is created if needed

Duplicate selected objects mirrored across chosen axis (X/Y/Z)

class `MYOGENERATOR_OT_mirror_duplicate` · `core_operators.py`

| Name | Type | Default | Description |
|---|---|---|---|
| `axis` | enum in ['X', 'Y', 'Z'] | `'X'` | **Axis**. Axis to mirror across |

### `bpy.ops.myogen.select_origin()`

**Select Origin** — Select Origin of the muscle

Select origin faces

class `Select_Origin_Op` · `core_operators.py`

_No parameters._

### `bpy.ops.myogen.select_insertion()`

**Select Insertion** — Select Insertion of the muscle

Select insertion faces

class `Select_Insertion_Op` · `core_operators.py`

_No parameters._

### `bpy.ops.myogen.submit_origin()`

**Submit Origin** — Submit Origin of the muscle

Submit origin selection

class `Submit_Origin_Op` · `core_operators.py` · poll: `return context.object is not None and context.object.mode == 'EDIT'`

_No parameters._

### `bpy.ops.myogen.submit_insertion()`

**Submit Insertion** — Submit Insertion of the muscle

Submit insertion selection

class `Submit_Insertion_Op` · `core_operators.py` · poll: `return context.object is not None and context.object.mode == 'EDIT'`

_No parameters._

### `bpy.ops.myogen.next_muscle()`

**Next Muscle** — Start the creation of the next muscle

Move to next muscle

class `Next_Muscle_Op` · `core_operators.py`

_No parameters._

### `bpy.ops.myogen.check_muscles()`

**Check Muscles** — Measure every muscle, store the results in the muscle records and flag implausible scales, volumes, lengths or parameters

Run the plausibility checks without exporting

class `Check_Muscles_Op` · `core_operators.py`

_No parameters._

### `bpy.ops.myogen.set_unit_scale(unit='MILLIMETERS')`

**Set Unit Scale** — Declare what one Blender unit is in the real specimen

Set the scene unit scale

class `Set_Unit_Scale_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `unit` | enum in ['MILLIMETERS', 'CENTIMETERS', 'METERS'] | `'MILLIMETERS'` | **1 Blender unit =**. Real length of one Blender unit in the specimen model |

### `bpy.ops.myogen.calculate_muscle_parameters()`

**Calculate Muscle Parameters** — Measure every muscle (volume, mass, lengths, areas, PCSA, force), store the muscle records in the .blend and export them to CSV

Calculate muscle parameters and save to CSV

class `Calculate_Muscle_Parameters_Op` · `core_operators.py`

_No parameters._

## `improved_muscle_workflow`

### `bpy.ops.myogen.muscle_preview_update()`

**Start Preview** — Build the belly as it will be generated, at draft resolution, along the muscle path, and keep it updated while you edit the path, the rings or the settings

Start the live preview of the muscle belly

class `Muscle_Preview_Update_Op` · `improved_muscle_workflow.py`

_No parameters._

### `bpy.ops.myogen.muscle_preview_stop()`

**Stop Preview** — Stop rebuilding the preview on changes; the preview mesh is kept

Stop updating the preview

class `Muscle_Preview_Stop_Op` · `improved_muscle_workflow.py`

_No parameters._

### `bpy.ops.myogen.edit_path()`

**Edit Path** — Select the muscle path and enter Edit Mode: move its points and handles to set the course of the belly. The preview and the rings follow

Edit the muscle path in Edit Mode

class `Muscle_Edit_Path_Op` · `improved_muscle_workflow.py`

_No parameters._

### `bpy.ops.myogen.reset_path()`

**Reset Path** — Replace the muscle path with the default one: from each attachment along its outward normal, outside the bone

Replace the path with the default one

class `Muscle_Reset_Path_Op` · `improved_muscle_workflow.py`

_No parameters._

### `bpy.ops.myogen.select_rings()`

**Select Rings** — Select the rings on the path. Click one: G slides it along the path, S sizes the section (S X X width, S Y Y thickness), R turns it

Select the section rings

class `Muscle_Select_Rings_Op` · `improved_muscle_workflow.py` · poll: `return context.scene.myogen.use_controls`

_No parameters._

### `bpy.ops.myogen.reset_rings()`

**Reset Rings** — Replace the rings with the number set below, evenly spaced along the path and sized by the muscle type

Replace the rings with evenly spaced default ones

class `Muscle_Reset_Rings_Op` · `improved_muscle_workflow.py` · poll: `return context.scene.myogen.use_controls`

_No parameters._

### `bpy.ops.myogen.muscle_mesh_generation()`

**Generate Final Mesh** — Build <muscle>_muscle at full resolution with the current path, rings and settings, and remove the construction helpers (preview, wire tube, rings); the path is kept for the measurements. Replaces an earlier final mesh

Generate the final muscle mesh

class `Muscle_Mesh_Generation_Op` · `improved_muscle_workflow.py`

_No parameters._
