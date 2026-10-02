# Properties and panels

Data that the extension registers on Blender types, and its UI panels. Generated from the source; do not edit by hand.

## `MyoGeneratorPreferences`

Registered at `context.preferences.addons[__package__].preferences` · `__init__.py`

Add-on preferences: the switch that shows the experimental tools in the panel.

| Name | Type | Default | Description |
|---|---|---|---|
| `show_advanced` | boolean | `False` | **Show Advanced (experimental) features**. Enable experimental features in the MyoGenerator panel |

## `MyoGeneratorProperties`

Registered at `bpy.types.Scene.myogen` · `properties.py`

All MyoGeneratorRemix scene settings, stored under `scene.myogen`.

| Name | Type | Default | Description |
|---|---|---|---|
| `conf_path` | string | `''` | **Path**. Folder where the CSV file is saved |
| `file_name` | string | `''` | **File Name**. CSV file name (without extension) |
| `origin_object` | pointer to `bpy.types.Object` | `''` | **Origin Bone**. Bone on which the origin area is painted (also the reference size for the scale check) |
| `insertion_object` | pointer to `bpy.types.Object` | `''` | **Insertion Bone**. Bone on which the insertion area is painted |
| `muscle_name` | string | `'Insert muscle name'` | **Muscle Name**. Name of the muscle being reconstructed. Use a _left/_right suffix for bilateral muscles (e.g. temp_sup_left) |
| `muscle_curve_subdivisions` | int (min 4, max 100) | `12` | **Curve Subdivisions**. Number of subdivisions along the muscle curve |
| `muscle_contour_resolution` | int (min 4, max 100) | `16` | **Contour Resolution**. Resolution of the contour loops (vertex count) |
| `origin_contour_offset` | int (min 0, max 64) | `0` | **Origin Offset**. Shift origin contour vertices for better alignment |
| `insertion_contour_offset` | int (min 0, max 64) | `0` | **Insertion Offset**. Shift insertion contour vertices for better alignment |
| `origin_reverse_orientation` | boolean | `False` | **Reverse Origin**. Reverse origin contour vertex order |
| `insertion_reverse_orientation` | boolean | `False` | **Reverse Insertion**. Reverse insertion contour vertex order |
| `contour_matching` | enum in ['AUTO', 'INDEX'] | `'AUTO'` | **Contour Matching**. How points of the origin contour are joined to points of the insertion contour |
| `contour_match_info` | string | `''` | **Last contour match**. Summary of the last loft: shift/reversal chosen and waist index (1 = no hourglass) |
| `muscle_connection_mode` | enum in ['FOLLOW_PATH', 'DIRECT_CONNECTION'] | `'FOLLOW_PATH'` | **Connection Mode**. Choose how the muscle loft connects origin and insertion |
| `anchor_falloff` | float (min 0.0, max 0.5) | `0.15` | **Anchored length**. Along the path: fraction of the length, from each attachment, over which the belly keeps the attachment's outline before following the path and the belly settings |
| `muscle_shape` | enum in ['FUSIFORM', 'PARALLEL', 'FAN'] | `'FUSIFORM'` | **Muscle type**. How the belly is built along the path. Fusiform and Parallel: a belly whose section the rings set. Fan: fibres spread over the origin; the rings set the fan's width (X) and thickness (Y). Switching type keeps the path and the rings |
| `belly_bulge` | float (min -0.7, max 1.5) | `0.35` | **Belly**. Along the path: how much thicker (positive) or thinner (negative) the middle is than a straight blend of the two attachments. 0.3 = 30 % larger at its widest point |
| `bulge_position` | float (min 0.05, max 0.95) | `0.5` | **Belly position**. Along the path: where the belly is widest, 0 = at the origin, 1 = at the insertion |
| `flatness` | float (min 0.1, max 1.0) | `0.75` | **Flatness**. Along the path: thickness / width of the cross-section (1 = round, 0.2 = flat). The flat side turns with the curve's Tilt (Ctrl+T in Edit Mode) |
| `use_controls` | boolean | `False` | **Shape with rings**. Put rings on the path to set the size and turn of the belly where you want: they slide along the path. Off: the muscle type's default profile. The rings are kept when off and removed by Generate Final Mesh |
| `ring_count` | int (min 2, max 12) | `3` | **Rings**. Number of rings created along the path (when they are created or reset); the first and last stay at the attachments |
| `attachment_thickness_mm` | float (min 0.0) | `0.0` | **Min. thickness (mm)**. Least thickness of muscle over each attachment surface, so the whole attachment is covered. 0 = automatic (3 voxels) |
| `surface_smoothing_mm` | float (min 0.0) | `1.5` | **Smoothing (mm)**. Rounds off the outer surface over this distance, joining the belly and the attachments smoothly (the face on the bone is never smoothed) |
| `voxel_size_mm` | float (min 0.0) | `0.0` | **Detail (mm)**. Size of the voxels the belly is built from: smaller = finer and slower. The preview uses 1.8 x this. 0 = automatic (about 1/110 of the muscle and at most 1/6 of the thinnest section) |
| `bone_clearance_mm` | float (min 0.0) | `0.1` | **Bone gap (mm)**. Gap kept between the muscle surface and the bones |
| `preview_live` | boolean | `False` | **Live preview**. True while the preview rebuilds itself when a setting, the path or an attachment changes |
| `preview_status` | string | `''` | **Preview status**. Size, resolution and build time of the last preview, and any warning |
| `show_fine_tune` | boolean | `False` | **Show fine-tune**. Show the optional contour offsets and reversals (Blender < 4.1 only; newer versions use a collapsible section) |
| `specific_tension` | float (min 0.0, max 100.0) | `'myo_record.DEFAULT_SPECIFIC_TENSION_N_CM2'` | **Specific Tension (N/cm²)**. Maximum isometric muscle stress used for F = PCSA x tension. 30 N/cm² (0.3 N/mm²) is the usual value; 25 and 37 N/cm² are also used |
| `density_g_cm3` | float (min 0.0) | `'myo_record.DEFAULT_DENSITY_G_CM3'` | **Muscle Density (g/cm³)**. Density used to compute mass from volume |
| `fiber_length_ratio` | float (min 0.05, max 1.0) | `'myo_record.DEFAULT_FIBER_LENGTH_RATIO'` | **Fibre/Muscle Length Ratio**. Fibre length as a fraction of the muscle path length. 1.0 reproduces Herbst et al. (2022); 0.7-0.9 is reported for masticatory muscles |
| `fiber_length_source` | enum in ['PATH', 'BELLY_FIBRES'] | `'PATH'` | **Fibre length from**. Where the fibre length used for the PCSA comes from |
| `pcsa_model` | enum in ['MEAN', 'WEIGHTED'] | `'MEAN'` | **PCSA**. How the belly fibres give the PCSA |
| `belly_fibre_count` | int (min 20, max 1000) | `150` | **Fibres**. Number of belly fibres, spread evenly over the origin attachment |
| `pennation_deg` | float (min 0.0, max 60.0) | `'myo_record.DEFAULT_PENNATION_DEG'` | **Pennation Angle (°)**. Fibre pennation angle; PCSA is multiplied by cos(angle). 0 = parallel fibres |
| `advanced_selected_volume` | float | `0.0` | **Selected Volume**. Last computed total volume of the selected objects (m³) |
| `advanced_selected_mass` | float | `0.0` | **Selected Mass**. Last computed total mass of the selected objects (kg) |
| `advanced_selected_pcsa` | string | `''` | **Selected PCSA**. Read-out of the summed PCSA of the selected objects |
| `show_muscles` | boolean | `True` | **Show Muscles**. Show/hide the muscle bellies |
| `show_attachments` | boolean | `True` | **Show Attachments**. Show/hide origin and insertion surfaces and their contours |
| `show_curves` | boolean | `True` | **Show Curves**. Show/hide the muscle path curves |
| `mirror_axis` | enum in ['X', 'Y', 'Z'] | `'X'` | **Mirror Axis**. World axis across which Mirror Duplicate reflects the selection |
| `scene_qa` | string | `'[]'` | JSON list of [level, message] from the last scene scale/parameter check |
| `show_qa_details` | boolean | `True` | **Show details**. List every finding under each muscle in the QA box |

## Panels

| Panel | Space / region | Category | Label | Module |
|---|---|---|---|---|
| `MYOGENERATOR_PT_panel` | VIEW_3D / UI | MyoGeneratorRemix | MyoGeneratorRemix | `myoGenerator_panel.py` |
