import math
import os
import sys
import bpy
import bmesh
import mathutils
import csv
import os
from mathutils import Vector

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

        return {'FINISHED'}

def select_and_edit_object(obj):
    # Ensure the object is selected
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

    # Use a temporary override context to ensure the mode set operation is valid
    with bpy.context.temp_override(active_object=obj):
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

    # Deselect everything and select the contour object
    bpy.ops.object.select_all(action='DESELECT')
    contour_object.select_set(True)
    bpy.context.view_layer.objects.active = contour_object
    # Convert the contour object to a curve
    bpy.ops.object.convert(target='CURVE')

    #check the number of splines in the curve
    if len(contour_object.data.splines) > 1:
        #get the curve with the most points
        max_points = 0
        max_spline = None
        for spline in contour_object.data.splines:
            if len(spline.points) > max_points:
                max_points = len(spline.points)
                max_spline = spline
        #remove the other splines
        for spline in contour_object.data.splines:
            if spline != max_spline:
                contour_object.data.splines.remove(spline)
                # print the number of splines removed
                print("Spline removed")
            else:
                print("Spline not removed")





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

    def create_bezier_curve(self, start_point, end_point, start_normal, end_normal, muscle_name):
        """
        Crea una NURBS path con 5 puntos para representar el músculo, 
        posicionándolos según la orientación de start_point/end_point y sus normales.
        """
        line_length = (end_point - start_point).length
        if line_length == 0:
            line_length = 0.0001
    
        # Escala de la influencia de las normales
        scale_factor = 0.1 * line_length
    
        # Normaliza las normales para usarlas en cálculo de puntos intermedios
        if start_normal.length == 0:
            start_normal = Vector((0, 0, 1))
        if end_normal.length == 0:
            end_normal = Vector((0, 0, 1))
        start_normal_unit = start_normal.normalized()
        end_normal_unit = end_normal.normalized()
    
        # Calcula puntos intermedios
        point1 = start_point + (start_normal_unit * scale_factor)
        point3 = end_point + (end_normal_unit * scale_factor)
        mid_point = Vector((
            (point1.x + point3.x) / 2.0,
            (point1.y + point3.y) / 2.0,
            (point1.z + point3.z) / 2.0
        ))
    
        # Crea un NURBS path con 5 puntos
        bpy.ops.curve.primitive_nurbs_path_add(enter_editmode=False, align='WORLD')
        curve_obj = bpy.context.view_layer.objects.active
        curve_obj.name = muscle_name + "_curve"
        spline = curve_obj.data.splines[0]  # Hay un solo spline por defecto con 5 puntos
    
        # Asigna coordenadas a cada punto (el cuarto punto es index 4)
        spline.points[0].co = (start_point.x, start_point.y, start_point.z, 1)
        spline.points[1].co = (point1.x, point1.y, point1.z, 1)
        spline.points[2].co = (mid_point.x, mid_point.y, mid_point.z, 1)
        spline.points[3].co = (point3.x, point3.y, point3.z, 1)
        spline.points[4].co = (end_point.x, end_point.y, end_point.z, 1)
    
        # Subdivide algunos puntos en modo edición
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.select_all(action='DESELECT')
        # Subdivide entre [1] y [2]
        spline.points[1].select = True
        spline.points[2].select = True
        bpy.ops.curve.subdivide()
        # Subdivide entre [3] y [4]
        bpy.ops.curve.select_all(action='DESELECT')
        spline.points[3].select = True
        spline.points[4].select = True
        bpy.ops.curve.subdivide()
        bpy.ops.object.mode_set(mode='OBJECT')
    
        # Ajusta el origen a la geometría
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        return curve_obj

    def remap_objects(self, obj, target_collection):
        """
        Moves the object to the target collection and unlinks it from the current collection.
        """
        for collection in obj.users_collection:
            collection.objects.unlink(obj)
        target_collection.objects.link(obj)

    def import_geometry_nodes(self, target_collection):
        """
        Append all geometry nodes from the same folder of the addon
        """
        # Get the path of the current addon
        addon_path = os.path.dirname(os.path.realpath(__file__))
        # Get the path of the geometry node file
        geometry_node_path = os.path.join(addon_path, "geometry_node.blend")
        
        # Check if the node group already exists
        node_group_name = "Loft-path"  # Replace with the actual name of your node group
        if node_group_name in bpy.data.node_groups:
            print(f"Node group '{node_group_name}' already exists. Skipping import.")
            return
        
        # Append all geometry nodes
        with bpy.data.libraries.load(geometry_node_path) as (data_from, data_to):
            data_to.node_groups = [node_group for node_group in data_from.node_groups]
    
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
        origin_obj = target_collection.objects.get(muscle_name + "_origin")
        insertion_obj = target_collection.objects.get(muscle_name + "_insertion")


        if not origin_obj or not insertion_obj:
            self.report({'ERROR'}, "Required objects not found.")
            return {'CANCELLED'}

        # Calculate centroids and normals
        origin_centroid, origin_normal = self.calculate_centroid_and_normal(origin_obj)
        insertion_centroid, insertion_normal = self.calculate_centroid_and_normal(insertion_obj)

        # Create NURBS curve with multiple control points
        curve_obj = self.create_bezier_curve(origin_centroid, insertion_centroid, origin_normal, insertion_normal, muscle_name)

        # Duplicate the curve and set the name
        muscle_obj = curve_obj.copy()
        muscle_obj.data = curve_obj.data.copy()
        muscle_obj.name = muscle_name + "_muscle"
              
        # Move the curve to the target collection
        self.remap_objects(curve_obj, target_collection)
        self.remap_objects(muscle_obj, target_collection)

        # Import the geometry node
        self.import_geometry_nodes(target_collection)

        # Assign the geometry node loft-path to the muscle object
        muscle_obj.modifiers.new(name="Geometry Nodes", type='NODES')
        muscle_obj.modifiers["Geometry Nodes"].node_group = bpy.data.node_groups["Loft-path"]
        # deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        # select the muscle object and set it as active
        muscle_obj.select_set(True)
        bpy.context.view_layer.objects.active = muscle_obj

        # Configure the geometry node
        bpy.context.object.modifiers["Geometry Nodes"]["Socket_0"] = bpy.data.objects[muscle_name + "_curve"]
                #change to edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.object.modifiers["Geometry Nodes"]["Socket_3"] = bpy.data.objects[muscle_name + "_origin_contour"]
        bpy.context.object.modifiers["Geometry Nodes"]["Socket_4"] = bpy.data.objects[muscle_name + "_insertion_contour"]
        # clear the value of the input 2 and set the highest value
        bpy.context.object.modifiers["Geometry Nodes"]["Input_2"] = 80
        bpy.context.object.modifiers["Geometry Nodes"]["Input_3"] = 10
        #change to edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
        # select muscle curve and set it as active
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[muscle_name + "_curve"].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[muscle_name + "_curve"]
        bpy.ops.object.mode_set(mode='EDIT')
        #deselct all the points
        bpy.ops.curve.select_all(action='DESELECT')


        self.report({'INFO'}, "Muscle creation completed successfully.")
        return {'FINISHED'}

