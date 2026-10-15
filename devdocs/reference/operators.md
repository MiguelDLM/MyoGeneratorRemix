# Operators

All operators of MyoGeneratorRemix, as callable from Python. Generated from the source; do not edit by hand.

## `core_operators`

### `bpy.ops.myogen.submit_muscle()`

**Submit Muscle Name** — Submit Muscle Name

Submit muscle name and create collection

class `Muscle_Name_Submition` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.estimate_selected_volumes()`

**Estimate Selected Volumes** — Estimate the total volume, mass and PCSA of the selected mesh objects

Estimate summed volume of selected mesh objects

class `Estimate_Selected_Volumes_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.mirror_duplicate(axis='X')`

**Mirror Duplicate** — Duplicate the selected objects mirrored across the chosen axis. Objects of a muscle named *_left/*_right go to the opposite-side muscle collection, which is created if needed

Duplicate selected objects mirrored across chosen axis (X/Y/Z)

class `MYOGENERATOR_OT_mirror_duplicate` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `axis` | enum in ['X', 'Y', 'Z'] | `'X'` | **Axis**. Axis to mirror across |

### `bpy.ops.myogen.select_origin()`

**Select Origin** — Select Origin of the muscle

Select origin faces

class `Select_Origin_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.select_insertion()`

**Select Insertion** — Select Insertion of the muscle

Select insertion faces

class `Select_Insertion_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.submit_origin()`

**Submit Origin** — Submit Origin of the muscle

Submit origin selection

class `Submit_Origin_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}` · poll: `return context.object is not None and context.object.mode == 'EDIT'`

_No parameters._

### `bpy.ops.myogen.submit_insertion()`

**Submit Insertion** — Submit Insertion of the muscle

Submit insertion selection

class `Submit_Insertion_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}` · poll: `return context.object is not None and context.object.mode == 'EDIT'`

_No parameters._

### `bpy.ops.myogen.next_muscle()`

**Next Muscle** — Start the creation of the next muscle

Move to next muscle

class `Next_Muscle_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.create_ligament_material()`

**Create Ligament Material** — Create the procedural ligament material with dense collagen striations and subsurface scattering so it can be assigned to other elements

Create or get the procedural ligament material in the scene

class `Create_Ligament_Material_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.recall_attachment(role='origin')`

**Edit Attachment Faces** — Select the faces on the bone that currently form this attachment, allowing you to add or remove faces before re-submitting

Select the attachment faces on the bone in Edit Mode to allow adjustments

class `Recall_Attachment_Faces_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `role` | string | `'origin'` | **Attachment Role**. Attachment to edit ('origin' or 'insertion') |

### `bpy.ops.myogen.rename_muscle(muscle='', new_name='')`

**Rename Muscle** — Rename the current muscle and all its associated objects, collection and metadata

Rename the current muscle, its collection, objects and records

class `Rename_Muscle_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `muscle` | string | `''` | **Target Muscle**. Name of the muscle to rename (empty for active muscle) |
| `new_name` | string | `''` | **New Name**. New name for the muscle (use _left/_right for bilateral muscles) |

### `bpy.ops.myogen.delete_muscle(muscle='')`

**Delete Muscle** — Delete the current muscle collection, its objects and construction helpers

Delete the current muscle collection and its objects

class `Delete_Muscle_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `muscle` | string | `''` | **Target Muscle**. Name of the muscle to delete (empty for active muscle) |

### `bpy.ops.myogen.select_muscle(name='')`

**Select Muscle** — Set this muscle as the active muscle in MyoGenerator

Select and activate a muscle for editing

class `Select_Muscle_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | string | `''` | **Muscle**. Name of the muscle collection to activate |

### `bpy.ops.myogen.select_muscle_menu(muscle='...')`

**Select Muscle** — Select an existing muscle to view or edit

Select a muscle from the list of existing muscles

class `Select_Muscle_Menu_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `muscle` | enum | `''` | **Muscle**. Existing muscles in the scene |

### `bpy.ops.myogen.check_muscles()`

**Check Muscles** — Measure every muscle, store the results in the muscle records and flag implausible scales, volumes, lengths or parameters

Run the plausibility checks without exporting

class `Check_Muscles_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.trace_fibres()`

