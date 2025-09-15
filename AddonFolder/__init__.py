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
                            Calculate_Muscle_Parameters_Op,
                            MYOGENERATOR_OT_toggle_hide_non_muscles,
                            MYOGENERATOR_OT_mirror_duplicate)
from .muscle_utilities import (update_mesh_density, calculate_muscle_volume)
from .improved_muscle_workflow import (Muscle_Curve_Creation_Op, 
                                     Muscle_Mesh_Generation_Op,
                                     Muscle_Preview_Update_Op,
                                     Muscle_Preview_Stop_Op)
from .myoGenerator_panel import MYOGENERATOR_PT_panel
from .core_operators import Estimate_Selected_Volumes_Op


# Helper to update visibility of non-muscle objects when the scene property changes
def update_hide_non_muscle(self, context):
    try:
        muscles_collection = bpy.data.collections.get('muscles')
        if not muscles_collection:
            return

        hide = bool(getattr(context.scene, 'advanced_hide_non_muscle', False))

        for muscle_col in muscles_collection.children:
            for obj in muscle_col.objects:
                # Keep objects that are the final muscle mesh visible; hide others when requested
                is_muscle = obj.name.endswith('_muscle')
                if hide and not is_muscle:
                    try:
                        obj.hide_viewport = True
                    except Exception:
                        pass
                    try:
                        obj.hide_set(True)
                    except Exception:
                        pass
                else:
                    try:
                        obj.hide_viewport = False
                    except Exception:
                        pass
                    try:
                        obj.hide_set(False)
                    except Exception:
                        pass
    except Exception:
        # Best-effort only; avoid raising in UI callbacks
        return



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
    # Register mirror duplicate operator explicitly (guarded)
    try:
        bpy.utils.register_class(MYOGENERATOR_OT_mirror_duplicate)
    except Exception as e:
        print(f"MyoGenerator: mirror operator register skipped/failed: {e}")


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
        default=30,
        min=0.0,
        max=50.0,
        precision=3,
        step=1
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
    
    # Density for mass calculation (user input) in g/cm³ (default 1.0597 g/cm³)
    bpy.types.Scene.muscle_density_g_cm3 = bpy.props.FloatProperty(
        name="Muscle Density (g/cm³)",
        description="Density used to compute mass from volume (grams per cubic centimeter)",
        default=1.0597,
        min=0.0,
        precision=4,
        step=0.0001
    )

    # Store last computed total mass in kilograms (canonical)
    bpy.types.Scene.advanced_selected_mass = bpy.props.FloatProperty(
        name="Advanced Selected Mass",
        description="Holds the last computed total mass for selected objects (kg)",
        default=0.0,
        precision=6
    )

    # Human readable PCSA per muscle (multiline string)
    bpy.types.Scene.advanced_selected_pcsa = bpy.props.StringProperty(
        name="Advanced Selected PCSA",
        description="Display of PCSA per muscle (read-only)",
        default="",
        maxlen=4096
    )

    # Toggle to hide non-muscle objects in muscle subcollections (updates on change)
    bpy.types.Scene.advanced_hide_non_muscle = bpy.props.BoolProperty(
        name="Hide non-muscle objects",
        description="When enabled, hides objects inside each muscle subcollection that are not the final '_muscle' mesh",
        default=False,
        update=update_hide_non_muscle
    )

    # Mirror duplicate axis property (used by Advanced UI)
    bpy.types.Scene.myogenerator_mirror_axis = bpy.props.EnumProperty(
        name="Mirror Axis",
        items=[('X', 'X', 'Mirror across X'), ('Y', 'Y', 'Mirror across Y'), ('Z', 'Z', 'Mirror across Z')],
        default='X'
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
    # Unregister mirror operator if present
    try:
        from . import core_operators as _co
        cls = getattr(_co, 'MYOGENERATOR_OT_mirror_duplicate', None)
        if cls:
            bpy.utils.unregister_class(cls)
    except Exception as e:
        print(f"MyoGenerator: failed to unregister mirror operator: {e}")


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
    del bpy.types.Scene.muscle_density_g_cm3
    del bpy.types.Scene.advanced_selected_mass
    del bpy.types.Scene.advanced_selected_pcsa

    if hasattr(bpy.types.Scene, 'myogenerator_mirror_axis'):
        del bpy.types.Scene.myogenerator_mirror_axis



