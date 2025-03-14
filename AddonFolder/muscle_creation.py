import bpy
import os
from mathutils import Vector
import bmesh
from .muscle_utilities import with_temp_object_active


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

    def initialize_geometry_nodes(self):
        """
        Initialize all required geometry node groups using the functions from geometry_node.py
        """
        from . import geometry_node
        
        # Check if the node groups already exist
        if "Loft-path" not in bpy.data.node_groups:
            # Create the node groups in the correct order (dependency order)
            loft_splines = geometry_node.loft_splines_node_group()
            instances_on_points = geometry_node.instances_on_points_node_group()
            loft_mesh = geometry_node.loft_mesh_node_group()
            index_rotation = geometry_node.index_rotation_node_group()
            loft_path = geometry_node.loft_path_node_group()
            
            print("Geometry node groups created successfully")
            return True
        else:
            print("Geometry node groups already exist")
            return False
    
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

        # Inside execute method of Muscle_Creation_Op
        # After creating the modifier
        
        # Import or use existing geometry nodes
        self.initialize_geometry_nodes()
        
        # Assign the geometry node loft-path to the muscle object
        muscle_obj.modifiers.new(name="Geometry Nodes", type='NODES')
        muscle_obj.modifiers["Geometry Nodes"].node_group = bpy.data.node_groups["Loft-path"]
        
        # Select the muscle object and set it as active
        bpy.ops.object.select_all(action='DESELECT')
        muscle_obj.select_set(True)
        bpy.context.view_layer.objects.active = muscle_obj
        
        # Get references to objects we'll assign to inputs
        curve_obj = bpy.data.objects.get(muscle_name + "_curve")
        origin_contour = bpy.data.objects.get(muscle_name + "_origin_contour")
        insertion_contour = bpy.data.objects.get(muscle_name + "_insertion_contour")
        
        # Check if any objects are missing
        if not curve_obj or not origin_contour or not insertion_contour:
            missing = []
            if not curve_obj: missing.append(f"{muscle_name}_curve")
            if not origin_contour: missing.append(f"{muscle_name}_origin_contour")
            if not insertion_contour: missing.append(f"{muscle_name}_insertion_contour")
            self.report({'WARNING'}, f"Objects not found: {', '.join(missing)}")
            # MOVED SOCKET ASSIGNMENT OUTSIDE THIS BLOCK
        
        # Configure the geometry node inputs - FIXED INDENTATION
        modifier = muscle_obj.modifiers["Geometry Nodes"]
        
        # Print all available sockets for debugging
        print("Available socket keys in geometry nodes:")
        for key in modifier.keys():
            print(f"  - {key}: {modifier[key]}")
        
        try:
            # IMPORTANT: Set input_name for consistency check
            socket_names = {
            "curve": "Socket_7", 
            "origin_contour": "Socket_10", 
            "insertion_contour": "Socket_11", 
            "resample": "Socket_2",  # Socket_2 used for resampling
            "subdivide": "Socket_3"
        }
            
            # Only try to assign objects that exist
            if curve_obj:
                modifier[socket_names["curve"]] = curve_obj
            if origin_contour:
                modifier[socket_names["origin_contour"]] = origin_contour
            if insertion_contour:
                modifier[socket_names["insertion_contour"]] = insertion_contour
            
            # Set numeric values
            modifier[socket_names["resample"]] = 80  # Resample Count
            modifier[socket_names["subdivide"]] = 10  # Subdivide value
            
            # Force updates several times
            for i in range(3):
                bpy.context.view_layer.update()
                muscle_obj.update_tag()
                
                # Check if assignments succeeded
                if curve_obj and modifier[socket_names["curve"]] == curve_obj:
                    print(f"Socket 'curve' assignment successful on attempt {i+1}")
                else:
                    print(f"Socket 'curve' assignment FAILED on attempt {i+1}")
                    # Try again
                    if curve_obj:
                        modifier[socket_names["curve"]] = curve_obj
            
        except Exception as e:
            self.report({'WARNING'}, f"Error configuring geometry nodes: {str(e)}")
        
        return {'FINISHED'}

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
    