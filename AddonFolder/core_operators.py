"""
Core operators for the MyoGeneratorRemix addon.
Contains essential operators that support the old workflow interface.
"""

import os

import bpy
import bmesh

from . import muscle_metrics, myo_record
from .muscle_utilities import select_and_edit_object
from .modes import to_object_mode
from .muscle_texture import create_ligament_material


class Muscle_Name_Submition(bpy.types.Operator):
    """Submit muscle name and create collection"""
    bl_idname = "myogen.submit_muscle"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Submit Muscle Name"
    bl_description = "Submit Muscle Name"

    def execute(self, context):
        create_ligament_material()
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
        if hasattr(context.scene.myogen, "active_muscle"):
            context.scene.myogen.active_muscle = objName
        return {'FINISHED'}


def _owning_muscle_collection(obj):
    """The MyoGen muscle collection an object belongs to, or None."""
    root = myo_record.get_root()
    for col in obj.users_collection:
        if root and root.children.get(col.name) is col:
            return col
        if myo_record.is_muscle_collection(col):
            return col
    return None


class Estimate_Selected_Volumes_Op(bpy.types.Operator):
    """Estimate summed volume of selected mesh objects"""
    bl_idname = "myogen.estimate_selected_volumes"
    bl_options = {'REGISTER', 'UNDO'}
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
    bl_options = {'REGISTER', 'UNDO'}
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
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Select Origin"
    bl_description = "Select Origin of the muscle"

    def execute(self, context):
        bone = context.scene.myogen.origin_object
        if bone is None:
            m_name = context.scene.myogen.muscle_name
            root = myo_record.get_root()
            coll = (root.children.get(m_name) if root else None) or bpy.data.collections.get(m_name)
            if coll and coll.get("myo_origin_bone"):
                bone = bpy.data.objects.get(coll["myo_origin_bone"])
                if bone:
                    context.scene.myogen.origin_object = bone
        if bone is None:
            self.report({'ERROR'}, "Please specify the Origin Bone first")
            return {'CANCELLED'}
        select_and_edit_object(bone)
        return {'FINISHED'}


class Select_Insertion_Op(bpy.types.Operator):
    """Select insertion faces"""
    bl_idname = "myogen.select_insertion"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Select Insertion"
    bl_description = "Select Insertion of the muscle"

    def execute(self, context):
        bone = context.scene.myogen.insertion_object
        if bone is None:
            m_name = context.scene.myogen.muscle_name
            root = myo_record.get_root()
            coll = (root.children.get(m_name) if root else None) or bpy.data.collections.get(m_name)
            if coll and coll.get("myo_insertion_bone"):
                bone = bpy.data.objects.get(coll["myo_insertion_bone"])
                if bone:
                    context.scene.myogen.insertion_object = bone
        if bone is None:
            self.report({'ERROR'}, "Please specify the Insertion Bone first")
            return {'CANCELLED'}
        select_and_edit_object(bone)
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

    # Get muscle collection (in root or outside root)
    root = myo_record.get_root()
    target_collection = None
    if root and muscle_name in root.children:
        target_collection = root.children[muscle_name]
    else:
        candidate = bpy.data.collections.get(muscle_name)
        if candidate is not None and myo_record.is_muscle_collection(candidate):
            target_collection = candidate

    if not target_collection:
        operator.report({'ERROR'}, f"Muscle collection '{muscle_name}' not found")
        return
    
    # Check if objects already exist; remove them to allow clean update/replacement
    existing_mesh = target_collection.objects.get(f"{muscle_name}_{mesh_name}")
    existing_contour = target_collection.objects.get(f"{muscle_name}_{mesh_name}_contour")
    is_update = bool(existing_mesh or existing_contour)
    if existing_mesh:
        data = existing_mesh.data
        bpy.data.objects.remove(existing_mesh, do_unlink=True)
        if data and data.users == 0:
            bpy.data.meshes.remove(data)
    if existing_contour:
        data = existing_contour.data
        bpy.data.objects.remove(existing_contour, do_unlink=True)
        if data and data.users == 0:
            bpy.data.curves.remove(data)

    target_collection[f"myo_{mesh_name}_bone"] = obj.name
    
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
    to_object_mode()
    
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
    to_object_mode()
    
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
    
    action_text = "Updated" if is_update else "Created"
    operator.report({'INFO'}, f"{action_text} mesh '{muscle_name}_{mesh_name}' and contour curve")
    
    # Return to object mode and deselect all
    to_object_mode()
    bpy.ops.object.select_all(action='DESELECT')

    from . import volume_builder
    if bpy.context.scene.myogen.preview_live:
        volume_builder.schedule_rebuild(bpy.context)


