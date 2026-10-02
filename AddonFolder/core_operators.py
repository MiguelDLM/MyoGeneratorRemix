"""
Core operators for the MyoGeneratorRemix addon.
Contains essential operators that support the old workflow interface.
"""

import os

import bpy
import bmesh

from . import muscle_metrics, myo_record
from .muscle_utilities import select_and_edit_object


class Muscle_Name_Submition(bpy.types.Operator):
    """Submit muscle name and create collection"""
    bl_idname = "myogen.submit_muscle"
    bl_label = "Submit Muscle Name"
    bl_description = "Submit Muscle Name"

    def execute(self, context):
        objName = context.scene.myogen.muscle_name
        muscles_collection = myo_record.get_root(create=True, scene=context.scene)

        if objName in muscles_collection.children:
            self.report({'WARNING'}, f"Muscle '{objName}' already exists, choose a different name.")
            return {'CANCELLED'}
        if bpy.data.collections.get(objName) is not None:
            self.report({'WARNING'}, f"A collection named '{objName}' already exists elsewhere in the file, "
                                     "choose a different name.")
            return {'CANCELLED'}

        new_collection = bpy.data.collections.new(objName)
        muscles_collection.children.link(new_collection)
        new_collection["myo_schema"] = myo_record.SCHEMA_VERSION
        new_collection["myo_name"] = objName
        new_collection["myo_side"] = myo_record.parse_side(objName)
        return {'FINISHED'}


def _owning_muscle_collection(obj):
    """The MyoGen muscle collection an object belongs to, or None."""
    root = myo_record.get_root()
    if root is None:
        return None
    for col in obj.users_collection:
        if root.children.get(col.name) is col:
            return col
    return None


class Estimate_Selected_Volumes_Op(bpy.types.Operator):
    """Estimate summed volume of selected mesh objects"""
    bl_idname = "myogen.estimate_selected_volumes"
    bl_label = "Estimate Selected Volumes"
    bl_description = "Estimate the total volume, mass and PCSA of the selected mesh objects"

    def execute(self, context):
        props = context.scene.myogen
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "No mesh objects selected")
            props.advanced_selected_volume = 0.0
            props.advanced_selected_mass = 0.0
            props.advanced_selected_pcsa = ""
            return {'CANCELLED'}

        mpu = myo_record.metres_per_unit(context.scene)
        total_volume_m3 = 0.0
        total_pcsa_m2 = 0.0
        skipped = []
        for obj in selected:
            vol_bu, _signed, _area, _c, _closed = myo_record.mesh_stats(obj)
            vol_m3 = vol_bu * mpu ** 3
            total_volume_m3 += vol_m3

            coll = _owning_muscle_collection(obj)
            path = myo_record.resolve_objects(coll).get("path") if coll else None
            path_m = myo_record.curve_length(path) * mpu if path else 0.0
            if path_m <= 0.0:
                skipped.append(obj.name)
                continue
            pcsa_m2, _lf = myo_record.pcsa_from_volume(vol_m3, path_m, props.fiber_length_ratio,
                                                       props.pennation_deg)
            total_pcsa_m2 += pcsa_m2

        props.advanced_selected_volume = total_volume_m3
        props.advanced_selected_mass = total_volume_m3 * props.density_g_cm3 * 1000.0
        text = f"Total PCSA: {total_pcsa_m2 * 1e4:.4f} cm²"
        if skipped:
            text += f" ({len(skipped)} without path curve skipped)"
        props.advanced_selected_pcsa = text
        return {'FINISHED'}


def _mirror_curve_data(curve, axis_idx):
    for spline in curve.splines:
        for p in spline.bezier_points:
            for attr in ("co", "handle_left", "handle_right"):
                v = getattr(p, attr).copy()
                v[axis_idx] = -v[axis_idx]
                setattr(p, attr, v)
        for p in spline.points:
            co = p.co.copy()
            co[axis_idx] = -co[axis_idx]
            p.co = co


