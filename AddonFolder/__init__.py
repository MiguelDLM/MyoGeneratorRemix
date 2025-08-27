# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy

from .core_operators import (Muscle_Name_Submition, Select_Origin_Op,
                            Select_Insertion_Op, Submit_Origin_Op,    
                            Submit_Insertion_Op, Next_Muscle_Op,
                            Calculate_Muscle_Parameters_Op)
from .muscle_utilities import (update_mesh_density, calculate_muscle_volume)
from .improved_muscle_workflow import (Muscle_Curve_Creation_Op, 
                                     Muscle_Mesh_Generation_Op,
                                     Muscle_Preview_Update_Op,
                                     Muscle_Preview_Stop_Op)
from .myoGenerator_panel import MYOGENERATOR_PT_panel
from .core_operators import Estimate_Selected_Volumes_Op



def register():
    # Register addon preferences FIRST
    bpy.utils.register_class(MyoGeneratorPreferences)
    
    bpy.utils.register_class(Muscle_Name_Submition)
    bpy.utils.register_class(Select_Origin_Op)
    bpy.utils.register_class(Select_Insertion_Op)
    bpy.utils.register_class(Submit_Origin_Op)
    bpy.utils.register_class(Submit_Insertion_Op)
    bpy.utils.register_class(Calculate_Muscle_Parameters_Op)
    bpy.utils.register_class(Next_Muscle_Op)
    # Register core UI panel after core operators so buttons reference valid operators
    bpy.utils.register_class(Estimate_Selected_Volumes_Op)
    bpy.utils.register_class(MYOGENERATOR_PT_panel)
    
    # Register improved workflow classes
    bpy.utils.register_class(Muscle_Curve_Creation_Op)
    bpy.utils.register_class(Muscle_Mesh_Generation_Op)
    bpy.utils.register_class(Muscle_Preview_Update_Op)
    bpy.utils.register_class(Muscle_Preview_Stop_Op)

    # Register fallback operator (always available) for estimating volumes in the Advanced UI
    bpy.utils.register_class(MYOGENERATOR_OT_estimate_selected_volumes)


    bpy.types.Scene.conf_path = bpy.props.StringProperty(
        name="Path",
        default="",
        description="Select folder where to save your CSV file...",
        subtype="DIR_PATH",
        maxlen=1024
    )
    bpy.types.Scene.file_name = bpy.props.StringProperty(
        name="File_Name",
        description="Your file name. It will be exported as .csv",
        subtype="FILE_NAME"
    )

    bpy.types.Scene.origin_object = bpy.props.PointerProperty(

        type=bpy.types.Object,
        name="origin object"
    )

    bpy.types.Scene.insertion_object = bpy.props.PointerProperty(

        type=bpy.types.Object,
        name="insertion_object"
    )

    bpy.types.Scene.muscle_Name = bpy.props.StringProperty(
        name="Muscle Name",
        description="Insert your muscle name",
        default='Insert muscle name'
    )

    # New mesh density control properties
    bpy.types.Scene.muscle_curve_subdivisions = bpy.props.IntProperty(
        name="Curve Subdivisions",
        description="Number of subdivisions along the muscle curve",
        default=12,
        min=4,
        max=100,
        update=update_mesh_density
    )

    bpy.types.Scene.muscle_contour_resolution = bpy.props.IntProperty(
        name="Contour Resolution",
        description="Resolution of the contour loops (vertex count)",
        default=16,
        min=4,
        max=100,
        update=update_mesh_density
    )

    # Vertex order offsets for contour alignment
    bpy.types.Scene.origin_contour_offset = bpy.props.IntProperty(
        name="Origin Offset",
        description="Shift origin contour vertices for better alignment",
        default=0,
        min=0,
        max=64,
        update=update_mesh_density
    )

    bpy.types.Scene.insertion_contour_offset = bpy.props.IntProperty(
        name="Insertion Offset",
        description="Shift insertion contour vertices for better alignment",
        default=0,
        min=0,
        max=64,
        update=update_mesh_density
    )

    # Optional reversal of contour vertex orientation
    bpy.types.Scene.origin_reverse_orientation = bpy.props.BoolProperty(
        name="Reverse Origin",
        description="Reverse origin contour vertex order",
        default=False,
        update=update_mesh_density,
    )

    bpy.types.Scene.insertion_reverse_orientation = bpy.props.BoolProperty(
        name="Reverse Insertion",
        description="Reverse insertion contour vertex order",
        default=False,
        update=update_mesh_density,
    )


    # Muscle force calculation constant
    bpy.types.Scene.muscle_constant = bpy.props.FloatProperty(
        name="Muscle Constant",
        description="Muscle constant for force calculation (N/cm²)",
        default=0.3,
        min=0.0,
        max=10.0,
        precision=3,
        step=0.01
    )

    # Connection mode for lofting: follow the curve path or directly connect origin->insertion
    bpy.types.Scene.muscle_connection_mode = bpy.props.EnumProperty(
        name="Connection Mode",
        description="Choose how the muscle loft connects origin and insertion",
        items=[
            ('FOLLOW_PATH', "Follow Path", "Loft along the curve path (default)"),
            ('DIRECT_CONNECTION', "Direct Connection", "Connect origin and insertion directly, ignoring curve curvature")
        ],
        default='FOLLOW_PATH'
    )

    # Temporary scene storage for advanced UI (sum of selected volumes)
    bpy.types.Scene.advanced_selected_volume = bpy.props.FloatProperty(
        name="Advanced Selected Volume",
        description="Holds the last computed total volume for selected objects (m³)",
        default=0.0,
        precision=6
    )