def with_temp_object_active(context, obj, action):
    """
    Helper function to:
      1. Store the current active object and mode
      2. Set 'obj' as active, switch to OBJECT mode
      3. Run 'action' callback
      4. Restore original active object and mode
    """
    original_active_obj = context.view_layer.objects.active
    original_mode = original_active_obj.mode if original_active_obj else 'OBJECT'

    # Switch to object mode and select our target
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj

    # Perform the custom action
    action()

    # Restore original selection and mode
    bpy.ops.object.select_all(action='DESELECT')
    if original_active_obj:
        original_active_obj.select_set(True)
        context.view_layer.objects.active = original_active_obj
        try:
            bpy.ops.object.mode_set(mode=original_mode)
        except RuntimeError:
            print("Couldn't restore previous mode (possibly invalid).")


def update_muscle_subdivision(self, context):
    muscle_name = context.scene.muscle_Name
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection or (muscle_name not in muscles_collection.children):
        print(f"Muscle collection '{muscle_name}' not found.")
        return
    muscle_obj = muscles_collection.children[muscle_name].objects.get(muscle_name + "_muscle")
    if not muscle_obj:
        print(f"Muscle object '{muscle_name}_muscle' not found.")
        return

    subdivision = context.scene.muscle_subdivisions

    def subdiv_action():
        if "Geometry Nodes" in muscle_obj.modifiers:
            muscle_obj.modifiers["Geometry Nodes"]["Input_3"] = subdivision
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("Geometry Nodes modifier not found on muscle object")

    with_temp_object_active(context, muscle_obj, subdiv_action)