_SIDE_SWAP = (("_left", "_right"), ("_right", "_left"), ("_l", "_r"), ("_r", "_l"))


def _swap_side(name):
    """'temp_sup_left' -> 'temp_sup_right' (None if the name has no side suffix)."""
    low = name.lower()
    for a, b in _SIDE_SWAP:
        if low.endswith(a):
            return name[: -len(a)] + b
    return None


class MYOGENERATOR_OT_mirror_duplicate(bpy.types.Operator):
    """Duplicate selected objects mirrored across chosen axis (X/Y/Z)"""
    bl_idname = "myogen.mirror_duplicate"
    bl_label = "Mirror Duplicate"
    bl_description = ("Duplicate the selected objects mirrored across the chosen axis. Objects of a "
                      "muscle named *_left/*_right go to the opposite-side muscle collection, "
                      "which is created if needed")

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis to mirror across",
        items=[('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')],
        default='X'
    )

    def _target_collections(self, context, obj):
        """(collections to link the copy to, new object name)."""
        src = _owning_muscle_collection(obj)
        other = _swap_side(src.name) if src else None
        if not other:
            return list(obj.users_collection), obj.name + "_mirror"
        root = myo_record.get_root(create=True, scene=context.scene)
        dst = root.children.get(other)
        if dst is None:
            dst = bpy.data.collections.new(other)
            root.children.link(dst)
            dst["myo_schema"] = myo_record.SCHEMA_VERSION
            dst["myo_name"] = other
            dst["myo_side"] = myo_record.parse_side(other)
        new_name = other + obj.name[len(src.name):] if obj.name.startswith(src.name) else obj.name + "_mirror"
        return [dst], new_name

    def execute(self, context):
        sel = [o for o in context.selected_objects if o is not None]
        if not sel:
            self.report({'WARNING'}, "No objects selected to mirror")
            return {'CANCELLED'}

        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}.get(self.axis, 0)
        created = []
        for o in sel:
            o.select_set(False)

        for obj in sel:
            collections, new_name = self._target_collections(context, obj)
            if any(c.objects.get(new_name) for c in collections):
                self.report({'WARNING'}, f"'{new_name}' already exists: '{obj.name}' not mirrored")
                continue

            new_obj = obj.copy()
            new_obj.name = new_name
            if obj.data is not None:
                data = obj.data.copy()
                if isinstance(data, bpy.types.Mesh):
                    bm = bmesh.new()
                    bm.from_mesh(data)
                    for vert in bm.verts:
                        vert.co[axis_idx] = -vert.co[axis_idx]
                    # Mirroring flips the winding; reverse faces to keep normals outward.
                    bmesh.ops.reverse_faces(bm, faces=bm.faces)
                    bm.normal_update()
                    bm.to_mesh(data)
                    bm.free()
                    data.update()
                elif isinstance(data, bpy.types.Curve):
                    _mirror_curve_data(data, axis_idx)
                new_obj.data = data

            for col in collections:
                col.objects.link(new_obj)

            loc = obj.location.copy()
            loc[axis_idx] = -loc[axis_idx]
            new_obj.location = loc
            new_obj.select_set(True)
            created.append(new_obj)

        if created:
            context.view_layer.objects.active = created[-1]
        self.report({'INFO'}, f"Created {len(created)} mirrored objects")
        return {'FINISHED'}


class Select_Origin_Op(bpy.types.Operator):
    """Select origin faces"""
    bl_idname = "myogen.select_origin"
    bl_label = "Select Origin"
    bl_description = "Select Origin of the muscle"

    def execute(self, context):
        select_and_edit_object(context.scene.myogen.origin_object)
        return {'FINISHED'}


class Select_Insertion_Op(bpy.types.Operator):
    """Select insertion faces"""
    bl_idname = "myogen.select_insertion"
    bl_label = "Select Insertion"
    bl_description = "Select Insertion of the muscle"

    def execute(self, context):
        select_and_edit_object(context.scene.myogen.insertion_object)
        return {'FINISHED'}


