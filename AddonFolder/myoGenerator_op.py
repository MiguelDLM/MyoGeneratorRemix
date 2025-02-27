import math
import os
import sys
import bpy
import bmesh
import mathutils
from mathutils import Vector


from . import muscleCore, myoGenerator_panel, vertex_Counter

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
    bpy.ops.object.mode_set(mode='OBJECT')
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

    # Set the new object as active
    bpy.context.view_layer.objects.active = new_object
    new_object.select_set(True)

    # Switch to edit mode to remove doubles
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.region_to_loop()
    #separate the selected edges
    bpy.ops.mesh.separate(type='SELECTED')

    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    #rename the object 
    #get the last object created
    contour_object = bpy.context.selected_objects[-1]
    mesh_name = objName + "_" + mesh_name
    new_object.name = mesh_name
    contour_object.name = mesh_name + "_contour"


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

    def equalize_vertex_counts(self, obj_a, obj_b):
        """
        Equalizes the vertex counts of two MESH objects by subdividing edges efficiently.
        """
        # Get vertex counts
        count_a = len(obj_a.data.vertices)
        count_b = len(obj_b.data.vertices)

        # Calculate the difference
        diff = abs(count_a - count_b)

        if diff == 0:
            print("Both objects already have the same number of vertices.")
            return

        # Determine which object needs subdivision
        obj_to_subdivide = obj_a if count_a < count_b else obj_b

        # Switch to Edit Mode
        bpy.context.view_layer.objects.active = obj_to_subdivide
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj_to_subdivide.data)

        # Subdivide edges evenly to match vertex counts
        edges = bm.edges[:]

        # Calculate how many cuts are needed per edge
        total_edges = len(edges)
        cuts_per_edge = diff // total_edges
        extra_cuts = diff % total_edges  # Remainder

        # Subdivide edges
        if cuts_per_edge > 0:
            bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts_per_edge, use_grid_fill=True)

        if extra_cuts > 0:
            # Subdivide a subset of edges to distribute the remaining cuts
            edges_subset = edges[:extra_cuts]
            bmesh.ops.subdivide_edges(bm, edges=edges_subset, cuts=1, use_grid_fill=True)

        # Update mesh and switch back to Object Mode
        bmesh.update_edit_mesh(obj_to_subdivide.data)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Recalculate the vertex counts
        new_count_a = len(obj_a.data.vertices)
        new_count_b = len(obj_b.data.vertices)

        print(f"Vertex counts after subdivision: {new_count_a}, {new_count_b}")

    def reorder_vertices(self, obj):
        """
        Reorders the vertices of a MESH object for consistent indexing.
        """
        if obj.type != 'MESH':
            return

        # Switch to Edit Mode
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        # Get BMesh representation
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        # Start from a vertex and traverse connected edges
        vert_order = []
        visited = set()

        def traverse_vert(vert):
            visited.add(vert)
            vert_order.append(vert)
            linked_verts = [e.other_vert(vert) for e in vert.link_edges if e.other_vert(vert) not in visited]
            for v in linked_verts:
                traverse_vert(v)

        # Find a vertex with only two connected edges (start of open loop)
        start_vert = None
        for v in bm.verts:
            if len(v.link_edges) <= 2:
                start_vert = v
                break
        if not start_vert:
            start_vert = bm.verts[0]

        # Traverse vertices
        traverse_vert(start_vert)

        # Reassign indices
        for i, v in enumerate(vert_order):
            v.index = i

        bmesh.update_edit_mesh(obj.data)
        bpy.ops.object.mode_set(mode='OBJECT')

    def calculate_centroid_and_normal(self, obj):
        """
        Calculates the centroid and average normal of an object based on its vertices and faces.
        """
        # Calculate centroid
        vertices = [v.co for v in obj.data.vertices]
        centroid_local = sum(vertices, Vector()) / len(vertices)
        centroid_world = obj.matrix_world @ centroid_local  # Transform to world coordinates

        # Calculate average normal
        normals = []
        if len(obj.data.polygons) > 0:
            for poly in obj.data.polygons:
                normals.append(poly.normal)
            avg_normal = sum(normals, Vector()) / len(normals)
        else:
            # If no faces, estimate normal using vertex positions
            avg_normal = Vector((0, 0, 1))

        avg_normal_world = obj.matrix_world.to_3x3() @ avg_normal  # Transform to world coordinates

        return centroid_world, avg_normal_world

    def create_nurbs_curve(self, start_point, end_point, start_normal, end_normal, muscle_name):
        """
        Creates a NURBS curve with multiple control points between two points, influenced by normals.
        """
    
        # Calculate length between points
        line_length = (end_point - start_point).length
        scale_factor = 0.1 * line_length
    
        # Normalize normals
        start_normal_unit = start_normal.normalized()
        end_normal_unit = end_normal.normalized()
    
        # Calculate intermediate control points
        point1 = start_point + (start_normal_unit * scale_factor)
        point3 = end_point + (end_normal_unit * scale_factor)
        point2 = (point1 + point3) / 2
    
        # Create curve data
        curve_data = bpy.data.curves.new(name=muscle_name + "_curve_data", type='CURVE')
        curve_data.dimensions = '3D'
    
        # Create NURBS spline
        spline = curve_data.splines.new(type='NURBS')
        spline.points.add(count=4)
        spline.points[0].co = (*start_point, 1)
        spline.points[1].co = (*point1, 1)
        spline.points[2].co = (*point2, 1)
        spline.points[3].co = (*point3, 1)
        spline.points[4].co = (*end_point, 1)
        spline.order_u = 5
    
        # Create new curve object under a temporary name
        temp_name = "TEMP_" + muscle_name + "_curve"
        curve_obj = bpy.data.objects.new(temp_name, curve_data)
        bpy.context.collection.objects.link(curve_obj)
    
        # If there's already an object named <muscle_name>_curve, rename it
        existing_obj = bpy.data.objects.get(muscle_name + "_curve")
        if existing_obj:
            existing_obj.name = existing_obj.name + "_old"
    
        # Now rename to the desired final name
        curve_obj.name = muscle_name + "_curve"
        curve_data.name = muscle_name + "_curve_data"
    
        # Optionally refine the curve
        bpy.context.view_layer.objects.active = curve_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.curve.subdivide(number_cuts=2)
        bpy.ops.object.mode_set(mode='OBJECT')
        #clear location of the curve
        bpy.ops.object.location_clear(clear_delta=False)
        #set origin to geometry
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')    
        # set geometry to origin
        bpy.ops.object.location_clear(clear_delta=False)
        return curve_obj

    def remap_objects(self, obj, target_collection):
        """
        Moves the object to the target collection and unlinks it from the current collection.
        """
        for collection in obj.users_collection:
            collection.objects.unlink(obj)
        target_collection.objects.link(obj)
    def create_transition_mesh(self, obj_a, obj_b, curve_obj, muscle_name):

        
    def execute(self, context):
        # Get the muscle name
        muscle_name = bpy.context.scene.muscle_Name

        # Access the 'muscles' collection and specific muscle collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection or muscle_name not in muscles_collection.children:
            self.report({'ERROR'}, f"Collection '{muscle_name}' not found in 'muscles'")
            return {'CANCELLED'}
        target_collection = muscles_collection.children[muscle_name]

        # Get the origin and insertion objects
        origin_obj = target_collection.objects.get(muscle_name + "_origin_contour")
        insertion_obj = target_collection.objects.get(muscle_name + "_insertion_contour")

        if not origin_obj or not insertion_obj:
            self.report({'ERROR'}, "Required objects not found.")
            return {'CANCELLED'}

        # Ensure both are meshes
        if origin_obj.type != 'MESH':
            bpy.context.view_layer.objects.active = origin_obj
            bpy.ops.object.convert(target='MESH')
        if insertion_obj.type != 'MESH':
            bpy.context.view_layer.objects.active = insertion_obj
            bpy.ops.object.convert(target='MESH')

        # Reorder vertices
        self.reorder_vertices(origin_obj)
        self.reorder_vertices(insertion_obj)

        # Equalize vertex counts
        self.equalize_vertex_counts(origin_obj, insertion_obj)

        # Calculate centroids and normals
        origin_centroid, origin_normal = self.calculate_centroid_and_normal(origin_obj)
        insertion_centroid, insertion_normal = self.calculate_centroid_and_normal(insertion_obj)

        # Create NURBS curve with multiple control points
        curve_obj = self.create_nurbs_curve(origin_centroid, insertion_centroid, origin_normal, insertion_normal, muscle_name)

        # Move the curve to the target collection
        self.remap_objects(curve_obj, target_collection)

        # Create the transition mesh along the curve
        #mesh_obj = self.create_transition_mesh(origin_obj, insertion_obj, curve_obj, muscle_name)

        # Move the mesh to the target collection
        #self.remap_objects(mesh_obj, target_collection)

        self.report({'INFO'}, "Muscle creation completed successfully.")
        return {'FINISHED'}


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

        from . import globalVariables




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
        
        from . import globalVariables
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
        from . import globalVariables
        muscleCore.mirror_bevel(globalVariables.muscleName)
        return {'FINISHED'}


class Reset_Variables_Op(bpy.types.Operator):
    bl_idname = "view3d.reset_variables"
    bl_label = "ResetVariables"

    def execute(self, context):

        from . import globalVariables

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