def update_muscle_resampling(self, context):
    muscle_name = context.scene.muscle_Name
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection or (muscle_name not in muscles_collection.children):
        print(f"Muscle collection '{muscle_name}' not found.")
        return
    muscle_obj = muscles_collection.children[muscle_name].objects.get(muscle_name + "_muscle")
    if not muscle_obj:
        print(f"Muscle object '{muscle_name}_muscle' not found.")
        return

    resampling = context.scene.muscle_resampling

    def resample_action():
        if "Geometry Nodes" in muscle_obj.modifiers:
            muscle_obj.modifiers["Geometry Nodes"]["Input_2"] = resampling
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("Geometry Nodes modifier not found on muscle object")

    with_temp_object_active(context, muscle_obj, resample_action)

class Muscle_Volume_Creation_Op(bpy.types.Operator):
    bl_idname = "view3d.muscle_volume_creator"
    bl_label = "Muscle Volume Creation"

    def execute(self, context):
        # Get the muscle name
        muscle_name = context.scene.muscle_Name

        # Access the 'muscles' collection and specific muscle collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            print("Muscles collection not found")
            return
        if muscle_name not in muscles_collection.children:
            print(f"Muscle collection '{muscle_name}' not found in muscles collection")
            return
        target_collection = muscles_collection.children[muscle_name]

        # Get the muscle object
        muscle_obj = target_collection.objects.get(muscle_name + "_muscle")
        if not muscle_obj:
            print(f"Muscle object '{muscle_name}_muscle' not found in collection '{muscle_name}'")
            return

        # Get the origin and insertion objects
        origin_obj = target_collection.objects.get(muscle_name + "_origin")
        insertion_obj = target_collection.objects.get(muscle_name + "_insertion")
        if not origin_obj or not insertion_obj:
            print("Origin or insertion objects not found")
            return
        
        #change to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        # convert the muscle object to mesh

        muscle_obj.select_set(True)
        bpy.context.view_layer.objects.active = muscle_obj
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.edge_face_add()
        # change to object mode
        bpy.ops.object.editmode_toggle()

        return {'FINISHED'}
    
def update_origin_rotation(self, context):
    muscle_name = context.scene.muscle_Name
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection or (muscle_name not in muscles_collection.children):
        print(f"Muscle collection '{muscle_name}' not found.")
        return
    muscle_obj = muscles_collection.children[muscle_name].objects.get(muscle_name + "_muscle")
    if not muscle_obj:
        print(f"Muscle object '{muscle_name}_muscle' not found.")
        return

    origin_rotation = context.scene.origin_rotation

    def origin_rot_action():
        if "Geometry Nodes" in muscle_obj.modifiers:
            muscle_obj.modifiers["Geometry Nodes"]["Socket_1"] = origin_rotation
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("Geometry Nodes modifier not found on muscle object")

    with_temp_object_active(context, muscle_obj, origin_rot_action)

def update_insertion_rotation(self, context):
    muscle_name = context.scene.muscle_Name
    muscles_collection = bpy.data.collections.get("muscles")
    if not muscles_collection or (muscle_name not in muscles_collection.children):
        print(f"Muscle collection '{muscle_name}' not found.")
        return
    muscle_obj = muscles_collection.children[muscle_name].objects.get(muscle_name + "_muscle")
    if not muscle_obj:
        print(f"Muscle object '{muscle_name}_muscle' not found.")
        return

    insertion_rotation = context.scene.insertion_rotation

    def insertion_rot_action():
        if "Geometry Nodes" in muscle_obj.modifiers:
            muscle_obj.modifiers["Geometry Nodes"]["Socket_2"] = insertion_rotation
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("Geometry Nodes modifier not found on muscle object")

    with_temp_object_active(context, muscle_obj, insertion_rot_action)