def create_mesh_from_selected_faces(operator, mesh_name):
    """Turn the faces selected on a bone into an attachment surface and its contour.

    Creates ``<M>_<mesh_name>`` (the faces, world space, ``myo_role`` =
    ``mesh_name``) and ``<M>_<mesh_name>_contour`` (its boundary as a closed
    curve, role ``<mesh_name>_contour``) inside ``muscles/<M>``, where ``M`` is
    ``scene.myogen.muscle_name``.

    :arg operator: Calling operator (for reports).
    :type operator: :class:`bpy.types.Operator`
    :arg mesh_name: ``'origin'`` or ``'insertion'``.
    :type mesh_name: str
    """
    # Get active object
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        operator.report({'ERROR'}, "No active mesh object")
        return
    
    muscle_name = bpy.context.scene.myogen.muscle_name

    # Get or create muscle collection
    muscles_collection = myo_record.get_root()
    if not muscles_collection:
        operator.report({'ERROR'}, "Muscles collection not found")
        return
    
    if muscle_name not in muscles_collection.children:
        operator.report({'ERROR'}, f"Muscle collection '{muscle_name}' not found")
        return
    
    target_collection = muscles_collection.children[muscle_name]
    
    # Check if objects already exist
    existing_mesh = target_collection.objects.get(f"{muscle_name}_{mesh_name}")
    existing_contour = target_collection.objects.get(f"{muscle_name}_{mesh_name}_contour")
    
    if existing_mesh or existing_contour:
        operator.report({'WARNING'}, f"Object '{mesh_name}' already exists in collection '{muscle_name}'")
        return
    
    # Get the BMesh representation
    bm = bmesh.from_edit_mesh(obj.data)
    
    # Find the selected faces
    selected_faces = [face for face in bm.faces if face.select]
    
    if not selected_faces:
        operator.report({'WARNING'}, "No faces selected")
        return
    
    # Create a new mesh and object for the surface
    new_mesh = bpy.data.meshes.new(f"{muscle_name}_{mesh_name}")
    new_object = bpy.data.objects.new(f"{muscle_name}_{mesh_name}", new_mesh)
    
    # Create a new BMesh for the new object
    new_bm = bmesh.new()
    
    # Copy selected faces to the new BMesh with world coordinates, sharing
    # vertices between faces (a connected surface with a real boundary).
    vert_map = {}
    for face in selected_faces:
        world_verts = []
        for vert in face.verts:
            if vert.index not in vert_map:
                vert_map[vert.index] = new_bm.verts.new(obj.matrix_world @ vert.co)
            world_verts.append(vert_map[vert.index])
        new_face = new_bm.faces.new(world_verts)
        new_face.normal_update()
    
    # Finish up the new BMesh
    new_bm.to_mesh(new_mesh)
    new_bm.free()
    
    # Add the new object to the target collection
    target_collection.objects.link(new_object)
    new_object[myo_record.ROLE_KEY] = mesh_name
    
    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Set the new object as active and selected
    bpy.ops.object.select_all(action='DESELECT')
    new_object.select_set(True)
    bpy.context.view_layer.objects.active = new_object
    
    # Now duplicate this object to create the contour
    bpy.ops.object.duplicate()
    
    # Get the duplicated object (should be the active object now)
    contour_object = bpy.context.active_object
    contour_object.name = f"{muscle_name}_{mesh_name}_contour"
    contour_object[myo_record.ROLE_KEY] = f"{mesh_name}_contour"
    
    # Move contour to target collection
    for collection in contour_object.users_collection:
        collection.objects.unlink(contour_object)
    target_collection.objects.link(contour_object)
    
    # Switch to edit mode to extract boundary loop
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.region_to_loop()
    
    # Separate the selected edges (boundary loop)
    bpy.ops.mesh.separate(type='SELECTED')
    
    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # After separate, we have two objects:
    # 1. contour_object (the original faces, now without boundary)  
    # 2. boundary_object (just the boundary loop)
    # We want to keep only the boundary_object and remove the faces
    
    # Find the boundary object (the newly created one with boundary loop)
    boundary_object = None
    for selected_obj in bpy.context.selected_objects:
        if selected_obj != contour_object:
            boundary_object = selected_obj
            break
    
    if boundary_object:
        # Remove the original contour object (the solid faces - we don't need them)
        bpy.data.objects.remove(contour_object, do_unlink=True)
        
        # The boundary object becomes our contour
        contour_object = boundary_object
        contour_object.name = f"{muscle_name}_{mesh_name}_contour"
        
        # Move to target collection
        for collection in contour_object.users_collection:
            collection.objects.unlink(contour_object)
        target_collection.objects.link(contour_object)
        
        # Select only the contour object and convert to curve
        bpy.ops.object.select_all(action='DESELECT')
        contour_object.select_set(True)
        bpy.context.view_layer.objects.active = contour_object
        
        # Convert to curve
        bpy.ops.object.convert(target='CURVE')
        
        # Now that it's a curve, clean up splines - keep only the largest spline if multiple exist
        if hasattr(contour_object.data, 'splines') and len(contour_object.data.splines) > 1:
            max_points = 0
            max_spline = None
            for spline in contour_object.data.splines:
                points_count = len(spline.points) if spline.type in ['NURBS', 'POLY'] else len(spline.bezier_points)
                if points_count > max_points:
                    max_points = points_count
                    max_spline = spline
            
            # Remove other splines
            splines_to_remove = [spline for spline in contour_object.data.splines if spline != max_spline]
            for spline in splines_to_remove:
                contour_object.data.splines.remove(spline)
        
        # Make sure the curve is cyclic (closed)
        if hasattr(contour_object.data, 'splines') and len(contour_object.data.splines) > 0:
            contour_object.data.splines[0].use_cyclic_u = True
        contour_object[myo_record.ROLE_KEY] = f"{mesh_name}_contour"
    else:
        # If no boundary object found, something went wrong
        operator.report({'WARNING'}, "Could not extract boundary loop properly")
    
    operator.report({'INFO'}, f"Created mesh '{muscle_name}_{mesh_name}' and contour curve")
    
    # Return to object mode and deselect all
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')


