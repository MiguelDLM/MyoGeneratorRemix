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

        # New improved workflow section
        box = layout.box()
        box.label(text="Muscle Creation Workflow", icon='CURVE_BEZCURVE')
        
        # Stage 1: Curve Creation
        subbox = box.box()
        subbox.label(text="Stage 1: Create & Adjust Path")
        row = subbox.row()
        row.operator("view3d.muscle_curve_creation", text="Create Muscle Path", icon='CURVE_PATH')
        
        row = subbox.row()
        row.label(text="Manual curve adjustment in Edit Mode")
        row = subbox.row()
        # Check if preview is active to show appropriate button
        if hasattr(context.scene, 'muscle_preview_active') and context.scene.muscle_preview_active:
            row.operator("view3d.muscle_preview_stop", text="Stop Preview", icon='PAUSE')
        else:
            row.operator("view3d.muscle_preview_update", text="Start Preview", icon='PLAY')
        
        # Stage 2: Mesh Generation
        subbox = box.box()
        subbox.label(text="Stage 2: Generate Final Mesh")
        row = subbox.row()
        row.operator("view3d.muscle_mesh_generation", text="Generate Mesh", icon='MESH_CUBE')
        
        row = subbox.row()
        row.operator("view3d.muscle_finalize", text="Finalize Muscle", icon='CHECKMARK')

        layout.separator()

        # Validation and utilities section
        subbox = box.box()
        subbox.label(text="Validation & Utilities")
        row = subbox.row()
        row.operator("view3d.muscle_validation", text="Validate Setup", icon='CHECKMARK')
        row.operator("view3d.muscle_cleanup", text="Clean Up", icon='TRASH')
        
        row = subbox.row()
        row.operator("view3d.muscle_debug_alignment", text="Debug Alignment", icon='ZOOM_SELECTED')

        layout.separator()
        
        box = layout.box()
        box.label(text="Finish")
        row = box.row()
        row.operator("view3d.next_muscle", text="Next Muscle")
        row = box.row()
        row.operator("view3d.calculate_muscle_parameters", text="Calculate Muscle Parameters")