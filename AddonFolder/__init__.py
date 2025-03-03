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

from .myoGenerator_op import (Submit_Origin_Op, Submit_Insertion_Op,
                              Muscle_Creation_Op, 
                              Select_Insertion_Op, Muscle_Name_Submition,
                              Select_Origin_Op, update_muscle_subdivision, update_muscle_resampling,
                              update_insertion_rotation, update_origin_rotation, Swap_Origin_Insertion_Op, Switch_Insertion_Vertex_Order_Op, Switch_Origin_Vertex_Order_Op,
                              Muscle_Volume_Creation_Op, Calculate_Muscle_Parameters_Op, Next_Muscle_Op
                              )
from .myoGenerator_panel import MYOGENERATOR_PT_panel



def register():
    bpy.utils.register_class(Muscle_Name_Submition)
    bpy.utils.register_class(Select_Origin_Op)
    bpy.utils.register_class(Select_Insertion_Op)
    bpy.utils.register_class(Submit_Origin_Op)
    bpy.utils.register_class(Submit_Insertion_Op)
    bpy.utils.register_class(MYOGENERATOR_PT_panel)
    bpy.utils.register_class(Muscle_Creation_Op)
    bpy.utils.register_class(Muscle_Volume_Creation_Op)
    bpy.utils.register_class(Swap_Origin_Insertion_Op)
    bpy.utils.register_class(Switch_Insertion_Vertex_Order_Op)
    bpy.utils.register_class(Switch_Origin_Vertex_Order_Op)
    bpy.utils.register_class(Calculate_Muscle_Parameters_Op)
    bpy.utils.register_class(Next_Muscle_Op)


    bpy.types.Scene.conf_path = bpy.props.StringProperty(
        name="Path",
        default="",
        description="Select where to save your file...",
        subtype="DIR_PATH"
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
    bpy.types.Scene.origin_Name = bpy.props.StringProperty(
        name="Origin Name",
        description="Insert origin name",
        default='Insert origin name'
    )
    bpy.types.Scene.insertion_Name = bpy.props.StringProperty(
        name="Insertion Name",
        description="Insert insertion name",
        default='Insert insertion name'
    )
    bpy.types.Scene.muscle_subdivisions = bpy.props.IntProperty(
        name="muscle_subdivisions",
        description="Number of subdivisions",
        default=10,
        min=2,
        max=100,
        update=update_muscle_subdivision
    )

    bpy.types.Scene.muscle_resampling = bpy.props.IntProperty(
        name="muscle_resampling",
        description="Number resamplings for the attachment areas",
        default= 32,
        min=3,
        max=300,
        update= update_muscle_resampling
    )

    bpy.types.Scene.origin_rotation = bpy.props.IntProperty(
        name="origin_rotation",
        description="Rotate the order of the vertex from the origin object",
        default= 0,
        min= 0,
        max= 1000,
        update= update_origin_rotation
    )

    bpy.types.Scene.insertion_rotation = bpy.props.IntProperty(
        name="insertion_rotation",
        description="Rotate the order of the vertex from the insertion object",
        default= 0,
        min= 0,
        max= 1000,
        update= update_insertion_rotation
    )


def unregister():
    bpy.utils.unregister_class(Muscle_Name_Submition)
    bpy.utils.unregister_class(Select_Origin_Op)
    bpy.utils.unregister_class(Select_Insertion_Op)
    bpy.utils.unregister_class(Submit_Origin_Op)
    bpy.utils.unregister_class(Submit_Insertion_Op)
    bpy.utils.unregister_class(MYOGENERATOR_PT_panel)
    bpy.utils.unregister_class(Muscle_Creation_Op)
    bpy.utils.unregister_class(Muscle_Volume_Creation_Op)
    bpy.utils.unregister_class(Swap_Origin_Insertion_Op)
    bpy.utils.unregister_class(Switch_Insertion_Vertex_Order_Op)
    bpy.utils.unregister_class(Switch_Origin_Vertex_Order_Op)
    bpy.utils.unregister_class(Calculate_Muscle_Parameters_Op)
    bpy.utils.unregister_class(Next_Muscle_Op)


    del bpy.types.Scene.muscle_Name
    del bpy.types.Scene.conf_path
    del bpy.types.Scene.file_name
    del bpy.types.Scene.muscle_subdivisions
    del bpy.types.Scene.origin_object
    del bpy.types.Scene.insertion_object
    del bpy.types.Scene.muscle_resampling