class Submit_Origin_Op(bpy.types.Operator):
    """Submit origin selection"""
    bl_idname = "myogen.submit_origin"
    bl_label = "Submit Origin"
    bl_description = "Submit Origin of the muscle"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'EDIT'

    def execute(self, context):
        create_mesh_from_selected_faces(self, "origin")
        return {'FINISHED'}


class Submit_Insertion_Op(bpy.types.Operator):
    """Submit insertion selection"""
    bl_idname = "myogen.submit_insertion"
    bl_label = "Submit Insertion"
    bl_description = "Submit Insertion of the muscle"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'EDIT'

    def execute(self, context):
        create_mesh_from_selected_faces(self, "insertion")
        return {'FINISHED'}


class Next_Muscle_Op(bpy.types.Operator):
    """Move to next muscle"""
    bl_idname = "myogen.next_muscle"
    bl_label = "Next Muscle"
    bl_description = "Start the creation of the next muscle"

    def execute(self, context):
        context.scene.myogen.muscle_name = "Insert muscle name"
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}


def _report_findings(operator, rows, scene_findings):
    worst = myo_record.worst_level(scene_findings + [f for r in rows for f in r["qa"]])
    errors = [m for lvl, m in scene_findings if lvl == myo_record.QA_ERROR]
    if errors:
        operator.report({'WARNING'}, errors[0])
    flagged = [r["collection"] for r in rows if myo_record.worst_level(r["qa"]) in
               (myo_record.QA_WARNING, myo_record.QA_ERROR)]
    if flagged:
        operator.report({'WARNING'}, f"Check {len(flagged)} muscle(s) in the QA box: {', '.join(flagged)}")
    return worst