class Swap_Origin_Insertion_Op(bpy.types.Operator):
    bl_idname = "view3d.swap_origin_insertion"
    bl_label = "Swap Origin and Insertion"

    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            print("Muscles collection not found")
            return {'CANCELLED'}
        if muscle_name not in muscles_collection.children:
            print(f"Muscle collection '{muscle_name}' not found in muscles collection")
            return {'CANCELLED'}
        target_collection = muscles_collection.children[muscle_name]

        muscle_obj = target_collection.objects.get(muscle_name + "_muscle")
        if not muscle_obj:
            print(f"Muscle object '{muscle_name}_muscle' not found in collection '{muscle_name}'")
            return {'CANCELLED'}

        def swap_action():
            if "Geometry Nodes" in muscle_obj.modifiers:
                socket_val = muscle_obj.modifiers["Geometry Nodes"]["Socket_5"]
                muscle_obj.modifiers["Geometry Nodes"]["Socket_5"] = not socket_val
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                print("Geometry Nodes modifier not found on muscle object")

        with_temp_object_active(context, muscle_obj, swap_action)
        return {'FINISHED'}


class Switch_Origin_Vertex_Order_Op(bpy.types.Operator):
    bl_idname = "view3d.switch_vertex_order_origin"
    bl_label = "Switch Origin Vertex Order"

    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            print("Muscles collection not found")
            return {'CANCELLED'}
        if muscle_name not in muscles_collection.children:
            print(f"Muscle collection '{muscle_name}' not found in muscles collection")
            return {'CANCELLED'}
        target_collection = muscles_collection.children[muscle_name]

        muscle_obj = target_collection.objects.get(muscle_name + "_muscle")
        if not muscle_obj:
            print(f"Muscle object '{muscle_name}_muscle' not found in collection '{muscle_name}'")
            return {'CANCELLED'}

        def switch_origin_action():
            if "Geometry Nodes" in muscle_obj.modifiers:
                socket_val = muscle_obj.modifiers["Geometry Nodes"]["Socket_6"]
                muscle_obj.modifiers["Geometry Nodes"]["Socket_6"] = not socket_val
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                print("Geometry Nodes modifier not found on muscle object")

        with_temp_object_active(context, muscle_obj, switch_origin_action)
        return {'FINISHED'}


class Switch_Insertion_Vertex_Order_Op(bpy.types.Operator):
    bl_idname = "view3d.switch_vertex_order_insertion"
    bl_label = "Switch Insertion Vertex Order"

    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            print("Muscles collection not found")
            return {'CANCELLED'}
        if muscle_name not in muscles_collection.children:
            print(f"Muscle collection '{muscle_name}' not found in muscles collection")
            return {'CANCELLED'}
        target_collection = muscles_collection.children[muscle_name]

        muscle_obj = target_collection.objects.get(muscle_name + "_muscle")
        if not muscle_obj:
            print(f"Muscle object '{muscle_name}_muscle' not found in collection '{muscle_name}'")
            return {'CANCELLED'}

        def switch_insertion_action():
            if "Geometry Nodes" in muscle_obj.modifiers:
                socket_val = muscle_obj.modifiers["Geometry Nodes"]["Socket_7"]
                muscle_obj.modifiers["Geometry Nodes"]["Socket_7"] = not socket_val
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                print("Geometry Nodes modifier not found on muscle object")

        with_temp_object_active(context, muscle_obj, switch_insertion_action)
        return {'FINISHED'}

class Next_Muscle_Op(bpy.types.Operator):
    bl_idname = "view3d.next_muscle"
    bl_label = "Next Muscle"
    bl_description = "Start the creation of the next muscle"

    def execute(self, context):
        # Clean the muscle name from the muscle panel
        bpy.context.scene.muscle_Name = "Insert muscle name"
        #Change to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}

