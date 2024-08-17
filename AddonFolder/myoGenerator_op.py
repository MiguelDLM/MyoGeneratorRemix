import math
import os
import sys
import bpy
import bmesh
import mathutils


from AddonFolder import muscleCore, myoGenerator_panel, vertex_Counter

isSubmittingOrigin = False


testAttch0 = "baseAttch0"
testAttch1 = "baseAttch1"

testList = ["list"]

class Muscle_Name_Submition(bpy.types.Operator):
    bl_idname = "view3d.submit_button"
    bl_label = "Submit Muscle Name"
    bl_description = "Submit Muscle Name"

    def execute(self, context):
        objName = bpy.context.scene.muscle_Name

        # Check if the "muscles" collection exists
        if "muscles" not in bpy.data.collections:
            # Create the "muscles" collection
            muscles_collection = bpy.data.collections.new("muscles")
            bpy.context.scene.collection.children.link(muscles_collection)
        else:
            muscles_collection = bpy.data.collections["muscles"]

        # Check if a collection with the name objName already exists inside "muscles"
        if objName in muscles_collection.children:
            self.report({'WARNING'}, f"Muscle '{objName}' already exists, choose a different name.")            
            return {'CANCELLED'}
        else:
            # Create a new collection inside "muscles" with the name objName
            new_collection = bpy.data.collections.new(objName)
            muscles_collection.children.link(new_collection)

        myoGenerator_panel.parentMuscleGenerated = True

        return {'FINISHED'}

def select_and_edit_object(obj):
    # Ensure the object is selected
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')
    bpy.ops.wm.tool_set_by_id(name="builtin.select_lasso", space_type='VIEW_3D')
    bpy.ops.mesh.select_all(action='DESELECT')

class Select_Origin_Op(bpy.types.Operator):
    bl_idname = "view3d.select_origin"
    bl_label = "Select Origin"
    bl_description = "Select Origin of the muscle"

    def execute(self, context):
        # Get the selected object in origin object
        origin_object = bpy.context.scene.origin_object
        select_and_edit_object(origin_object)
        return {'FINISHED'}

def create_mesh_from_selected_faces(self, mesh_name):
    # Get the selected object based on mesh_name
    if mesh_name == "origin":
        selected_object = bpy.context.scene.origin_object
    elif mesh_name == "insertion":
        selected_object = bpy.context.scene.insertion_object
    else:
        self.report({'ERROR'}, f"Invalid object type '{mesh_name}'")
        return {'CANCELLED'}
    
    objName = bpy.context.scene.muscle_Name

    # Check if the object already exists in the collection
    muscles_collection = bpy.data.collections.get("muscles")
    if muscles_collection and objName in muscles_collection.children:
        target_collection = muscles_collection.children[objName]
        if mesh_name in target_collection.objects:
            self.report({'WARNING'}, f"Object '{mesh_name}' already exists in collection '{objName}'")
            return {'CANCELLED'}
    else:
        self.report({'ERROR'}, f"Collection '{objName}' not found in 'muscles'")
        return {'CANCELLED'}
    
    # Ensure the selected object is in edit mode
    if bpy.context.object != selected_object or bpy.context.object.mode != 'EDIT':
        self.report({'ERROR'}, f"The active object is not in edit mode or is not the correct object for '{mesh_name}'")
        return {'CANCELLED'}
    # Get the BMesh representation
    bm = bmesh.from_edit_mesh(selected_object.data)

    # Find the selected faces
    selected_faces = [face for face in bm.faces if face.select]

    if not selected_faces:
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'WARNING'}, "No faces selected")
        return {'CANCELLED'}

    # Create a new mesh and object
    new_mesh = bpy.data.meshes.new(mesh_name)
    new_object = bpy.data.objects.new(mesh_name, new_mesh)
    bpy.context.collection.objects.link(new_object)

    # Create a new BMesh for the new object
    new_bm = bmesh.new()

    # Copy selected faces to the new BMesh
    for face in selected_faces:
        new_face = new_bm.faces.new([new_bm.verts.new(v.co) for v in face.verts])
        new_face.normal_update()

    # Finish up the new BMesh
    new_bm.to_mesh(new_mesh)
    new_bm.free()

    # Add the new object to the collection with objName inside "muscles"
    target_collection.objects.link(new_object)
    bpy.context.collection.objects.unlink(new_object)

    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    self.report({'INFO'}, f"New mesh '{mesh_name}' with selected faces created and added to collection '{objName}' inside 'muscles'")
    return {'FINISHED'}

