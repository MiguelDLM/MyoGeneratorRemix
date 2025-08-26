"""
Workflow for creating and manipulating muscle meshes
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
from .muscle_utilities import with_temp_object_active
from .muscle_texture import apply_muscle_material

# Import lofting utilities with error handling
try:
    from .lofting_utilities import validate_curve_object, smooth_curve_transitions
except ImportError:
    def validate_curve_object(curve_obj):
        """Fallback validation function"""
        if not curve_obj or curve_obj.type != 'CURVE':
            return False, "Object is not a curve"
        return True, "Valid curve"
    
    def smooth_curve_transitions(curve_obj, smoothing_factor=0.5):
        """Fallback smoothing function"""
        return True

from .lofting_utilities import (create_smooth_curve_between_points, 
                               auto_adjust_curve_handles)
from .spline_lofting_utilities import (reset_orientation_frame, 
                                     calculate_consistent_orientation_frame,
                                     get_bezier_point_at_parameter,
                                     detect_global_inversions)
from .muscle_utilities import align_contour_directions

class Muscle_Curve_Creation_Op(bpy.types.Operator):
    """Create and setup the muscle curve for manipulation"""
    bl_idname = "view3d.muscle_curve_creation"
    bl_label = "Create Muscle Path"
    bl_description = "Create a curve path between origin and insertion that can be manually adjusted"
    
    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        
        # Get muscle collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection or muscle_name not in muscles_collection.children:
            self.report({'ERROR'}, f"Collection '{muscle_name}' not found in 'muscles'")
            return {'CANCELLED'}
        
        target_collection = muscles_collection.children[muscle_name]
        
        # Get origin and insertion objects
        origin_obj = target_collection.objects.get(muscle_name + "_origin")
        insertion_obj = target_collection.objects.get(muscle_name + "_insertion")
        
        if not origin_obj or not insertion_obj:
            self.report({'ERROR'}, "Origin and insertion objects required.")
            return {'CANCELLED'}
        
        # Calculate centroids and normals
        origin_centroid, origin_normal = self.calculate_centroid_and_normal(origin_obj)
        insertion_centroid, insertion_normal = self.calculate_centroid_and_normal(insertion_obj)
        
        # Create the curve
        curve_obj = self.create_bezier_curve(origin_centroid, insertion_centroid, 
                                           origin_normal, insertion_normal, muscle_name)
        
        # Validate the created curve
        try:
            is_valid, message = validate_curve_object(curve_obj)
            if not is_valid:
                self.report({'WARNING'}, f"Curve validation warning: {message}")
        except:
            pass  # Skip validation if function not available
        
        # Apply automatic smoothing  
        try:
            smooth_curve_transitions(curve_obj)
        except:
            pass  # Skip smoothing if function not available
        
        # Move curve to target collection
        self.remap_objects(curve_obj, target_collection)
        
        # Now align the contour directions for proper lofting
        origin_contour = target_collection.objects.get(f"{muscle_name}_origin_contour")
        insertion_contour = target_collection.objects.get(f"{muscle_name}_insertion_contour")
        
        if origin_contour and insertion_contour:
            align_success = align_contour_directions(origin_contour, insertion_contour)
            if align_success:
                self.report({'INFO'}, "Contour directions aligned for proper lofting")
            else:
                self.report({'WARNING'}, "Could not align contour directions - check contour curves")
        else:
            self.report({'WARNING'}, "Origin or insertion contour not found - alignment skipped")
        
        # Set curve as active for user manipulation
        try:
            # Ensure we have a valid 3D view context
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    with context.temp_override(area=area):
                        bpy.ops.object.select_all(action='DESELECT')
                        curve_obj.select_set(True)
                        context.view_layer.objects.active = curve_obj
                        bpy.ops.object.mode_set(mode='EDIT')
                    break
            else:
                # Fallback if no 3D view found
                curve_obj.select_set(True)
                context.view_layer.objects.active = curve_obj
                if curve_obj.type == 'CURVE':
                    bpy.ops.object.mode_set(mode='EDIT')
        except RuntimeError as e:
            # If operations fail, just set as active and report
            curve_obj.select_set(True)
            context.view_layer.objects.active = curve_obj
            self.report({'WARNING'}, f"Could not enter edit mode: {str(e)}")
        
        self.report({'INFO'}, "Muscle curve created. You can now adjust the path manually.")
        return {'FINISHED'}
    
    def calculate_centroid_and_normal(self, obj):
        """Calculate centroid and average normal of an object"""
        # Validate object and mesh data
        if not obj or not obj.data or obj.type != 'MESH':
            self.report({'ERROR'}, f"Invalid object: {obj.name if obj else 'None'}")
            return Vector((0, 0, 0)), Vector((0, 0, 1))
        
        vertices = [v.co for v in obj.data.vertices]
        
        # Check if object has vertices
        if not vertices or len(vertices) == 0:
            self.report({'ERROR'}, f"Object '{obj.name}' has no vertices")
            return Vector((0, 0, 0)), Vector((0, 0, 1))
        
        centroid_local = sum(vertices, Vector()) / len(vertices)
        centroid_world = obj.matrix_world @ centroid_local
        
        # Calculate average normal
        normals = []
        if len(obj.data.polygons) > 0:
            for poly in obj.data.polygons:
                normals.append(poly.normal)
            avg_normal = sum(normals, Vector()) / len(normals)
        else:
            avg_normal = Vector((0, 0, 1))
        
        avg_normal_world = obj.matrix_world.to_3x3() @ avg_normal
        return centroid_world, avg_normal_world
    
    def create_bezier_curve(self, start_point, end_point, start_normal, end_normal, muscle_name):
        """Create a Bezier curve with proper control for orientation and scaling"""
        
        # Calculate control points for smooth muscle curve
        direction = end_point - start_point
        distance = direction.length
        
        # Create a new curve data object
        curve_data = bpy.data.curves.new(name=muscle_name + "_curve", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 12
        
        # Create a Bezier spline for better control
        spline = curve_data.splines.new(type='BEZIER')
        
        # Add more control points for better muscle shape control
        num_points = 5  # Start, 3 intermediate, End
        spline.bezier_points.add(num_points - 1)  # -1 because it starts with 1 point
        
        # Set up points for natural muscle curve
        for i in range(num_points):
            t = i / (num_points - 1)
            
            # Interpolate position along the path
            point_pos = start_point.lerp(end_point, t)
            
            # Add slight curve for natural muscle shape
            if i == 1 or i == 3:  # Intermediate points
                # Offset slightly based on normals for natural curve
                offset_strength = distance * 0.1
                if i == 1:
                    offset = start_normal * offset_strength
                else:
                    offset = end_normal * offset_strength
                point_pos += offset
            
            # Set point position
            bezier_point = spline.bezier_points[i]
            bezier_point.co = point_pos
            
            # Set radius for diameter control (1.0 = normal, >1.0 = thicker, <1.0 = thinner)
            if i == 0 or i == num_points - 1:
                # End points - tapered for attachment
                bezier_point.radius = 0.8
            elif i == num_points // 2:
                # Middle point - thicker for muscle belly
                bezier_point.radius = 1.4
            else:
                # Transition points - gradual increase toward middle
                distance_from_center = abs(i - num_points // 2)
                max_distance = num_points // 2
                # Linear interpolation from center (1.4) to ends (0.8)
                bezier_point.radius = 1.4 - (distance_from_center / max_distance) * 0.6
            
            # Set handle types for smooth curves
            bezier_point.handle_left_type = 'AUTO'
            bezier_point.handle_right_type = 'AUTO'
        
        # Create the curve object and link to scene
        curve_obj = bpy.data.objects.new(muscle_name + "_curve", curve_data)
        bpy.context.scene.collection.objects.link(curve_obj)
        
        # Set as active object
        bpy.context.view_layer.objects.active = curve_obj
        curve_obj.select_set(True)
        
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        return curve_obj
    
    def remap_objects(self, obj, target_collection):
        """Move object to target collection"""
        # Remove from current collection
        for collection in obj.users_collection:
            collection.objects.unlink(obj)
        # Add to target collection
        target_collection.objects.link(obj)


class Muscle_Mesh_Generation_Op(bpy.types.Operator):
    """Generate the final muscle mesh by keeping the current preview mesh"""
    bl_idname = "view3d.muscle_mesh_generation"
    bl_label = "Generate Final Mesh"
    bl_description = "Convert the current preview mesh to the final muscle mesh - this completes the muscle creation process"
    
    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        
        # Get muscle collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection or muscle_name not in muscles_collection.children:
            self.report({'ERROR'}, f"Collection '{muscle_name}' not found in 'muscles'")
            return {'CANCELLED'}
        
        target_collection = muscles_collection.children[muscle_name]
        
        # Look for the preview object
        preview_obj = target_collection.objects.get(muscle_name + "_preview")
        
        if not preview_obj:
            self.report({'ERROR'}, "No preview mesh found. Start preview mode first.")
            return {'CANCELLED'}
        
        # Stop preview mode first
        if hasattr(context.scene, 'muscle_preview_active'):
            context.scene.muscle_preview_active = False
        
        # Ensure we're in object mode before doing object operations
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Rename the preview object to be the final muscle mesh
        final_name = muscle_name + "_muscle"
        
        # Remove any existing muscle mesh with the same name
        existing_muscle = target_collection.objects.get(final_name)
        if existing_muscle:
            bpy.data.objects.remove(existing_muscle, do_unlink=True)
        
        # Rename preview to final muscle mesh
        preview_obj.name = final_name
        
        # Apply the procedural muscle material
        material_applied = apply_muscle_material(preview_obj)
        if material_applied:
            self.report({'INFO'}, "Muscle material applied successfully")
        else:
            self.report({'WARNING'}, "Failed to apply muscle material")
        
        # Make sure it's visible (not transparent)
        preview_obj.show_transparent = False
        
        # Ensure the final mesh has closed ends
        self.ensure_mesh_closed(preview_obj)
        
        # Apply diameter-aware smoothing to the final mesh
        self.smooth_muscle_mesh(preview_obj, context)
        
        # Select the new muscle object safely
        try:
            # Ensure we have a valid 3D view context
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    with context.temp_override(area=area):
                        bpy.ops.object.select_all(action='DESELECT')
                        preview_obj.select_set(True)
                        context.view_layer.objects.active = preview_obj
                    break
            else:
                # Fallback if no 3D view found
                preview_obj.select_set(True)
                context.view_layer.objects.active = preview_obj
        except RuntimeError:
            # If selection fails, just set as active
            context.view_layer.objects.active = preview_obj
        
        self.report({'INFO'}, f"Muscle mesh '{final_name}' generated successfully!")
        return {'FINISHED'}
    
    def ensure_mesh_closed(self, mesh_obj):
        """Ensure the muscle mesh has closed ends by filling any open boundaries"""
        if not mesh_obj or mesh_obj.type != 'MESH':
            return
        
        # Create bmesh instance from mesh
        bm = bmesh.new()
        bm.from_mesh(mesh_obj.data)
        
        # Ensure we have face indices
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        
        # Fill holes in the mesh
        open_edges = [edge for edge in bm.edges if len(edge.link_faces) == 1]
        
        if open_edges:
            # Group boundary edges into loops
            boundary_loops = []
            remaining_edges = open_edges.copy()
            
            while remaining_edges:
                loop = [remaining_edges.pop(0)]
                current_vert = loop[0].verts[1]
                
                # Follow the boundary loop
                while True:
                    found_next = False
                    for edge in remaining_edges:
                        if current_vert in edge.verts:
                            loop.append(edge)
                            remaining_edges.remove(edge)
                            current_vert = edge.verts[0] if edge.verts[1] == current_vert else edge.verts[1]
                            found_next = True
                            break
                    
                    if not found_next or current_vert == loop[0].verts[0]:
                        break
                
                if len(loop) > 2:
                    boundary_loops.append(loop)
            
            # Fill each boundary loop
            for loop in boundary_loops:
                loop_verts = []
                for edge in loop:
                    if not loop_verts or edge.verts[0] != loop_verts[-1]:
                        loop_verts.append(edge.verts[0])
                    if edge.verts[1] != loop_verts[0]:
                        loop_verts.append(edge.verts[1])
                
                # Use fan triangulation to fill the hole
                if len(loop_verts) >= 3:
                    self.create_cap_faces_simple(bm, loop_verts)
        
        # Update the mesh
        bm.to_mesh(mesh_obj.data)
        mesh_obj.data.update()
        bm.free()
    
    def create_cap_faces_simple(self, bm, vertex_loop):
        """Create cap faces using fan triangulation (simplified version)"""
        if len(vertex_loop) < 3:
            return
        
        # Calculate center point of the loop
        center_point = Vector((0, 0, 0))
        for vert in vertex_loop:
            center_point += vert.co
        center_point /= len(vertex_loop)
        
        # Create center vertex
        center_vert = bm.verts.new(center_point)
        
        # Create triangular faces from center to each edge
        for i in range(len(vertex_loop)):
            v1 = vertex_loop[i]
            v2 = vertex_loop[(i + 1) % len(vertex_loop)]
            
            try:
                bm.faces.new([center_vert, v1, v2])
            except ValueError:
                # Skip if face creation fails
                continue
    
    def smooth_muscle_mesh(self, mesh_obj, context):
        """Apply diameter-aware smoothing to the final muscle mesh"""
        if not mesh_obj or mesh_obj.type != 'MESH':
            return
        
        # Import smoothing utilities
        try:
            from .spline_lofting_utilities import smooth_diameter_transitions
        except ImportError:
            # Basic smoothing fallback
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(mesh_obj.data)
            for _ in range(2):
                bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.2)
            bm.to_mesh(mesh_obj.data)
            mesh_obj.data.update()
            bm.free()
            return
        
        # Advanced diameter-aware smoothing
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(mesh_obj.data)
        
        # Apply gentle smoothing to preserve diameter variations
        smoothing_iterations = max(1, int(getattr(context.scene, 'muscle_diameter_smoothing', 0.5) * 4))
        
        for _ in range(smoothing_iterations):
            bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.1)
        
        # Update the mesh
        bm.to_mesh(mesh_obj.data)
        mesh_obj.data.update()
        bm.free()


class Muscle_Preview_Update_Op(bpy.types.Operator):
    """Update muscle preview in real-time with modal operation"""
    bl_idname = "view3d.muscle_preview_update"
    bl_label = "Start Preview Mode"
    bl_description = "Start real-time preview of muscle mesh that updates when curve is modified"
    
    _preview_object = None
    _timer = None
    _last_curve_hash = None
    
    def modal(self, context, event):
        """Modal execution for real-time preview updates"""
        try:
            muscle_name = context.scene.muscle_Name
            
            # Check if preview should continue
            if not hasattr(context.scene, 'muscle_preview_active') or not context.scene.muscle_preview_active:
                self.finish_preview(context)
                return {'FINISHED'}
            
            # Update on timer events, curve edits, or when density properties change
            should_update = False
            
            if event.type == 'TIMER':
                # Get muscle collection and objects
                muscles_collection = bpy.data.collections.get("muscles")
                if not muscles_collection or muscle_name not in muscles_collection.children:
                    self.finish_preview(context)
                    return {'FINISHED'}
                
                target_collection = muscles_collection.children[muscle_name]
                curve_obj = target_collection.objects.get(muscle_name + "_curve")
                
                if not curve_obj:
                    return {'PASS_THROUGH'}
                
                # Check if curve structure or settings have changed
                curve_structure_hash = self.get_curve_structure_hash(curve_obj)
                current_curve_hash = self.get_curve_hash(curve_obj)
                density_hash = self.get_density_hash(context)
                
                # Also check for point count changes (more responsive)
                point_structure_changed = self.detect_bezier_point_changes(curve_obj)
                
                if (current_curve_hash != self._last_curve_hash or 
                    curve_structure_hash != getattr(self, '_last_structure_hash', None) or
                    point_structure_changed or
                    not hasattr(self, '_last_density_hash') or 
                    density_hash != self._last_density_hash):
                    
                    self._last_curve_hash = current_curve_hash
                    self._last_structure_hash = curve_structure_hash
                    self._last_density_hash = density_hash
                    should_update = True
            
            # Also check for curve editing events that should trigger immediate updates
            elif event.type in {'G', 'S', 'R', 'TAB', 'LEFTMOUSE', 'RIGHTMOUSE', 'E', 'X', 'DEL'} and event.value == 'RELEASE':
                # Check if we're editing a curve object
                if (context.active_object and context.active_object.type == 'CURVE' and 
                    context.active_object.name.endswith('_curve')):
                    should_update = True
            
            # Special check for extrude operations (adding points)
            elif event.type == 'E' and event.value == 'PRESS':
                if (context.active_object and context.active_object.type == 'CURVE' and 
                    context.active_object.name.endswith('_curve')):
                    # Force update after short delay to catch new points
                    self._force_update_next = True
            
            # Check for mode changes (entering/exiting edit mode)
            elif event.type == 'TAB' and event.value == 'PRESS':
                if (context.active_object and context.active_object.type == 'CURVE' and 
                    context.active_object.name.endswith('_curve')):
                    # Force update when entering/exiting edit mode
                    self._force_update_next = True

            
            # Check for undo/redo operations
            elif event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
                should_update = True

            
            # Force update if flagged
            if getattr(self, '_force_update_next', False):
                should_update = True
                self._force_update_next = False

            
            if should_update:
                muscles_collection = bpy.data.collections.get("muscles")
                if muscles_collection and muscle_name in muscles_collection.children:
                    target_collection = muscles_collection.children[muscle_name]
                    self.update_preview_mesh(context, muscle_name, target_collection)
                    
                    # Force viewport redraw
                    for area in context.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
            
            return {'PASS_THROUGH'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Preview modal error: {e}")
            self.finish_preview(context)
            return {'FINISHED'}
    
    def invoke(self, context, event):
        """Start the modal preview"""
        muscle_name = context.scene.muscle_Name
        
        # Get muscle collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection or muscle_name not in muscles_collection.children:
            self.report({'ERROR'}, f"Collection '{muscle_name}' not found")
            return {'CANCELLED'}
        
        target_collection = muscles_collection.children[muscle_name]
        
        # Check required objects
        curve_obj = target_collection.objects.get(muscle_name + "_curve")
        origin_contour = target_collection.objects.get(muscle_name + "_origin_contour")
        insertion_contour = target_collection.objects.get(muscle_name + "_insertion_contour")
        
        if not all([curve_obj, origin_contour, insertion_contour]):
            self.report({'ERROR'}, "Required objects not found: curve, origin_contour, insertion_contour")
            return {'CANCELLED'}
        
        # Set preview mode
        if not hasattr(context.scene, 'muscle_preview_active'):
            bpy.types.Scene.muscle_preview_active = bpy.props.BoolProperty(default=False)
        context.scene.muscle_preview_active = True
        
        # Create initial preview
        success = self.update_preview_mesh(context, muscle_name, target_collection)
        if not success:
            self.report({'ERROR'}, "Failed to create preview mesh")
            return {'CANCELLED'}
        
        # Add timer and modal handler with shorter interval for responsiveness
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)  # More responsive
        context.window_manager.modal_handler_add(self)
        
        self.report({'INFO'}, "Preview mode started - modify curve to see real-time updates")
        return {'RUNNING_MODAL'}
    
    def finish_preview(self, context):
        """Clean up preview mode"""
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        
        if hasattr(context.scene, 'muscle_preview_active'):
            context.scene.muscle_preview_active = False
        
        # Keep the preview object but rename it to indicate it's static
        try:
            if self._preview_object and hasattr(self._preview_object, 'name'):
                # Check if object still exists in Blender's data
                object_exists = False
                for obj in bpy.data.objects:
                    if obj == self._preview_object:
                        object_exists = True
                        break
                
                if object_exists:
                    self._preview_object.name = self._preview_object.name.replace("_preview", "_preview_static")
        except ReferenceError:
            # Object has been removed, ignore
            pass
        finally:
            self._preview_object = None
    
    def get_curve_hash(self, curve_obj):
        """Create a more sensitive hash of curve point positions and radius/weights"""
        if not curve_obj or not curve_obj.data.splines:
            return 0
        
        hash_val = 0
        spline = curve_obj.data.splines[0]
        
        if spline.type in ['NURBS', 'POLY']:
            for i, point in enumerate(spline.points):
                world_co = curve_obj.matrix_world @ Vector(point.co[:3])
                # Include weight value (4th component) for diameter control
                weight = point.co[3] if len(point.co) > 3 else 1.0
                # Use higher precision for more sensitive detection
                hash_val += hash((
                    round(world_co.x, 6), round(world_co.y, 6), round(world_co.z, 6), 
                    round(weight, 4), i
                ))
        elif spline.type == 'BEZIER':
            for i, point in enumerate(spline.bezier_points):
                world_co = curve_obj.matrix_world @ point.co
                # Include handle positions for Bezier curves
                handle_left = curve_obj.matrix_world @ point.handle_left
                handle_right = curve_obj.matrix_world @ point.handle_right
                # Include radius for diameter control
                radius = point.radius
                hash_val += hash((
                    round(world_co.x, 6), round(world_co.y, 6), round(world_co.z, 6),
                    round(handle_left.x, 6), round(handle_left.y, 6), round(handle_left.z, 6),
                    round(handle_right.x, 6), round(handle_right.y, 6), round(handle_right.z, 6),
                    round(radius, 4), i
                ))
        
        return hash_val
    
    def get_density_hash(self, context):
        """Create hash of density control values to detect changes"""
        return hash((
            context.scene.muscle_curve_subdivisions,
            context.scene.muscle_contour_resolution,
            getattr(context.scene, 'origin_contour_offset', 0),
            getattr(context.scene, 'insertion_contour_offset', 0),
            getattr(context.scene, 'origin_reverse_orientation', False),
            getattr(context.scene, 'insertion_reverse_orientation', False)
        ))
    
    def get_curve_structure_hash(self, curve_obj):
        """Create hash of curve structure to detect changes in Bezier points"""
        if not curve_obj or curve_obj.type != 'CURVE' or not curve_obj.data.splines:
            return 0
        
        spline = curve_obj.data.splines[0]
        if spline.type != 'BEZIER':
            return 0
        
        # Create hash based on number of points and their positions/radii
        hash_data = []
        hash_data.append(len(spline.bezier_points))  # Number of points
        
        for point in spline.bezier_points:
            # Include position and radius in hash
            hash_data.extend([
                round(point.co.x, 4), round(point.co.y, 4), round(point.co.z, 4),
                round(point.radius, 4)
            ])
            # Include handle positions for completeness
            hash_data.extend([
                round(point.handle_left.x, 4), round(point.handle_left.y, 4), round(point.handle_left.z, 4),
                round(point.handle_right.x, 4), round(point.handle_right.y, 4), round(point.handle_right.z, 4)
            ])
        
        return hash(tuple(hash_data))
    
    def detect_bezier_point_changes(self, curve_obj):
        """
        Detect if Bezier points have been added or removed
        Returns True if structure changed
        """
        if not curve_obj or curve_obj.type != 'CURVE' or not curve_obj.data.splines:
            return False
        
        spline = curve_obj.data.splines[0]
        if spline.type != 'BEZIER':
            return False
        
        current_point_count = len(spline.bezier_points)
        previous_count = getattr(self, '_last_bezier_point_count', current_point_count)
        
        if current_point_count != previous_count:
            self._last_bezier_point_count = current_point_count
            return True
        
        return False
    
    def update_preview_mesh(self, context, muscle_name, target_collection):
        """Update the preview mesh based on current curve"""
        try:
            # Get required objects
            curve_obj = target_collection.objects.get(muscle_name + "_curve")
            origin_contour = target_collection.objects.get(muscle_name + "_origin_contour")
            insertion_contour = target_collection.objects.get(muscle_name + "_insertion_contour")
            
            if not all([curve_obj, origin_contour, insertion_contour]):
                self.report({'ERROR'}, "Missing required objects for preview")
                return False
            
            # Remove existing preview
            try:
                if self._preview_object:
                    # Check if object still exists
                    object_exists = False
                    for obj in bpy.data.objects:
                        if obj == self._preview_object:
                            object_exists = True
                            break
                    
                    if object_exists:
                        bpy.data.objects.remove(self._preview_object, do_unlink=True)
            except ReferenceError:
                # Object has been removed already, ignore
                pass
            finally:
                self._preview_object = None
            
            # Create new preview mesh using improved parallel transport
            # Always reset the parallel transport frame to ensure consistency
            reset_orientation_frame()
            
            # Check if curve needs special handling for inversions
            needs_special_handling = detect_global_inversions(curve_obj)
            
            # Choose lofting mode based on scene property
            mode = getattr(context.scene, 'muscle_connection_mode', 'FOLLOW_PATH')
            if mode == 'DIRECT_CONNECTION':
                preview_mesh = self.create_direct_preview_mesh(context, origin_contour, insertion_contour)
            else:
                preview_mesh = self.create_simple_preview_mesh(
                    context, curve_obj, origin_contour, insertion_contour
                )
            
            if preview_mesh:
                # Create preview object
                self._preview_object = bpy.data.objects.new(muscle_name + "_preview", preview_mesh)
                target_collection.objects.link(self._preview_object)

                
                # Update viewport
                context.view_layer.update()
                return True
            
            return False
                
        except Exception as e:
            self.report({'ERROR'}, f"Error updating preview: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_simple_preview_mesh(self, context, curve_obj, origin_contour, insertion_contour):
        """Create preview mesh using Bezier parallel transport for robust orientation"""
        bm = bmesh.new()

        try:
            
            # Reset orientation frame for new mesh generation
            reset_orientation_frame()
            
            # Get contour vertices
            origin_loop = self.get_contour_vertices(origin_contour)
            insertion_loop = self.get_contour_vertices(insertion_contour)
                       
            if not origin_loop or not insertion_loop:
                self.report({'ERROR'}, "Missing contour vertices")
                return None
            
            # Calculate original centroids
            origin_centroid = sum(origin_loop, Vector()) / len(origin_loop)
            insertion_centroid = sum(insertion_loop, Vector()) / len(insertion_loop)
            
            # Use user-defined contour resolution
            target_count = max(6, int(context.scene.muscle_contour_resolution * 0.75))
            origin_resampled = self.simple_resample(origin_loop, target_count)
            insertion_resampled = self.simple_resample(insertion_loop, target_count)

            # Apply user-defined vertex order offsets
            origin_offset = getattr(context.scene, 'origin_contour_offset', 0)
            insertion_offset = getattr(context.scene, 'insertion_contour_offset', 0)
            if origin_resampled:
                origin_offset %= len(origin_resampled)
                origin_resampled = origin_resampled[origin_offset:] + origin_resampled[:origin_offset]
                if getattr(context.scene, 'origin_reverse_orientation', False):
                    origin_resampled = list(reversed(origin_resampled))
            if insertion_resampled:
                insertion_offset %= len(insertion_resampled)
                insertion_resampled = insertion_resampled[insertion_offset:] + insertion_resampled[:insertion_offset]
                if getattr(context.scene, 'insertion_reverse_orientation', False):
                    insertion_resampled = list(reversed(insertion_resampled))
            
            # Get curve subdivisions (use scene value directly so user control affects density)
            curve_subdivisions = max(4, int(context.scene.muscle_curve_subdivisions))
            
            # Generate mesh using parallel transport orientation
            vertex_loops = []
            
            
            for i in range(curve_subdivisions):
                t = i / (curve_subdivisions - 1) if curve_subdivisions > 1 else 0.0

                # Get orientation frame and position from Bezier curve using parallel transport
                tangent, normal, binormal, radius = calculate_consistent_orientation_frame(curve_obj, t)
                position, _, _ = get_bezier_point_at_parameter(curve_obj, t)

                # Linear interpolation between origin and insertion contours
                interpolated_contour = []
                for j in range(target_count):
                    origin_vert = origin_resampled[j]
                    insertion_vert = insertion_resampled[j]
                    interpolated_vert = origin_vert.lerp(insertion_vert, t)
                    interpolated_contour.append(interpolated_vert)

                # Calculate center of the interpolated contour
                interpolated_center = sum(interpolated_contour, Vector()) / len(interpolated_contour)

                # Create the final loop by moving each vertex from interpolated position to curve position
                interpolated_loop = []
                for vertex in interpolated_contour:
                    offset = vertex - interpolated_center
                    scaled_offset = offset * radius
                    final_pos = position + scaled_offset
                    interpolated_loop.append(final_pos)
                
                # Add vertices to bmesh
                loop_verts = []
                for vert_co in interpolated_loop:
                    vert = bm.verts.new(vert_co)
                    loop_verts.append(vert)
                
                vertex_loops.append(loop_verts)
            
            # Ensure bmesh is valid
            bm.verts.ensure_lookup_table()
            
            # Bridge loops with consistent winding order (like Bridge Edge Loops)
            for i in range(len(vertex_loops) - 1):
                current_loop = vertex_loops[i]
                next_loop = vertex_loops[i + 1]
                
                if len(current_loop) == len(next_loop):
                    for j in range(len(current_loop)):
                        j_next = (j + 1) % len(current_loop)
                        
                        # Get vertices for quad - maintain consistent winding order
                        v1 = current_loop[j]
                        v2 = next_loop[j]
                        v3 = next_loop[j_next]
                        v4 = current_loop[j_next]
                        
                        try:
                            # Create quad with consistent normal direction
                            face = bm.faces.new([v1, v2, v3, v4])
                            face.normal_update()
                        except ValueError:
                            # If quad fails, try triangles with consistent winding
                            try:
                                face1 = bm.faces.new([v1, v2, v3])
                                face2 = bm.faces.new([v1, v3, v4])
                                face1.normal_update()
                                face2.normal_update()
                            except ValueError:
                                continue
            
            # Add end caps with improved geometry
            if len(vertex_loops) > 0:
                # Create origin cap (first loop)
                if len(vertex_loops[0]) > 2:
                    self.create_cap_faces(bm, vertex_loops[0], reverse=False)
                
                # Create insertion cap (last loop)
                if len(vertex_loops[-1]) > 2:
                    self.create_cap_faces(bm, vertex_loops[-1], reverse=True)
            
            # Clean up
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)

            # Apply light smoothing to soften the preview mesh
            for _ in range(2):
                bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5)

            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            
            # Create mesh
            mesh = bpy.data.meshes.new("preview_mesh")
            bm.to_mesh(mesh)
            mesh.update()
            
            return mesh
            
        except Exception as e:
            self.report({'ERROR'}, f"Error in create_simple_preview_mesh: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            bm.free()
    
    def simple_resample(self, vertices, target_count):
        """Simple vertex resampling"""
        if len(vertices) <= target_count:
            return vertices
        
        resampled = []
        for i in range(target_count):
            index = int((i / (target_count - 1)) * (len(vertices) - 1)) if target_count > 1 else 0
            resampled.append(vertices[index])
        
        return resampled

    def create_direct_preview_mesh(self, context, origin_contour, insertion_contour):
        """Create a preview mesh by directly connecting origin and insertion contours without following the curve"""
        bm = bmesh.new()

        try:
            origin_loop = self.get_contour_vertices(origin_contour)
            insertion_loop = self.get_contour_vertices(insertion_contour)

            if not origin_loop or not insertion_loop:
                self.report({'ERROR'}, "Missing contour vertices for direct connection")
                return None

            # Use same target resolution as other method
            target_count = max(6, int(context.scene.muscle_contour_resolution * 0.75))
            origin_resampled = self.simple_resample(origin_loop, target_count)
            insertion_resampled = self.simple_resample(insertion_loop, target_count)

            # Apply offsets and reversals
            origin_offset = getattr(context.scene, 'origin_contour_offset', 0)
            insertion_offset = getattr(context.scene, 'insertion_contour_offset', 0)
            origin_offset %= len(origin_resampled)
            insertion_offset %= len(insertion_resampled)
            origin_resampled = origin_resampled[origin_offset:] + origin_resampled[:origin_offset]
            insertion_resampled = insertion_resampled[insertion_offset:] + insertion_resampled[:insertion_offset]
            if getattr(context.scene, 'origin_reverse_orientation', False):
                origin_resampled = list(reversed(origin_resampled))
            if getattr(context.scene, 'insertion_reverse_orientation', False):
                insertion_resampled = list(reversed(insertion_resampled))

            # Create multiple intermediate loops by interpolating between origin and insertion
            curve_subdivisions = max(2, int(context.scene.muscle_curve_subdivisions))
            vertex_loops = []

            for i in range(curve_subdivisions):
                t = i / (curve_subdivisions - 1) if curve_subdivisions > 1 else 0.0
                interpolated_loop = []
                for j in range(len(origin_resampled)):
                    o = origin_resampled[j]
                    ins = insertion_resampled[j]
                    interpolated = o.lerp(ins, t)
                    interpolated_loop.append(interpolated)

                # Add verts of this loop to bmesh
                loop_verts = [bm.verts.new(co) for co in interpolated_loop]
                vertex_loops.append(loop_verts)

            bm.verts.ensure_lookup_table()

            # Bridge consecutive loops
            for i in range(len(vertex_loops) - 1):
                current_loop = vertex_loops[i]
                next_loop = vertex_loops[i + 1]
                if len(current_loop) == len(next_loop):
                    for j in range(len(current_loop)):
                        j_next = (j + 1) % len(current_loop)
                        v1 = current_loop[j]
                        v2 = next_loop[j]
                        v3 = next_loop[j_next]
                        v4 = current_loop[j_next]

                        try:
                            bm.faces.new([v1, v2, v3, v4])
                        except ValueError:
                            try:
                                bm.faces.new([v1, v2, v3])
                                bm.faces.new([v1, v3, v4])
                            except ValueError:
                                continue

            # Add caps using first and last loop
            if len(vertex_loops) > 0:
                if len(vertex_loops[0]) > 2:
                    self.create_cap_faces(bm, vertex_loops[0], reverse=False)
                if len(vertex_loops[-1]) > 2:
                    self.create_cap_faces(bm, vertex_loops[-1], reverse=True)

            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

            mesh = bpy.data.meshes.new("preview_mesh")
            bm.to_mesh(mesh)
            mesh.update()
            return mesh

        except Exception as e:
            self.report({'ERROR'}, f"Error in create_direct_preview_mesh: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            bm.free()
    
    def get_curve_sample_points(self, curve_obj, num_samples):
        """Sample points along curve path with better interpolation"""
        if not curve_obj or curve_obj.type != 'CURVE' or not curve_obj.data.splines:
            return []
        
        spline = curve_obj.data.splines[0]
        spline_points = []
        
        if spline.type in ['NURBS', 'POLY']:
            for point in spline.points:
                world_point = curve_obj.matrix_world @ Vector(point.co[:3])
                spline_points.append(world_point)
        elif spline.type == 'BEZIER':
            for point in spline.bezier_points:
                world_point = curve_obj.matrix_world @ point.co
                spline_points.append(world_point)
        
        if len(spline_points) < 2:
            return spline_points
        
        # Better interpolation for smoother curve following
        points = []
        for i in range(num_samples):
            if num_samples == 1:
                t = 0.0
            else:
                t = i / (num_samples - 1)
            
            # Find the exact position along the curve
            curve_length = len(spline_points) - 1
            segment_pos = t * curve_length
            segment_index = int(segment_pos)
            local_t = segment_pos - segment_index
            
            if segment_index >= len(spline_points) - 1:
                points.append(spline_points[-1])
            else:
                # Linear interpolation between curve control points
                p1 = spline_points[segment_index]
                p2 = spline_points[segment_index + 1]
                interpolated = p1.lerp(p2, local_t)
                points.append(interpolated)
        
        return points
    
    def get_contour_vertices(self, contour_obj):
        """Extract vertices from contour curve"""
        if not contour_obj or contour_obj.type != 'CURVE' or not contour_obj.data.splines:
            return []
        
        spline = contour_obj.data.splines[0]
        vertices = []
        
        if spline.type in ['NURBS', 'POLY']:
            for point in spline.points:
                world_co = contour_obj.matrix_world @ Vector(point.co[:3])
                vertices.append(world_co)
        elif spline.type == 'BEZIER':
            for point in spline.bezier_points:
                world_co = contour_obj.matrix_world @ point.co
                vertices.append(world_co)
        
        return vertices
        
    def create_cap_faces(self, bm, vertex_loop, reverse=False):
        """Create cap faces for muscle ends using fan triangulation"""
        if len(vertex_loop) < 3:
            return
        
        try:
            # For simple cases, try to create a single face
            if len(vertex_loop) <= 4:
                if reverse:
                    bm.faces.new(reversed(vertex_loop))
                else:
                    bm.faces.new(vertex_loop)
                return
        except ValueError:
            pass  # If single face fails, continue with fan triangulation
        
        # For complex cases, use fan triangulation
        # Calculate center point of the loop
        center_point = Vector((0, 0, 0))
        for vert in vertex_loop:
            center_point += vert.co
        center_point /= len(vertex_loop)
        
        # Create center vertex
        center_vert = bm.verts.new(center_point)
        
        # Create triangular faces from center to each edge
        for i in range(len(vertex_loop)):
            v1 = vertex_loop[i]
            v2 = vertex_loop[(i + 1) % len(vertex_loop)]
            
            try:
                if reverse:
                    bm.faces.new([center_vert, v2, v1])
                else:
                    bm.faces.new([center_vert, v1, v2])
            except ValueError:
                # Skip if face creation fails
                continue

    def calculate_curve_tangent(self, curve_points, index):
        """
        Calculate the tangent vector at a specific point along the curve
        
        Args:
            curve_points: List of Vector points along the curve
            index: Index of the current point
            
        Returns:
            Vector: Normalized tangent vector
        """
        if len(curve_points) < 2:
            return Vector((1, 0, 0))  # Default tangent
        
        # Calculate tangent vector using finite differences
        if index == 0:
            # At start, use forward difference
            tangent = (curve_points[1] - curve_points[0]).normalized()
        elif index == len(curve_points) - 1:
            # At end, use backward difference
            tangent = (curve_points[-1] - curve_points[-2]).normalized()
        else:
            # In middle, use central difference for smoother results
            tangent = (curve_points[index + 1] - curve_points[index - 1]).normalized()
        
        return tangent

class Muscle_Preview_Stop_Op(bpy.types.Operator):
    """Stop the muscle preview mode"""
    bl_idname = "view3d.muscle_preview_stop"
    bl_label = "Stop Preview"
    bl_description = "Stop the real-time muscle preview"
    
    def execute(self, context):
        # Set preview mode to false to stop modal operator
        if hasattr(context.scene, 'muscle_preview_active'):
            context.scene.muscle_preview_active = False
        
        # Remove preview object if it exists
        muscle_name = context.scene.muscle_Name
        muscles_collection = bpy.data.collections.get("muscles")
        
        if muscles_collection and muscle_name in muscles_collection.children:
            target_collection = muscles_collection.children[muscle_name]
            preview_obj = target_collection.objects.get(muscle_name + "_preview")
            
            if preview_obj:
                try:
                    bpy.data.objects.remove(preview_obj, do_unlink=True)
                except ReferenceError:
                    # Object already removed, ignore
                    pass
        
        self.report({'INFO'}, "Preview stopped")
        return {'FINISHED'}