class Submit_Origin_Op(bpy.types.Operator):
    """Submit origin selection"""
    bl_idname = "myogen.submit_origin"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Submit Origin"
    bl_description = "Submit Origin of the muscle"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'EDIT'

    def execute(self, context):
        create_ligament_material()
        create_mesh_from_selected_faces(self, "origin")
        return {'FINISHED'}


class Submit_Insertion_Op(bpy.types.Operator):
    """Submit insertion selection"""
    bl_idname = "myogen.submit_insertion"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Submit Insertion"
    bl_description = "Submit Insertion of the muscle"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'EDIT'

    def execute(self, context):
        create_ligament_material()
        create_mesh_from_selected_faces(self, "insertion")
        return {'FINISHED'}


class Next_Muscle_Op(bpy.types.Operator):
    """Move to next muscle"""
    bl_idname = "myogen.next_muscle"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Next Muscle"
    bl_description = "Start the creation of the next muscle"

    def execute(self, context):
        create_ligament_material()
        from . import volume_builder
        volume_builder.stop_live(context)
        context.scene.myogen.preview_status = ""
        if hasattr(context.scene.myogen, "active_muscle"):
            context.scene.myogen.active_muscle = ""
        context.scene.myogen.muscle_name = "Insert muscle name"
        to_object_mode(context)
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}


class Create_Ligament_Material_Op(bpy.types.Operator):
    """Create or get the procedural ligament material in the scene"""
    bl_idname = "myogen.create_ligament_material"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Create Ligament Material"
    bl_description = ("Create the procedural ligament material with dense collagen striations and "
                      "subsurface scattering so it can be assigned to other elements")

    def execute(self, context):
        mat = create_ligament_material()
        self.report({'INFO'}, f"Material '{mat.name}' is available")
        return {'FINISHED'}


def _find_attachment_bone(att_obj, context, default_bone=None):
    """Find the bone mesh that an attachment surface lies on.

    :arg att_obj: Attachment surface mesh object.
    :type att_obj: :class:`bpy.types.Object`
    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg default_bone: Fallback bone object.
    :type default_bone: :class:`bpy.types.Object` or None
    :return: Best matching bone mesh object, or default_bone.
    :rtype: :class:`bpy.types.Object` or None
    """
    if att_obj is None or att_obj.type != 'MESH':
        return default_bone

    props = context.scene.myogen
    candidates = []
    for b in (default_bone, props.origin_object, props.insertion_object):
        if b is not None and b.type == 'MESH' and b not in candidates:
            candidates.append(b)

    bones_coll = bpy.data.collections.get("bones")
    if bones_coll:
        for b in bones_coll.objects:
            if b.type == 'MESH' and b not in candidates:
                candidates.append(b)

    if not candidates:
        for b in bpy.data.objects:
            if b.type == 'MESH' and b not in candidates:
                if not any(b.name.endswith(s) for s in ("_muscle", "_origin", "_insertion", "_preview",
                                                        "_tube", "_fibres", "_contour")):
                    candidates.append(b)

    if not candidates:
        return default_bone

    from . import preview
    from mathutils import Vector
    att_center = att_obj.matrix_world @ (sum((Vector(p) for p in att_obj.bound_box), Vector()) / 8.0)
    best_bone, best_dist = default_bone, float('inf')
    for b in candidates:
        try:
            tree = preview._bone_tree(b)
            hit = tree.find_nearest(att_center)
            dist = hit[3] if hit[0] is not None else float('inf')
        except Exception:
            dist = float('inf')
        if dist < best_dist:
            best_dist = dist
            best_bone = b

    return best_bone or default_bone


