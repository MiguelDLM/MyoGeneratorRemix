import bpy

class MYOGENERATOR_PT_panel(bpy.types.Panel):
    bl_idname = "MYOGENERATOR_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "MyoGeneratorRemix"
    bl_category = "MyoGeneratorRemix"
    bl_options = {'DEFAULT_CLOSED'}
    
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

        # Lofting mode selection
        row = box.row()
        row.prop(context.scene, "muscle_lofting_mode", text="Lofting Mode")
        
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