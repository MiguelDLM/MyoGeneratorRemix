import bpy

class MYOGENERATOR_PT_panel(bpy.types.Panel):
    bl_idname = "MYOGENERATOR_PT_panel"
    bl_label = "MyoGeneratorRemix"
    bl_category = "MyoGeneratorRemix"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

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

        box = layout.box()
        box.label(text="Muscle Creation")
        row = box.row()
        row.operator("view3d.muscle_creation",text="Create muscle")

        row = box.row()
        # add an input field for the number subvisions
        row.prop(context.scene, "muscle_subdivisions", text="Subdivisions")

        row = box.row()
        #add resampling number  
        row.prop(context.scene, "muscle_resampling", text="Resampling")

        row = box.row()
        row.prop(context.scene, "origin_rotation", text="Origin vertex rotation")

        row = box.row()
        row.prop(context.scene, "insertion_rotation", text="Insertion vertex rotation")

        row = box.row()
        row.operator("view3d.swap_origin_insertion", text="Swap Origin and Insertion")

        row = box.row()
        row.operator("view3d.switch_vertex_order_origin", text="Switch Origin Vertex Order")

        row = box.row()
        row.operator("view3d.switch_vertex_order_insertion", text="Switch Insertion Vertex Order")

        row = box.row()
        row.operator("view3d.muscle_volume_creator", text="Create Muscle volume")

        layout.separator()
        
        box = layout.box()
        box.label(text="Finish")
        row = box.row()
        row.operator("view3d.next_muscle", text="Next Muscle")
        row = box.row()
        row.operator("view3d.calculate_muscle_parameters", text="Calculate Muscle Parameters")