class Recall_Attachment_Faces_Op(bpy.types.Operator):
    """Select the attachment faces on the bone in Edit Mode to allow adjustments"""
    bl_idname = "myogen.recall_attachment"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Edit Attachment Faces"
    bl_description = ("Select the faces on the bone that currently form this attachment, "
                      "allowing you to add or remove faces before re-submitting")

    role: bpy.props.StringProperty(
        name="Attachment Role",
        description="Attachment to edit ('origin' or 'insertion')",
        default="origin",
    )

    def execute(self, context):
        role = self.role.lower()
        from . import preview
        coll, objs = preview.muscle_objects(context)
        if coll is None:
            name = context.scene.myogen.muscle_name.strip()
            coll = bpy.data.collections.get(name)
            if coll is not None and myo_record.is_muscle_collection(coll):
                objs = myo_record.resolve_objects(coll)
            else:
                coll = None
        if coll is None:
            self.report({'ERROR'}, f"Collection '{context.scene.myogen.muscle_name}' not found")
            return {'CANCELLED'}

        att_obj = objs.get(role)
        if att_obj is None or att_obj.type != 'MESH':
            self.report({'ERROR'}, f"No existing {role} surface found to edit")
            return {'CANCELLED'}

        bone_name = coll.get(f"myo_{role}_bone")
        bone_obj = bpy.data.objects.get(bone_name) if bone_name else None
        bone_obj = _find_attachment_bone(att_obj, context,
                                         default_bone=bone_obj or getattr(context.scene.myogen, f"{role}_object", None))
        if bone_obj is None or bone_obj.type != 'MESH':
            self.report({'ERROR'}, f"Please select the {role} bone object first")
            return {'CANCELLED'}

        coll[f"myo_{role}_bone"] = bone_obj.name
        setattr(context.scene.myogen, f"{role}_object", bone_obj)

        to_object_mode(context)
        poly_count = len(bone_obj.data.polygons)
        bone_obj.data.polygons.foreach_set('select', [False] * poly_count)

        att_mesh = att_obj.data
        matched = 0
        if len(att_mesh.polygons) > 0:
            from mathutils import Vector
            from mathutils.kdtree import KDTree
            inv_matrix = bone_obj.matrix_world.inverted()
            kd = KDTree(len(att_mesh.polygons))
            for i, poly in enumerate(att_mesh.polygons):
                kd.insert(inv_matrix @ (att_obj.matrix_world @ poly.center), i)
            kd.balance()

            att_local_corners = [inv_matrix @ (att_obj.matrix_world @ Vector(b)) for b in att_obj.bound_box]
            margin = 1.0
            min_c = Vector((min(p.x for p in att_local_corners) - margin,
                            min(p.y for p in att_local_corners) - margin,
                            min(p.z for p in att_local_corners) - margin))
            max_c = Vector((max(p.x for p in att_local_corners) + margin,
                            max(p.y for p in att_local_corners) + margin,
                            max(p.z for p in att_local_corners) + margin))

            for p in bone_obj.data.polygons:
                c = p.center
                if min_c.x <= c.x <= max_c.x and min_c.y <= c.y <= max_c.y and min_c.z <= c.z <= max_c.z:
                    _co, _idx, dist = kd.find(c)
                    if dist < 1e-4:
                        p.select = True
                        matched += 1

        for o in context.view_layer.objects:
            o.select_set(False)
        bone_obj.hide_viewport = False
        bone_obj.hide_set(False)
        bone_obj.select_set(True)
        context.view_layer.objects.active = bone_obj
        context.tool_settings.mesh_select_mode = (False, False, True)

        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except RuntimeError:
            to_object_mode(context)
            bone_obj.select_set(True)
            context.view_layer.objects.active = bone_obj
            bpy.ops.object.mode_set(mode='EDIT')

        self.report({'INFO'}, f"Selected {matched} {role} faces on '{bone_obj.name}'. Adjust selection and Submit.")
        return {'FINISHED'}