class Submit_Origin_Op(bpy.types.Operator):
    bl_idname = "view3d.submit_origin"
    bl_label = "Submit Origin"
    bl_description = "Submit Origin of the muscle"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'EDIT'


    def execute(self, context):

        create_mesh_from_selected_faces(self,"origin")

        return {'FINISHED'}

class Select_Insertion_Op(bpy.types.Operator):
    bl_idname = "view3d.select_insertion"
    bl_label = "Select Insertion"
    bl_description = "Select Insertion of the muscle"

    def execute(self, context):
        # Get the selected object in insertion object
        insertion_object = bpy.context.scene.insertion_object
        select_and_edit_object(insertion_object)

        return {'FINISHED'}

class Submit_Insertion_Op(bpy.types.Operator):
    bl_idname = "view3d.submit_insertion"
    bl_label = "Submit Insertion"
    bl_description = "Submit Insertion of the muscle"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'EDIT'

    def execute(self, context):

        create_mesh_from_selected_faces(self,"insertion")
        return {'FINISHED'}
    
class Muscle_Creation_Op(bpy.types.Operator):
    bl_idname = "view3d.muscle_creation"
    bl_label = "Muscle Creation"

    def execute(self, context):
        print("ALL OK")
        myoGenerator_panel.vertexCountMatched = True
        vertex_Counter.OverallVertexCount()
        return{'FINISHED'}


from mathutils import Vector

class Curve_Creator_Op(bpy.types.Operator):
    bl_idname = "view3d.curve_creator"
    bl_label = "Curve Creator"

    def execute(self, context):
        # Obtener la colección objName dentro de "muscles"
        objName = bpy.context.scene.muscle_Name
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection or objName not in muscles_collection.children:
            self.report({'ERROR'}, f"Collection '{objName}' not found in 'muscles'")
            return {'CANCELLED'}
        
        target_collection = muscles_collection.children[objName]

        # Obtener los objetos origin e insertion
        origin_object = target_collection.objects.get("origin")
        insertion_object = target_collection.objects.get("insertion")
        if not origin_object or not insertion_object:
            self.report({'ERROR'}, "Origin or insertion object not found in the collection")
            return {'CANCELLED'}

        # Calcular el centroide del objeto origin
        origin_centroid = self.calculate_centroid(origin_object)

        # Calcular el centroide del objeto insertion
        insertion_centroid = self.calculate_centroid(insertion_object)

        # Crear una nueva curva
        curve_data = bpy.data.curves.new(name="MuscleCurve", type='CURVE')
        curve_data.dimensions = '3D'
        polyline = curve_data.splines.new('POLY')
        polyline.points.add(10)  # Añadir 10 puntos adicionales para un total de 11 puntos (10 divisiones)
        
        # Calcular las posiciones intermedias
        for i in range(11):
            t = i / 10
            x = origin_centroid[0] * (1 - t) + insertion_centroid[0] * t
            y = origin_centroid[1] * (1 - t) + insertion_centroid[1] * t
            z = origin_centroid[2] * (1 - t) + insertion_centroid[2] * t
            polyline.points[i].co = (x, y, z, 1)
        
        # Crear un nuevo objeto con la curva
        curve_object = bpy.data.objects.new("MuscleCurve", curve_data)
        
        # Añadir la curva a la colección objName dentro de "muscles"
        target_collection.objects.link(curve_object)
        #set the curve as active object
        bpy.context.view_layer.objects.active = curve_object
        bpy.ops.object.mode_set(mode='EDIT')

        self.report({'INFO'}, "Curve created successfully")
        return {'FINISHED'}

    def calculate_centroid(self, obj):
        # Cambiar temporalmente al modo objeto si es necesario
        initial_mode = obj.mode
        if initial_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Obtener los vértices del objeto
        mesh = obj.data
        centroid = Vector((0, 0, 0))
        for vert in mesh.vertices:
            centroid += vert.co
        centroid /= len(mesh.vertices)  

        return centroid