class Calculate_Muscle_Parameters_Op(bpy.types.Operator):
    bl_idname = "view3d.calculate_muscle_parameters"
    bl_label = "Calculate Muscle Parameters"
    bl_description = "Calculate and export the muscle parameters"

    def calculate_volume(self, obj):
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.transform(obj.matrix_world)
        bmesh.ops.triangulate(bm, faces=bm.faces)

        volume = 0.0
        for f in bm.faces:
            if len(f.verts) >= 3:
                v1 = f.verts[0].co
                v2 = f.verts[1].co
                v3 = f.verts[2].co
                volume += v1.dot(v2.cross(v3)) / 6.0

        bm.free()
        return volume

    def calculate_area(self, obj):
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.transform(obj.matrix_world)
        bmesh.ops.triangulate(bm, faces=bm.faces)

        area = 0.0
        for f in bm.faces:
            area += f.calc_area()

        bm.free()
        return area

    def calculate_centroid(self, obj):
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.transform(obj.matrix_world)

        if not bm.verts:
            bm.free()
            return Vector((0.0, 0.0, 0.0))

        c = Vector((0.0, 0.0, 0.0))
        for v in bm.verts:
            c += v.co
        c /= len(bm.verts)
        bm.free()
        return c

    def calculate_curve_length(self, curve_obj):
        length = 0.0
        for spline in curve_obj.data.splines:
            length += spline.calc_length()
        return length

    def execute(self, context):
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection:
            self.report({'ERROR'}, "Collection 'muscles' not found.")
            return {'CANCELLED'}

        muscle_names = [child.name for child in muscles_collection.children]
        muscle_data = []

        for name in muscle_names:
            muscle_obj = bpy.data.objects.get(name + "_muscle")    # Malla del músculo
            curve_obj = bpy.data.objects.get(name + "_curve")      # Curva del músculo
            origin_obj = bpy.data.objects.get(name + "_origin")    # Malla de origen
            insertion_obj = bpy.data.objects.get(name + "_insertion")  # Malla de inserción

            if muscle_obj and muscle_obj.type == 'MESH' and curve_obj and curve_obj.type == 'CURVE':
                # Cálculo de volumen y longitud
                vol = abs(self.calculate_volume(muscle_obj))
                muscle_length = abs(self.calculate_curve_length(curve_obj))

                # Cálculo de áreas de origin e insertion (si existen)
                origin_area = 0.0
                insertion_area = 0.0
                if origin_obj and origin_obj.type == 'MESH':
                    origin_area = abs(self.calculate_area(origin_obj))
                if insertion_obj and insertion_obj.type == 'MESH':
                    insertion_area = abs(self.calculate_area(insertion_obj))

                # Cálculo de centroides y distancia lineal
                origin_centroid = Vector((0.0, 0.0, 0.0))
                insertion_centroid = Vector((0.0, 0.0, 0.0))
                if origin_obj and origin_obj.type == 'MESH':
                    origin_centroid = self.calculate_centroid(origin_obj)
                if insertion_obj and insertion_obj.type == 'MESH':
                    insertion_centroid = self.calculate_centroid(insertion_obj)
                linear_distance = (insertion_centroid - origin_centroid).length
                #remover el "vector" de los centroides y solo dejar los valores separados por comas
                origin_centroid = origin_centroid.to_tuple()
                insertion_centroid = insertion_centroid.to_tuple()
                origin_centroid = str(origin_centroid).replace("(","").replace(")","")
                insertion_centroid = str(insertion_centroid).replace("(","").replace(")","")


                # PCSA y Force
                pcsa = vol / muscle_length if muscle_length else 0.0
                force = pcsa * 0.3

                display_name = muscle_obj.name.replace("_muscle", "")
                muscle_data.append((
                    display_name,
                    vol,
                    muscle_length,
                    pcsa,
                    force,
                    origin_area,
                    insertion_area,
                    origin_centroid,
                    insertion_centroid,
                    linear_distance,
                ))

        output_path = bpy.path.abspath(context.scene.conf_path)
        csv_name = context.scene.file_name + ".csv"
        full_csv_path = os.path.join(output_path, csv_name)

        try:
            with open(full_csv_path, mode='w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([
                    "Muscle Name", "Volume", "Muscle Length", "PCSA",
                    "Force", "Origin Area", "Insertion Area",
                    "Origin Centroid", "Insertion Centroid", "Linear Distance"
                ])
                for row in muscle_data:
                    writer.writerow(row)
            self.report({'INFO'}, f"Muscle parameters exported to {full_csv_path}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to write file: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}