class Check_Muscles_Op(bpy.types.Operator):
    """Run the plausibility checks without exporting"""
    bl_idname = "myogen.check_muscles"
    bl_label = "Check Muscles"
    bl_description = ("Measure every muscle, store the results in the muscle records and flag "
                      "implausible scales, volumes, lengths or parameters")

    def execute(self, context):
        rows, scene_findings = muscle_metrics.compute_muscles(context, write=True)
        if not rows:
            self.report({'WARNING'}, "No MyoGen muscles found in the 'muscles' collection")
            return {'CANCELLED'}
        worst = _report_findings(self, rows, scene_findings)
        if worst in (myo_record.QA_OK, myo_record.QA_INFO):
            self.report({'INFO'}, f"{len(rows)} muscles checked, nothing suspicious")
        return {'FINISHED'}


class Set_Unit_Scale_Op(bpy.types.Operator):
    """Set the scene unit scale"""
    bl_idname = "myogen.set_unit_scale"
    bl_label = "Set Unit Scale"
    bl_description = "Declare what one Blender unit is in the real specimen"
    bl_options = {'REGISTER', 'UNDO'}

    unit: bpy.props.EnumProperty(
        name="1 Blender unit =",
        description="Real length of one Blender unit in the specimen model",
        items=[('MILLIMETERS', "1 mm", "Model built in millimetres (Unit Scale 0.001)"),
               ('CENTIMETERS', "1 cm", "Model built in centimetres (Unit Scale 0.01)"),
               ('METERS', "1 m", "Model built in metres (Unit Scale 1.0)")],
        default='MILLIMETERS')

    def execute(self, context):
        us = context.scene.unit_settings
        us.system = 'METRIC'
        us.scale_length = {'MILLIMETERS': 0.001, 'CENTIMETERS': 0.01, 'METERS': 1.0}[self.unit]
        us.length_unit = self.unit
        self.report({'INFO'}, f"Unit Scale set to {us.scale_length:g} (1 BU = {self.unit.lower()[:-1]})")
        return {'FINISHED'}


class Calculate_Muscle_Parameters_Op(bpy.types.Operator):
    """Calculate muscle parameters and save to CSV"""
    bl_idname = "myogen.calculate_muscle_parameters"
    bl_label = "Calculate Muscle Parameters"
    bl_description = ("Measure every muscle (volume, mass, lengths, areas, PCSA, force), store the "
                      "muscle records in the .blend and export them to CSV")

    def execute(self, context):
        props = context.scene.myogen
        folder_path, file_name = props.conf_path, props.file_name
        if not folder_path or not file_name:
            self.report({'ERROR'}, "Please specify folder path and file name")
            return {'CANCELLED'}
        folder_path = bpy.path.abspath(folder_path)
        try:
            os.makedirs(folder_path, exist_ok=True)
        except OSError as e:
            self.report({'ERROR'}, f"Cannot create directory '{folder_path}': {e}")
            return {'CANCELLED'}
        csv_path = os.path.join(folder_path, file_name + ".csv")

        rows, scene_findings = muscle_metrics.compute_muscles(context, write=True)
        if not rows:
            self.report({'ERROR'}, "No MyoGen muscles found in the 'muscles' collection")
            return {'CANCELLED'}

        try:
            muscle_metrics.write_csv(csv_path, rows)
        except OSError as e:
            self.report({'ERROR'}, f"Failed to save CSV '{csv_path}': {e}")
            return {'CANCELLED'}

        _report_findings(self, rows, scene_findings)
        self.report({'INFO'}, f"Muscle parameters of {len(rows)} muscles saved to {csv_path}")
        return {'FINISHED'}