class Join_Muscle_Op(bpy.types.Operator):
    bl_idname = "view3d.join_muscle"
    bl_label = "Join Muscle"

    def execute(self, context):

        print(bpy.context.scene.muscle_Name, "JOINMUSCLE")
        muscleCore.join_muscle(bpy.context.scene.muscle_Name)

        return{"FINISHED"}


class Transform_To_Mesh_Op(bpy.types.Operator):
    bl_idname = "view3d.convert_to_mesh"
    bl_label = "Convert To Mesh"

    def execute(self, context):

        from AddonFolder import globalVariables




        path =os.path.join(
            context.scene.conf_path,
            (context.scene.file_name + ".csv"))

        
        path = (os.path.realpath(bpy.path.abspath(path)))


        globalVariables.csvDir=path


        # this code is deprecated but keep it jic: relative path to blender file. 
        # globalVariables.csvDir = os.path.join(
        #     context.scene.conf_path,
        #     (context.scene.file_name + ".csv"))

        muscleCore.get_length()  # ASSIGN NURBS LENGTH TO DICTIONARY
        muscleCore.Transform_to_Mesh(bpy.context.scene.muscle_Name)
        myoGenerator_panel.curveToMesh = True
        return{"FINISHED"}


def SetAttach(index, thisValue):

    print(thisValue, "VALUEPASSED")

    global testAttch1
    global testAttch0

    if(index == 1):
        testAttch0 = thisValue

    else:
        testAttch1 = thisValue



class SetBevel_Op(bpy.types.Operator):
    bl_idname = "view3d.set_bevel"
    bl_label = "SetBevel"

    def execute(self, context):

        muscleCore.bpy.context.object.data.bevel_factor_start = bpy.context.scene.bevel


class SetBevel2_Op(bpy.types.Operator):
    bl_idname = "view3d.set_bevel2"
    bl_label = "SetBevel"

    def execute(self, context):

        muscleCore.bpy.context.object.data.bevel_factor_end = bpy.context.scene.bevel2
        # return {'FINISHED'}


class SetTilt_Op(bpy.types.Operator):
    bl_idname = "view3d.set_tilt"
    bl_label = "SetTilt"

    def execute(self, context):

        if(not bpy.context.active_object.mode == 'EDIT'):
            bpy.ops.object.editmode_toggle()

        bpy.ops.curve.select_all(action='SELECT')
        tilt = bpy.context.scene.tilt * 0.0174533

        bpy.ops.curve.tilt_clear()
        bpy.ops.transform.tilt(value=tilt)



class Calculate_Volume_Op(bpy.types.Operator):
    bl_idname = "view3d.calculate_volume"
    bl_label = "CalculateVolume"

    def execute(self, context):
        
        from AddonFolder import globalVariables
        path =os.path.join(
            context.scene.conf_path,
            (context.scene.file_name + ".csv"))
        
        path = (os.path.realpath(bpy.path.abspath(path)))

        globalVariables.csvDir=path
        muscleCore.updateVolumes()
        return {'FINISHED'}



class Mirror_Cross_Section_Op(bpy.types.Operator):
    bl_idname = "view3d.mirror_cross_section"
    bl_label = "MirrorCrossSection"

    def execute(self, context):
        from AddonFolder import globalVariables
        muscleCore.mirror_bevel(globalVariables.muscleName)
        return {'FINISHED'}


class Reset_Variables_Op(bpy.types.Operator):
    bl_idname = "view3d.reset_variables"
    bl_label = "ResetVariables"

    def execute(self, context):

        from AddonFolder import globalVariables

        globalVariables.muscleName = ''
        globalVariables.attachment_centroids = [0, 0]
        globalVariables.attachment_normals = [0, 0]
        globalVariables.allMuscleParameters.clear()

        bpy.context.scene.muscle_Name = "Insert muscle name"
        bpy.context.scene.origin_object = None
        bpy.context.scene.insertion_object = None
        bpy.context.scene.tilt = 0
        bpy.context.scene.bevel = 0
        bpy.context.scene.bevel2 = 0

        myoGenerator_panel.parentMuscleGenerated = False
        myoGenerator_panel.originSubmitted = False
        myoGenerator_panel.insertionSubmitted = False
        myoGenerator_panel.vertexCountMatched = False
        myoGenerator_panel.curveCreated = False
        myoGenerator_panel.curveToMesh = False

        return {'FINISHED'}
