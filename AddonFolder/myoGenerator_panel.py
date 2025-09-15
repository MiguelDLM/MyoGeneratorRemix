import bpy

class MYOGENERATOR_PT_panel(bpy.types.Panel):
    bl_idname = "MYOGENERATOR_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "MyoGeneratorRemix"
    bl_category = "MyoGeneratorRemix"
    bl_options = {'DEFAULT_CLOSED'}
    
    #Menu for the panel
    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Data Storage Location")

        row = box.row()
        row.prop(context.scene, "conf_path", text="Folder path")	

        row = box.row()
        row.prop(context.scene, "file_name", text="File name", icon='GREASEPENCIL')

        layout.separator()

        box = layout.box()
        box.label(text="Muscle ID")
        row = box.row()
        row.prop(context.scene, "muscle_Name", text="Muscle Name", icon='GREASEPENCIL')
        row.enabled = (context.scene.file_name != "")

        row = box.row()
        row.operator('view3d.submit_button', text="Submit Muscle")
        row.enabled = context.scene.muscle_Name != "Insert muscle name"

        layout.separator()

        box = layout.box()
        box.label(text="Origin Creation")
        row = box.row()
        row.prop(context.scene, "origin_object", text='Origin\'s Bone')

        row = box.row()
        col1 = row.column()
        col1.operator("view3d.select_origin", text="Start Origin Selection")
        col1.enabled = context.scene.origin_object is not None

        col2 = row.column()
        col2.operator('view3d.submit_origin', text="Submit Origin")
        col2.enabled = context.scene.origin_object is not None

        layout.separator()

        box = layout.box()
        box.label(text="Insertion Creation")
        row1 = box.row()
        row1.prop(context.scene, "insertion_object", text='Insertion\'s Bone')

        row2 = box.row()
        col1 = row2.column()
        col1.operator("view3d.select_insertion", text="Start Insertion Selection")
        col1.enabled = context.scene.insertion_object is not None

        col2 = row2.column()
        col2.operator('view3d.submit_insertion', text="Submit Insertion")
        col2.enabled = context.scene.insertion_object is not None

        layout.separator()

        # Muscle Creation Workflow - simplified single section
        box = layout.box()
        box.label(text="Muscle Creation", icon='CURVE_BEZCURVE')
        
        # Create muscle path
        row = box.row()
        row.operator("view3d.muscle_curve_creation", text="Create Muscle Path", icon='CURVE_PATH')
        
        row = box.row()
        row.label(text="Manual curve adjustment in Edit Mode")
        
        # Preview controls
        row = box.row()
        # Connection mode selector (appears before preview controls)
        row = box.row()
        row.prop(context.scene, "muscle_connection_mode", text="Connection Mode", expand=True)

        if hasattr(context.scene, 'muscle_preview_active') and context.scene.muscle_preview_active:
            row.operator("view3d.muscle_preview_stop", text="Stop Preview", icon='PAUSE')
        else:
            row.operator("view3d.muscle_preview_update", text="Start Preview", icon='PLAY')
        
        # Mesh Quality Controls
        row = box.row()
        row.label(text="Mesh Quality:", icon='MESH_ICOSPHERE')
        
        # Curve subdivisions
        row = box.row()
        row.prop(context.scene, "muscle_curve_subdivisions", text="Curve Subdivisions")
        
        # Contour resolution
        row = box.row()
        row.prop(context.scene, "muscle_contour_resolution", text="Contour Resolution")

        # Vertex order offsets for contour alignment
        row = box.row(align=True)
        row.prop(context.scene, "origin_contour_offset", text="Origin Offset")
        row.prop(context.scene, "insertion_contour_offset", text="Insertion Offset")

        # Option to reverse contour orientation if needed
        row = box.row(align=True)
        row.prop(context.scene, "origin_reverse_orientation", text="Reverse Origin")
        row.prop(context.scene, "insertion_reverse_orientation", text="Reverse Insertion")

        
        # Info about automatic Bezier control
        row = box.row()
        row.label(text="Tip: Use curve handles to control muscle shape", icon='INFO')
        
        # Generate final mesh
        row = box.row()
        row.operator("view3d.muscle_mesh_generation", text="Generate Final Mesh", icon='MESH_CUBE')

        layout.separator()
        
        box = layout.box()
        box.label(text="Finish")
        row = box.row()
        row.operator("view3d.next_muscle", text="Next Muscle")
        
        layout.separator()
        
        row = box.row()
        row.prop(context.scene, "muscle_constant", text="Muscle Constant (N/cm²)", icon='FORCE_FORCE')
        
        row = box.row()
        row.operator("view3d.calculate_muscle_parameters", text="Calculate Muscle Parameters")

        # Advanced (experimental) features from Add-on preferences
        show_adv = False
        
        try:
            # Try multiple possible addon names (development vs released)
            addon_names = [
                "bl_ext.vscode_development.AddonFolder",  # VSCode development mode
                "MyoGeneratorRemix",  # Released version
                "bl_ext.user_default.MyoGeneratorRemix",  # User extensions
            ]
            
            for addon_name in addon_names:
                addon_prefs = bpy.context.preferences.addons.get(addon_name)
                if addon_prefs and hasattr(addon_prefs, 'preferences'):
                    prefs = addon_prefs.preferences
                    if hasattr(prefs, 'show_advanced'):
                        show_adv = bool(prefs.show_advanced)
                        break
                            
        except Exception as e:
            show_adv = False

        if show_adv:
            layout.separator()
            adv_box = layout.box()
            adv_box.label(text="Advanced (experimental)")

            row = adv_box.row()
            # Prefer the core operator if registered, otherwise fallback to the packaged operator
            if hasattr(bpy.ops, 'view3d') and hasattr(bpy.ops.view3d, 'estimate_selected_volumes'):
                row.operator("view3d.estimate_selected_volumes", text="Estimate Selected Volumes")
            else:
                row.operator("myogenerator.estimate_selected_volumes", text="Estimate Selected Volumes")

            # Display last computed value converted to the scene unit system
            total_vol_m3 = getattr(context.scene, 'advanced_selected_volume', 0.0)
            # Default values
            displayed_vol = total_vol_m3
            suffix = "m³"

            try:
                us = context.scene.unit_settings
                scale = float(getattr(us, 'scale_length', 1.0)) or 1.0

                # Try to detect explicit declared length unit if available (Blender exposes length_unit enum)
                length_unit = getattr(us, 'length_unit', None)

                # Map length unit enum or value to a human unit (meters, centimeters, millimeters, inches)
                if length_unit:
                    lu = str(length_unit).upper()
                    # Common enum names include 'METERS', 'CENTIMETERS', 'MILLIMETERS', 'INCHES', 'FEET'
                    if 'MILLIM' in lu or 'MM' == lu:
                        unit_len = 'mm'
                    elif 'CENTIM' in lu or 'CM' == lu:
                        unit_len = 'cm'
                    elif 'INCH' in lu or 'IN' == lu:
                        unit_len = 'in'
                    elif 'FOOT' in lu or 'FT' == lu:
                        unit_len = 'ft'
                    else:
                        unit_len = 'm'
                else:
                    # Fallback to mapping common scale_length values
                    if abs(scale - 0.001) < 1e-9:
                        unit_len = 'mm'
                    elif abs(scale - 0.01) < 1e-9:
                        unit_len = 'cm'
                    elif abs(scale - 0.0254) < 1e-9:
                        unit_len = 'in'
                    else:
                        unit_len = 'm' if scale >= 1.0 else 'm'

                # Convert canonical m³ to chosen length unit³
                if unit_len == 'm':
                    displayed_vol = total_vol_m3
                    suffix = 'm³'
                elif unit_len == 'cm':
                    # 1 m³ = 1e6 cm³
                    displayed_vol = total_vol_m3 * 1e6
                    suffix = 'cm³'
                elif unit_len == 'mm':
                    # 1 m³ = 1e9 mm³
                    displayed_vol = total_vol_m3 * 1e9
                    suffix = 'mm³'
                elif unit_len == 'in':
                    # 1 m = 39.3700787402 in -> 1 m³ = (39.3700787402)^3 in³
                    displayed_vol = total_vol_m3 * (39.3700787402 ** 3)
                    suffix = 'in³'
                else:
                    displayed_vol = total_vol_m3
                    suffix = 'm³'

            except Exception:
                # fallback already set
                pass

            # Format number sensibly: 4 decimals for medium values, 2 for large
            if displayed_vol == 0:
                disp_str = f"0.0000"
            elif displayed_vol < 1.0:
                disp_str = f"{displayed_vol:.6f}"
            elif displayed_vol < 1000.0:
                disp_str = f"{displayed_vol:.4f}"
            else:
                disp_str = f"{displayed_vol:,.2f}"

            row = adv_box.row()
            row.label(text=f"Selected Total Volume: {disp_str} {suffix}")
            
            # Density input (g/cm³)
            row = adv_box.row()
            row.prop(context.scene, "muscle_density_g_cm3", text="Density (g/cm³)")

            # Option to hide non-muscle objects in muscle collections
            row = adv_box.row()
            row.prop(context.scene, "advanced_hide_non_muscle", text="Hide non-muscle objects")

            # Mirror duplicate control (axis selector + button)
            row = adv_box.row(align=True)
            row.prop(context.scene, "myogenerator_mirror_axis", expand=True)
            # Only show the Mirror Duplicate button if the operator is registered
            if hasattr(bpy.ops, 'myogenerator') and hasattr(bpy.ops.myogenerator, 'mirror_duplicate'):
                op = row.operator("myogenerator.mirror_duplicate", text="Mirror Duplicate")
                # pass current scene property as default
                try:
                    op.axis = context.scene.myogenerator_mirror_axis
                except Exception:
                    pass
            else:
                row.label(text="Mirror Duplicate (operator not registered)")

            # Total mass display (convert kg -> g for user view)
            total_mass_kg = getattr(context.scene, 'advanced_selected_mass', 0.0)
            try:
                mass_g = total_mass_kg * 1000.0
            except Exception:
                mass_g = 0.0

            if mass_g == 0:
                mass_str = "0.00 g"
            elif mass_g < 1000.0:
                mass_str = f"{mass_g:.4f} g"
            else:
                mass_str = f"{mass_g:,.2f} g"

            row = adv_box.row()
            row.label(text=f"Estimated Total Mass: {mass_str}")

            # PCSA total
            pcsa_text = getattr(context.scene, 'advanced_selected_pcsa', "")
            row = adv_box.row()
            row.label(text=pcsa_text if pcsa_text else "Total PCSA: NA")