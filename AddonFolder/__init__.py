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

bl_info = {
    "name" : "MyoGenerator",
    "author" : "Niccolo Fioritti and Eva Herbst",
    "description" : "TestAddon",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 1),
    "location" : "View3D",
    "warning" : "",
    "category" : "Generic"
}


from AddonFolder.muscleCore import curve_creator
import bpy

#from muscleCore.create_muscle_empties import *
#import bpy.utilis


from . test_op import Nico_Select_Muscle_Op, Nico_Select_Origin_Op,Nico_Select_Insertion_Op,Nico_AllowAttach_Op, Nico_Muscle_Creation_Op,Nico_Curve_Creator_Op,Nico_Join_Muscle_Op,Nico_Transform_To_Mesh_Op,SetBevel_Op,SetBevel2_Op,SetTilt_Op, Calculate_Volume_Op

from . test_panel import Nico_Test_Panel_PT_
#classes =(Nico_Test_Op, Nico_Test_Panel_PT_)
#register, unregister = bpy.utils.register_classes_factory(classes)


# REF FOR BUTTON TO MAKE BUTTONS: https://blender.stackexchange.com/questions/57545/can-i-make-a-ui-button-that-makes-buttons-in-a-panel

#OTHER REF GENERAL BLENDER ADDONS: https://b3d.interplanety.org/en/calling-functions-by-pressing-buttons-in-blender-custom-ui/

#REF GRAYOUT BUTTONS: https://blenderartists.org/t/gray-out-a-panel-button/522047/2

#REF GRAOUT BUTTONS 2 https://blender.stackexchange.com/questions/160883/contextually-grey-out-panel-element-in-python-2-8


def register():
    bpy.utils.register_class(Nico_Select_Muscle_Op)
    bpy.utils.register_class(Nico_Select_Origin_Op)
    bpy.utils.register_class(Nico_Select_Insertion_Op)
    bpy.utils.register_class(Nico_AllowAttach_Op)
    bpy.utils.register_class(Nico_Test_Panel_PT_)
    bpy.utils.register_class( Nico_Muscle_Creation_Op)
    bpy.utils.register_class(Nico_Curve_Creator_Op)
    bpy.utils.register_class(Nico_Join_Muscle_Op)
    bpy.utils.register_class(Nico_Transform_To_Mesh_Op)
    bpy.utils.register_class(SetBevel_Op)
    bpy.utils.register_class(SetBevel2_Op)
    bpy.utils.register_class(SetTilt_Op)
    bpy.utils.register_class(Calculate_Volume_Op)
             


    bpy.types.Scene.conf_path = bpy.props.StringProperty \
        (
            name = "Path",
            default = "",
            #update = lambda s,c: make_path_absolute('conf_path'),
            description = "Select where to save your file...",
            subtype = "DIR_PATH"
        )
    bpy.types.Scene.file_name = bpy.props.StringProperty \
        (
            name = "File_Name",
            default = "",
            #update = lambda s,c: make_path_absolute('conf_path'),
            description = "Your file name. It will be exported as .csv",
            subtype = "FILE_NAME"
        )

    
    bpy.types.Scene.origin_object =bpy.props.PointerProperty \
    (
                
        type=bpy.types.Object,        
        name = "origin object"
       # description = "asd",
        #default ='asd'
    )
        
    bpy.types.Scene.insertion_object =bpy.props.PointerProperty \
    (
                
        type=bpy.types.Object,        
        name = "insertion_object"
       # description = "asd",
        #default ='asd'
    )
        

    bpy.types.Scene.muscle_Name=bpy.props.StringProperty \
        (
            name = "Muscle Name",
            description = "Insert your muscle name",
            default ='Insert muscle name'
        )
    bpy.types.Scene.origin_Name=bpy.props.StringProperty \
        (
            name = "Origin Name",
            description = "Insert origin name",
            default ='Insert origin name'
        )
    bpy.types.Scene.insertion_Name=bpy.props.StringProperty \
        (
            name = "Insertion Name",
            description = "Insert insertion name",
            default ='Insert insertion name'
        )


    bpy.types.Scene.bevel =bpy.props.FloatProperty \
        (
                    
            name = "bevel",
            min=0,
            max=1,
            update=SetBevel_Op.execute
        # description = "asd",
            #default ='asd'
        )

    bpy.types.Scene.bevel2 =bpy.props.FloatProperty \
        (
                             
            name = "bevel2",
            min=0,
            max=1,
            update=SetBevel2_Op.execute
        # description = "asd",
            #default ='asd'
        )

    bpy.types.Scene.tilt =bpy.props.FloatProperty \
        (

            name = "tilt",
            min=0,
            max=360,
            update=SetTilt_Op.execute
        # description = "asd",
            #default ='asd'
        )

    #NEED TO ADD PROPERTY Scene.theChosenObject



#### FOR OBJECT EYEDROPPER: https://blender.stackexchange.com/questions/30487/object-selection-box-with-eyedropper

def unregister():
    bpy.utils.unregister_class(Nico_Select_Muscle_Op)
    bpy.utils.unregister_class(Nico_Select_Origin_Op)
    bpy.utils.unregister_class(Nico_Select_Insertion_Op)
    bpy.utils.unregister_class(Nico_AllowAttach_Op)
    bpy.utils.unregister_class(Nico_Test_Panel_PT_)
    bpy.utils.unregister_class( Nico_Muscle_Creation_Op)
    bpy.utils.unregister_class(Nico_Curve_Creator_Op)
    bpy.utils.unregister_class(Nico_Join_Muscle_Op)
    bpy.utils.unregister_class(Nico_Transform_To_Mesh_Op)
    bpy.utils.unregister_class(SetBevel_Op)
    bpy.utils.unregister_class(SetBevel2_Op)
    bpy.utils.unregister_class(SetTilt_Op)
    bpy.utils.unregister_class(Calculate_Volume_Op)

    del bpy.types.Scene.muscle_Name
    del bpy.types.Scene.bevel
    del bpy.types.Scene.conf_path
    del bpy.types.Scene.file_name
    
