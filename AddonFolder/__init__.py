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
from .muscle_utilities import (update_mesh_density)
from .improved_muscle_workflow import (Muscle_Curve_Creation_Op, 
                                     Muscle_Mesh_Generation_Op,
                                     Muscle_Preview_Update_Op,
                                     Muscle_Preview_Stop_Op)
from .myoGenerator_panel import MYOGENERATOR_PT_panel



def register():
    bpy.utils.register_class(Muscle_Name_Submition)
    bpy.utils.register_class(Select_Origin_Op)
    bpy.utils.register_class(Select_Insertion_Op)
    bpy.utils.register_class(Submit_Origin_Op)
    bpy.utils.register_class(Submit_Insertion_Op)
    bpy.utils.register_class(Calculate_Muscle_Parameters_Op)
    bpy.utils.register_class(Next_Muscle_Op)
    bpy.utils.register_class(MYOGENERATOR_PT_panel)
    
    # Register improved workflow classes
    bpy.utils.register_class(Muscle_Curve_Creation_Op)
    bpy.utils.register_class(Muscle_Mesh_Generation_Op)
    bpy.utils.register_class(Muscle_Preview_Update_Op)
    bpy.utils.register_class(Muscle_Preview_Stop_Op)


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
        max=50,
        update=update_mesh_density
    )

    bpy.types.Scene.muscle_contour_resolution = bpy.props.IntProperty(
        name="Contour Resolution",
        name="Contour Resolution",
        description="Resolution of the contour loops (vertex count)",
        default=16,
        min=6,
        max=64,
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


def unregister():
    bpy.utils.unregister_class(Muscle_Name_Submition)
    bpy.utils.unregister_class(Select_Origin_Op)
    bpy.utils.unregister_class(Select_Insertion_Op)
    bpy.utils.unregister_class(Submit_Origin_Op)
    bpy.utils.unregister_class(Submit_Insertion_Op)
    bpy.utils.unregister_class(Calculate_Muscle_Parameters_Op)
    bpy.utils.unregister_class(Next_Muscle_Op)
    bpy.utils.unregister_class(MYOGENERATOR_PT_panel)
    
    # Unregister improved workflow classes
    bpy.utils.unregister_class(Muscle_Curve_Creation_Op)
    bpy.utils.unregister_class(Muscle_Mesh_Generation_Op)
    bpy.utils.unregister_class(Muscle_Preview_Update_Op)
    bpy.utils.unregister_class(Muscle_Preview_Stop_Op)


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