class Rename_Muscle_Op(bpy.types.Operator):
    """Rename the current muscle, its collection, objects and records"""
    bl_idname = "myogen.rename_muscle"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Rename Muscle"
    bl_description = "Rename the current muscle and all its associated objects, collection and metadata"

    muscle: bpy.props.StringProperty(
        name="Target Muscle",
        description="Name of the muscle to rename (empty for active muscle)",
        default="",
    )
    new_name: bpy.props.StringProperty(
        name="New Name",
        description="New name for the muscle (use _left/_right for bilateral muscles)",
        default="",
    )

    def invoke(self, context, event):
        props = context.scene.myogen
        active = getattr(props, "active_muscle", "").strip()
        old_candidate = self.muscle.strip()
        if not old_candidate:
            if active and bpy.data.collections.get(active):
                old_candidate = active
            elif bpy.data.collections.get(props.muscle_name.strip()):
                old_candidate = props.muscle_name.strip()
        self.muscle = old_candidate

        # If a different new_name is already provided (e.g. passed from button when field was edited):
        if self.new_name and self.new_name.strip() != old_candidate and self.new_name.strip() != "Insert muscle name":
            return self.execute(context)

        # If the user edited props.muscle_name in the panel and it differs from active muscle:
        if old_candidate and props.muscle_name.strip() not in (old_candidate, "", "Insert muscle name"):
            self.new_name = props.muscle_name.strip()
            return self.execute(context)

        # Otherwise prompt with dialog:
        self.new_name = old_candidate
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_name", text="New Name")

    def execute(self, context):
        props = context.scene.myogen
        active = getattr(props, "active_muscle", "").strip()
        old_name = self.muscle.strip()
        if not old_name:
            if active and bpy.data.collections.get(active):
                old_name = active
            elif bpy.data.collections.get(props.muscle_name.strip()):
                old_name = props.muscle_name.strip()

        new_name = self.new_name.strip()
        if not new_name and props.muscle_name.strip() not in (old_name, "", "Insert muscle name"):
            new_name = props.muscle_name.strip()

        if not new_name or new_name == "Insert muscle name":
            self.report({'ERROR'}, "Please provide a valid muscle name")
            return {'CANCELLED'}
        if new_name == old_name:
            return {'FINISHED'}

        root = myo_record.get_root()
        coll = None
        if root and old_name in root.children:
            coll = root.children[old_name]
        else:
            coll = bpy.data.collections.get(old_name)

        if coll is None:
            self.report({'ERROR'}, f"Muscle collection '{old_name}' not found")
            return {'CANCELLED'}

        if (root and new_name in root.children) or (bpy.data.collections.get(new_name) is not None):
            self.report({'ERROR'}, f"A collection named '{new_name}' already exists, choose a different name")
            return {'CANCELLED'}

        from . import volume_builder
        was_live = context.scene.myogen.preview_live
        if was_live:
            volume_builder.stop_live(context)

        # Rename collection and its metadata
        coll.name = new_name
        coll["myo_name"] = new_name
        coll["myo_side"] = myo_record.parse_side(new_name)

        # Rename all objects in the collection that start with old_name
        for obj in list(coll.objects):
            if obj.name.startswith(old_name + "_"):
                suffix = obj.name[len(old_name):]
                obj.name = new_name + suffix
                if hasattr(obj.data, "name") and obj.data.name.startswith(old_name + "_"):
                    obj.data.name = new_name + suffix

        # Also rename recognized role objects that might not have standard prefix
        for role, obj in myo_record.resolve_objects(coll).items():
            suffix = myo_record.ROLES.get(role, "")
            if suffix and not obj.name.startswith(new_name + "_"):
                obj.name = f"{new_name}{suffix}"
                if hasattr(obj.data, "name") and not obj.data.name.startswith(new_name + "_"):
                    obj.data.name = f"{new_name}{suffix}"

        # Update stored object references on collection
        for key, role in myo_record.OBJECT_KEYS.items():
            if key in coll and coll[key]:
                suffix = myo_record.ROLES.get(role, "")
                target_obj = coll.objects.get(new_name + suffix)
                if target_obj:
                    coll[key] = target_obj.name

        # Update myo_record object references
        myo_record.tag_roles(coll)

        # Update active muscle and muscle name in scene settings
        if hasattr(props, "active_muscle"):
            props.active_muscle = new_name
        props.muscle_name = new_name

        if was_live:
            volume_builder.start_live(context)

        self.report({'INFO'}, f"Renamed muscle '{old_name}' to '{new_name}'")
        return {'FINISHED'}


