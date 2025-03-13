import bpy
import bmesh
import csv
import os
from mathutils import Vector


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