**Trace Fibres** — Trace the fibres of every finished belly (seeding and number as set), measure the muscles with them as Check Muscles does, and show the fibres (detours in magenta)

Trace the belly fibres of every muscle and show them

class `Trace_Fibres_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}` · poll: `return context.scene.myogen.fiber_length_source == 'BELLY_FIBRES'`

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

class `Calculate_Muscle_Parameters_Op` · `core_operators.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

## `improved_muscle_workflow`

### `bpy.ops.myogen.muscle_preview_update()`

**Start Preview** — Build the belly as it will be generated, at draft resolution, along the muscle path, and keep it updated while you edit the path, the rings or the settings

Start the live preview of the muscle belly

class `Muscle_Preview_Update_Op` · `improved_muscle_workflow.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.muscle_preview_discard()`

**Discard Preview** — Stop the live preview and delete the preview mesh, e.g. to redo an attachment. The path and the rings (hidden) are kept: Start Preview brings the same shape back

Discard the live preview

class `Muscle_Preview_Discard_Op` · `improved_muscle_workflow.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.edit_path()`

**Edit Path** — Select the muscle path and enter Edit Mode: move its points and handles to set the course of the belly. The preview and the rings follow

Edit the muscle path in Edit Mode

class `Muscle_Edit_Path_Op` · `improved_muscle_workflow.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.reset_path()`

**Reset Path** — Replace the muscle path with the default one: from each attachment along its outward normal, outside the bone

Replace the path with the default one

class `Muscle_Reset_Path_Op` · `improved_muscle_workflow.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

### `bpy.ops.myogen.select_rings()`

**Select Rings** — Select the rings on the path. Click one: G slides it along the path, S sizes the section (S X X width, S Y Y thickness), R turns it

Select the section rings

class `Muscle_Select_Rings_Op` · `improved_muscle_workflow.py` · options `{'REGISTER', 'UNDO'}` · poll: `return context.scene.myogen.use_controls`

_No parameters._

### `bpy.ops.myogen.reset_rings()`

**Reset Rings** — Replace the rings with the number set below, evenly spaced along the path and showing the muscle's natural shape (no change)

Replace the rings with evenly spaced default ones

class `Muscle_Reset_Rings_Op` · `improved_muscle_workflow.py` · options `{'REGISTER', 'UNDO'}` · poll: `return context.scene.myogen.use_controls`

_No parameters._

### `bpy.ops.myogen.muscle_mesh_generation()`

**Generate Final Mesh** — Build <muscle>_muscle at full resolution with the current path, rings and settings, and remove the construction helpers (preview, wire tube, rings); the path is kept for the measurements. Replaces an earlier final mesh

Generate the final muscle mesh

class `Muscle_Mesh_Generation_Op` · `improved_muscle_workflow.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._

## `myoGenerator_panel`

### `bpy.ops.myogen.qa_finding(message='...', level='...')`

**QA Finding** — QA finding

One QA finding: hover for the full text, click to print it

class `MYOGEN_OT_qa_finding` · `myoGenerator_panel.py` · options `{'INTERNAL'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | string | `''` | **Message**. Full text of the finding |
| `level` | string | `''` | **Level**. Finding level (OK, INFO, WARNING, ERROR) |

## `visibility`

### `bpy.ops.myogen.toggle_kind(kind='...')`

**Toggle Type** — Show or hide this type of object in every muscle (hide if any is visible)

Show or hide one type of object in every muscle

class `MYOGEN_OT_toggle_kind` · `visibility.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `kind` | enum | `''` | **Type**. Type of object |

### `bpy.ops.myogen.solo_kind(kind='...')`

**Show Only Type** — Show this type of object in every muscle and hide every other MyoGen object

Show only one type of object in every muscle

class `MYOGEN_OT_solo_kind` · `visibility.py` · options `{'REGISTER', 'UNDO'}`

| Name | Type | Default | Description |
|---|---|---|---|
| `kind` | enum | `''` | **Type**. Type of object |

### `bpy.ops.myogen.show_all_kinds()`

**Show All** — Show every MyoGen object of every muscle (also the fibres, hidden when written)

Show every MyoGen object

class `MYOGEN_OT_show_all_kinds` · `visibility.py` · options `{'REGISTER', 'UNDO'}`

_No parameters._