class Delete_Muscle_Op(bpy.types.Operator):
    """Delete the current muscle collection and its objects"""
    bl_idname = "myogen.delete_muscle"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Delete Muscle"
    bl_description = "Delete the current muscle collection, its objects and construction helpers"

    muscle: bpy.props.StringProperty(
        name="Target Muscle",
        description="Name of the muscle to delete (empty for active muscle)",
        default="",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        props = context.scene.myogen
        active = getattr(props, "active_muscle", "").strip()
        name = self.muscle.strip() or active or props.muscle_name.strip()
        root = myo_record.get_root()
        coll = None
        if root and name in root.children:
            coll = root.children[name]
        else:
            coll = bpy.data.collections.get(name)

        if coll is None:
            self.report({'ERROR'}, f"Muscle collection '{name}' not found")
            return {'CANCELLED'}

        from . import volume_builder
        if context.scene.myogen.preview_live:
            volume_builder.stop_live(context)

        for obj in list(coll.objects):
            data = obj.data
            obj_type = obj.type
            bpy.data.objects.remove(obj, do_unlink=True)
            if data and data.users == 0:
                if obj_type == 'MESH':
                    bpy.data.meshes.remove(data)
                elif obj_type == 'CURVE':
                    bpy.data.curves.remove(data)

        if root and name in root.children:
            root.children.unlink(coll)
        bpy.data.collections.remove(coll)

        muscles = myo_record.iter_muscle_collections()
        new_active = muscles[0].name if muscles else ""
        if hasattr(props, "active_muscle"):
            props.active_muscle = new_active
        props.muscle_name = new_active or "Insert muscle name"
        props.preview_status = ""
        to_object_mode(context)
        bpy.ops.object.select_all(action='DESELECT')
        self.report({'INFO'}, f"Deleted muscle '{name}'")
        return {'FINISHED'}


class Select_Muscle_Op(bpy.types.Operator):
    """Select and activate a muscle for editing"""
    bl_idname = "myogen.select_muscle"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Select Muscle"
    bl_description = "Set this muscle as the active muscle in MyoGenerator"

    name: bpy.props.StringProperty(
        name="Muscle",
        description="Name of the muscle collection to activate",
        default="",
    )

    def execute(self, context):
        coll = bpy.data.collections.get(self.name)
        if not coll or not myo_record.is_muscle_collection(coll):
            self.report({'ERROR'}, f"Muscle '{self.name}' not found")
            return {'CANCELLED'}

        props = context.scene.myogen
        from . import volume_builder
        if props.preview_live and props.muscle_name != self.name:
            volume_builder.stop_live(context)

        if hasattr(props, "active_muscle"):
            props.active_muscle = self.name
        props.muscle_name = self.name
        objs = myo_record.resolve_objects(coll)
        # Restore origin/insertion bones if stored, or auto-detect
        for role, prop_name in (("origin", "origin_object"), ("insertion", "insertion_object")):
            b_name = coll.get(f"myo_{role}_bone")
            b_obj = bpy.data.objects.get(b_name) if b_name else None
            if b_obj is None:
                b_obj = _find_attachment_bone(objs.get(role), context, default_bone=getattr(props, prop_name, None))
                if b_obj:
                    coll[f"myo_{role}_bone"] = b_obj.name
            if b_obj:
                setattr(props, prop_name, b_obj)

        # Select belly or path in viewport
        coll.hide_viewport = False
        target = objs.get("belly") or objs.get("path")
        if target:
            to_object_mode(context)
            for o in context.view_layer.objects:
                o.select_set(False)
            target.hide_viewport = False
            target.hide_set(False)
            target.select_set(True)
            context.view_layer.objects.active = target

        self.report({'INFO'}, f"Active muscle: '{self.name}'")
        return {'FINISHED'}


def _existing_muscle_items(self, context):
    items = [(c.name, c.name, f"Muscle '{c.name}'") for c in myo_record.iter_muscle_collections()]
    return items or [("", "No muscles available", "")]


class Select_Muscle_Menu_Op(bpy.types.Operator):
    """Select a muscle from the list of existing muscles"""
    bl_idname = "myogen.select_muscle_menu"
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Select Muscle"
    bl_description = "Select an existing muscle to view or edit"

    muscle: bpy.props.EnumProperty(
        name="Muscle",
        description="Existing muscles in the scene",
        items=_existing_muscle_items,
    )

    def execute(self, context):
        if not self.muscle:
            return {'CANCELLED'}
        return bpy.ops.myogen.select_muscle(name=self.muscle)



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
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Check Muscles"
    bl_description = ("Measure every muscle, store the results in the muscle records and flag "
                      "implausible scales, volumes, lengths or parameters")

    def execute(self, context):
        rows, scene_findings = muscle_metrics.compute_muscles(context, write=True)
        if not rows:
            self.report({'WARNING'}, "No MyoGen muscles found in the scene")
            return {'CANCELLED'}
        worst = _report_findings(self, rows, scene_findings)
        if worst in (myo_record.QA_OK, myo_record.QA_INFO):
            self.report({'INFO'}, f"{len(rows)} muscles checked, nothing suspicious")
        return {'FINISHED'}


class Trace_Fibres_Op(bpy.types.Operator):
    """Trace the belly fibres of every muscle and show them"""
    bl_idname = "myogen.trace_fibres"
    bl_label = "Trace Fibres"
    bl_description = ("Trace the fibres of every finished belly (seeding and number as set), measure the "
                      "muscles with them as Check Muscles does, and show the fibres (detours in magenta)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.myogen.fiber_length_source == 'BELLY_FIBRES'

    def execute(self, context):
        from . import fibre_texture, visibility
        rows, scene_findings = muscle_metrics.compute_muscles(context, write=True)
        fibres = visibility.objects_by_kind()['FIBRES']
        if not fibres:
            self.report({'WARNING'}, "No fibres traced: muscles need a final belly and both attachments "
                                     "(see the QA box)")
            return {'CANCELLED'}
        visibility.set_visible(fibres, True)
        _report_findings(self, rows, scene_findings)
        for r in rows:
            coll = bpy.data.collections.get(r["collection"])
            if coll:
                belly = myo_record.resolve_objects(coll).get("belly")
                if belly:
                    fibre_texture.apply_fibre_texture(context, belly)
        traced = sum(1 for o in fibres if o.get(myo_record.ROLE_KEY) == "fibres")
        self.report({'INFO'}, f"Fibres traced for {traced} of {len(rows)} muscles")
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
    bl_options = {'REGISTER', 'UNDO'}
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
            self.report({'ERROR'}, "No MyoGen muscles found in the scene")
            return {'CANCELLED'}

        try:
            muscle_metrics.write_csv(csv_path, rows)
        except OSError as e:
            self.report({'ERROR'}, f"Failed to save CSV '{csv_path}': {e}")
            return {'CANCELLED'}

        _report_findings(self, rows, scene_findings)
        self.report({'INFO'}, f"Muscle parameters of {len(rows)} muscles saved to {csv_path}")
        return {'FINISHED'}