# Addon Preferences Class
class MyoGeneratorPreferences(bpy.types.AddonPreferences):
    # Use the package name so it matches both dev (bl_ext.vscode_development.AddonFolder)
    # and installed addon module names automatically.
    bl_idname = __package__

    # Define as an annotation so Blender's RNA picks it up reliably.
    show_advanced: bpy.props.BoolProperty(
        name="Show Advanced (experimental) features",
        description="Enable experimental features in the MyoGenerator panel",
        default=False,
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "show_advanced")


def unregister():
    bpy.utils.unregister_class(Muscle_Name_Submition)
    bpy.utils.unregister_class(Select_Origin_Op)
    bpy.utils.unregister_class(Select_Insertion_Op)
    bpy.utils.unregister_class(Submit_Origin_Op)
    bpy.utils.unregister_class(Submit_Insertion_Op)
    bpy.utils.unregister_class(Calculate_Muscle_Parameters_Op)
    bpy.utils.unregister_class(Next_Muscle_Op)
    bpy.utils.unregister_class(MYOGENERATOR_PT_panel)
    bpy.utils.unregister_class(Estimate_Selected_Volumes_Op)
    bpy.utils.unregister_class(MyoGeneratorPreferences)
    # Unregister improved workflow classes
    bpy.utils.unregister_class(Muscle_Curve_Creation_Op)
    bpy.utils.unregister_class(Muscle_Mesh_Generation_Op)
    bpy.utils.unregister_class(Muscle_Preview_Update_Op)
    bpy.utils.unregister_class(Muscle_Preview_Stop_Op)
    bpy.utils.unregister_class(MYOGENERATOR_OT_estimate_selected_volumes)


    del bpy.types.Scene.muscle_Name
    del bpy.types.Scene.conf_path
    del bpy.types.Scene.file_name
    del bpy.types.Scene.origin_object
    del bpy.types.Scene.insertion_object
    del bpy.types.Scene.muscle_curve_subdivisions
    del bpy.types.Scene.muscle_contour_resolution
    del bpy.types.Scene.muscle_constant
    del bpy.types.Scene.origin_contour_offset
    del bpy.types.Scene.insertion_contour_offset
    del bpy.types.Scene.origin_reverse_orientation
    del bpy.types.Scene.insertion_reverse_orientation
    del bpy.types.Scene.muscle_connection_mode
    del bpy.types.Scene.advanced_selected_volume


# Fallback operator for estimating volumes (ensures button exists regardless of core_operators import order)
class MYOGENERATOR_OT_estimate_selected_volumes(bpy.types.Operator):
    bl_idname = "myogenerator.estimate_selected_volumes"
    bl_label = "Estimate Selected Volumes"
    bl_description = "Estimate the total volume of selected mesh objects (fallback)"

    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "No mesh objects selected")
            context.scene.advanced_selected_volume = 0.0
            return {'CANCELLED'}

        total_volume = 0.0
        for obj in selected:
            try:
                vol = calculate_muscle_volume(obj)
                total_volume += vol
            except Exception:
                continue

        try:
            context.scene.advanced_selected_volume = float(total_volume)
        except Exception:
            context.scene.advanced_selected_volume = 0.0

        self.report({'INFO'}, f"Estimated total volume: {total_volume:.6f} m³")
        return {'FINISHED'}
