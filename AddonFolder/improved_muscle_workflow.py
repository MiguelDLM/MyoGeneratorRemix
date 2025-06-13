"""
Improved Muscle Workflow Module
Implements a two-stage workflow for muscle creation:
1. Curve creation and manipulation
2. Final mesh generation with lofting
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
from .muscle_utilities import with_temp_object_active

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
                               improve_curve_smoothness,
                               validate_lofting_inputs,
                               auto_adjust_curve_handles)

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
        
        # Set curve as active for user manipulation
        bpy.ops.object.select_all(action='DESELECT')
        curve_obj.select_set(True)
        context.view_layer.objects.active = curve_obj
        bpy.ops.object.mode_set(mode='EDIT')
        
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
        """Create a NURBS path with multiple control points using improved curve generation"""
        
        # Use the enhanced curve creation from utilities
        curve_points = create_smooth_curve_between_points(
            start_point, end_point, start_normal, end_normal, num_points=7
        )
        
        # Create a new curve data object
        curve_data = bpy.data.curves.new(name=muscle_name + "_curve", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 12
        
        # Create a new spline
        spline = curve_data.splines.new(type='NURBS')
        spline.points.add(len(curve_points) - 1)  # -1 because spline starts with 1 point
        
        # Assign coordinates to each point
        for i, point in enumerate(curve_points):
            spline.points[i].co = (point.x, point.y, point.z, 1)
        
        # Set spline properties for smooth muscle curves
        spline.order_u = min(4, len(curve_points))
        spline.use_endpoint_u = True
        
        # Create the curve object and link to scene
        curve_obj = bpy.data.objects.new(muscle_name + "_curve", curve_data)
        bpy.context.scene.collection.objects.link(curve_obj)
        
        # Set as active object
        bpy.context.view_layer.objects.active = curve_obj
        curve_obj.select_set(True)
        
        # Apply automatic smoothing
        auto_adjust_curve_handles(curve_obj)
        
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
    """Generate the final muscle mesh using bmesh lofting"""
    bl_idname = "view3d.muscle_mesh_generation"
    bl_label = "Generate Muscle Mesh"
    bl_description = "Generate the final muscle mesh with volume using bmesh lofting between origin and insertion"
    
    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        
        # Get muscle collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection or muscle_name not in muscles_collection.children:
            self.report({'ERROR'}, f"Collection '{muscle_name}' not found in 'muscles'")
            return {'CANCELLED'}
        
        target_collection = muscles_collection.children[muscle_name]
        
        # Get required objects
        curve_obj = target_collection.objects.get(muscle_name + "_curve")
        origin_contour = target_collection.objects.get(muscle_name + "_origin_contour")
        insertion_contour = target_collection.objects.get(muscle_name + "_insertion_contour")
        
        # Validate inputs
        validation_errors = validate_lofting_inputs(curve_obj, origin_contour, insertion_contour)
        if validation_errors:
            self.report({'ERROR'}, f"Validation failed: {'; '.join(validation_errors)}")
            return {'CANCELLED'}
        
        try:
            # Create muscle mesh using bmesh lofting
            muscle_obj = self.create_muscle_mesh_bmesh(
                context, 
                muscle_name, 
                curve_obj, 
                origin_contour, 
                insertion_contour, 
                target_collection
            )
            
            # Move to target collection
            target_collection.objects.link(muscle_obj)
            if muscle_obj.name in bpy.context.collection.objects:
                bpy.context.collection.objects.unlink(muscle_obj)
            
            self.report({'INFO'}, "Muscle mesh generated successfully using bmesh!")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error creating muscle mesh: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}
    
    def create_muscle_mesh_bmesh(self, context, muscle_name, curve_obj, origin_contour, insertion_contour, target_collection):
        """Create muscle mesh using bmesh operations with proper curve following"""
        
        # Create new bmesh instance
        bm = bmesh.new()
        
        try:
            # Get curve points for creating cross-sections (higher resolution for final mesh)
            curve_points = self.get_curve_sample_points(curve_obj, context.scene.muscle_resampling)
            
            if len(curve_points) < 2:
                raise Exception("Curve must have at least 2 points")
            
            # Get contour loops
            origin_loop = self.get_contour_vertices(origin_contour)
            insertion_loop = self.get_contour_vertices(insertion_contour)
            
            if not origin_loop or not insertion_loop:
                raise Exception("Both origin and insertion contours must have vertices")
            
            # Create vertex loops at each curve point following the curve path
            vertex_loops = []
            
            for i, curve_point in enumerate(curve_points):
                # Calculate parameter t along the curve (0 to 1)
                t = i / (len(curve_points) - 1) if len(curve_points) > 1 else 0.0
                
                # Get curve frame (direction and normal) at this point
                curve_direction, curve_normal, curve_binormal = self.get_curve_frame_at_point_detailed(curve_obj, curve_points, i)
                
                # Create transformation matrix for this curve position
                transform_matrix = self.create_curve_transform_matrix(curve_point, curve_direction, curve_normal, curve_binormal)
                
                # Interpolate and transform contour to follow curve
                interpolated_loop = self.interpolate_and_transform_contour_advanced(
                    origin_loop, insertion_loop, t, transform_matrix, curve_point
                )
                
                # Add vertices to bmesh
                loop_verts = []
                for vert_co in interpolated_loop:
                    vert = bm.verts.new(vert_co)
                    loop_verts.append(vert)
                
                vertex_loops.append(loop_verts)
            
            # Ensure face indices are valid
            bm.verts.ensure_lookup_table()
            
            # Bridge consecutive loops to create faces
            for i in range(len(vertex_loops) - 1):
                current_loop = vertex_loops[i]
                next_loop = vertex_loops[i + 1]
                
                # Create quad faces between loops
                self.bridge_vertex_loops(bm, current_loop, next_loop)
            
            # Create end caps
            if len(vertex_loops) > 0:
                # Origin cap
                origin_face_verts = vertex_loops[0]
                if len(origin_face_verts) > 2:
                    try:
                        bm.faces.new(origin_face_verts)
                    except ValueError:
                        pass  # Skip if face creation fails
                
                # Insertion cap
                insertion_face_verts = vertex_loops[-1]
                if len(insertion_face_verts) > 2:
                    try:
                        bm.faces.new(reversed(insertion_face_verts))  # Reverse for correct normal
                    except ValueError:
                        pass  # Skip if face creation fails
            
            # Clean up mesh
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            
            # Create mesh object
            mesh = bpy.data.meshes.new(muscle_name + "_muscle")
            bm.to_mesh(mesh)
            muscle_obj = bpy.data.objects.new(muscle_name + "_muscle", mesh)
            
            return muscle_obj
            
        finally:
            bm.free()
    
    def align_contour_loops(self, origin_loop, insertion_loop):
        """Align two contour loops to minimize twisting during lofting"""
        if not origin_loop or not insertion_loop:
            return origin_loop, insertion_loop
        
        # Ensure both loops have the same number of vertices
        target_count = max(len(origin_loop), len(insertion_loop))
        origin_resampled = self.resample_loop_improved(origin_loop, target_count)
        insertion_resampled = self.resample_loop_improved(insertion_loop, target_count)
        
        # Calculate centroids
        origin_centroid = sum(origin_resampled, Vector()) / len(origin_resampled)
        insertion_centroid = sum(insertion_resampled, Vector()) / len(insertion_resampled)
        
        # Find the best alignment by testing different starting points
        best_offset = 0
        min_twist = float('inf')
        
        for offset in range(len(insertion_resampled)):
            # Rotate insertion loop by offset
            rotated_insertion = insertion_resampled[offset:] + insertion_resampled[:offset]
            
            # Calculate total twist/distance for this alignment
            total_twist = 0
            for i in range(len(origin_resampled)):
                # Calculate relative vectors from centroids
                origin_rel = origin_resampled[i] - origin_centroid
                insertion_rel = rotated_insertion[i] - insertion_centroid
                
                # Calculate angular difference (simplified)
                origin_angle = origin_rel.xy.angle_signed(Vector((1, 0))) if origin_rel.xy.length > 0.001 else 0
                insertion_angle = insertion_rel.xy.angle_signed(Vector((1, 0))) if insertion_rel.xy.length > 0.001 else 0
                
                angle_diff = abs(origin_angle - insertion_angle)
                if angle_diff > 3.14159:  # π
                    angle_diff = 2 * 3.14159 - angle_diff
                
                total_twist += angle_diff
            
            if total_twist < min_twist:
                min_twist = total_twist
                best_offset = offset
        
        # Apply best alignment
        aligned_insertion = insertion_resampled[best_offset:] + insertion_resampled[:best_offset]
        
        return origin_resampled, aligned_insertion
    
    def resample_loop_improved(self, vertices, target_count):
        """Improved resampling that preserves curve shape better"""
        if len(vertices) == target_count:
            return vertices
        
        if len(vertices) < 2:
            return vertices * target_count if vertices else []
        
        # Calculate cumulative distances for arc-length parameterization
        distances = [0.0]
        total_length = 0.0
        
        for i in range(1, len(vertices)):
            segment_length = (vertices[i] - vertices[i-1]).length
            total_length += segment_length
            distances.append(total_length)
        
        if total_length == 0:
            return vertices * target_count if vertices else []
        
        # Resample at equal arc-length intervals
        resampled = []
        for i in range(target_count):
            if target_count == 1:
                target_distance = 0.0
            else:
                target_distance = (i / (target_count - 1)) * total_length
            
            # Find the segment containing this distance
            for j in range(len(distances) - 1):
                if distances[j] <= target_distance <= distances[j + 1]:
                    # Interpolate within this segment
                    if distances[j + 1] - distances[j] > 0:
                        t = (target_distance - distances[j]) / (distances[j + 1] - distances[j])
                    else:
                        t = 0.0
                    
                    interpolated = vertices[j].lerp(vertices[j + 1], t)
                    resampled.append(interpolated)
                    break
            else:
                # If not found, use the last vertex
                resampled.append(vertices[-1])
        
        return resampled
    
    def get_curve_frame_at_point_detailed(self, curve_obj, curve_points, index):
        """Get detailed frame (direction, normal, binormal) at curve point"""
        if len(curve_points) < 2:
            return Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))
        
        # Calculate tangent direction
        if index == 0:
            direction = (curve_points[1] - curve_points[0]).normalized()
        elif index == len(curve_points) - 1:
            direction = (curve_points[-1] - curve_points[-2]).normalized()
        else:
            # Use central difference for smoother tangent
            direction = (curve_points[index + 1] - curve_points[index - 1]).normalized()
        
        # Create orthonormal frame using Frenet frame approach
        up = Vector((0, 0, 1))
        
        # If direction is too parallel to up vector, use different reference
        if abs(direction.dot(up)) > 0.9:
            up = Vector((1, 0, 0))
        
        # Calculate normal (perpendicular to direction in horizontal plane)
        normal = direction.cross(up).normalized()
        
        # Calculate binormal (completes the orthonormal basis)
        binormal = direction.cross(normal).normalized()
        
        return direction, normal, binormal
    
    def create_curve_transform_matrix(self, position, direction, normal, binormal):
        """Create transformation matrix for curve frame"""
        # Create rotation matrix from the orthonormal frame
        rotation_matrix = Matrix((
            normal,
            binormal, 
            direction
        )).transposed()
        
        # Create full transformation matrix
        transform_matrix = Matrix.Translation(position) @ rotation_matrix.to_4x4()
        
        return transform_matrix
    
    def interpolate_and_transform_contour_advanced(self, origin_loop, insertion_loop, t, transform_matrix, curve_point):
        """Advanced interpolation and transformation that follows curve orientation"""
        
        # Ensure both loops have same number of vertices
        target_count = max(len(origin_loop), len(insertion_loop))
        origin_resampled = self.resample_loop_improved(origin_loop, target_count)
        insertion_resampled = self.resample_loop_improved(insertion_loop, target_count)
        
        # Calculate centroids for proper positioning
        origin_centroid = sum(origin_resampled, Vector()) / len(origin_resampled)
        insertion_centroid = sum(insertion_resampled, Vector()) / len(insertion_resampled)
        
        # Calculate interpolated centroid
        interpolated_centroid = origin_centroid.lerp(insertion_centroid, t)
        
        # Interpolate between contours
        interpolated_loop = []
        for i in range(target_count):
            origin_vert = origin_resampled[i]
            insertion_vert = insertion_resampled[i]
            
            # Interpolate position
            interpolated_pos = origin_vert.lerp(insertion_vert, t)
            
            # Calculate relative position from interpolated centroid
            relative_pos = interpolated_pos - interpolated_centroid
            
            # Apply curve transformation to position relative to curve point
            final_pos = curve_point + relative_pos
            
            interpolated_loop.append(final_pos)
        
        return interpolated_loop
    
    def bridge_vertex_loops(self, bm, loop1, loop2):
        """Create faces bridging two vertex loops with proper winding"""
        if len(loop1) != len(loop2) or len(loop1) < 3:
            return
        
        count = len(loop1)
        
        # Determine proper winding order by checking face normal direction
        if count > 2:
            # Test the normal direction of the first potential face
            v1 = loop1[0]
            v2 = loop1[1]
            v3 = loop2[0]
            
            # Calculate normal of test triangle
            edge1 = v2.co - v1.co
            edge2 = v3.co - v1.co
            test_normal = edge1.cross(edge2)
            
            # Compare with expected direction (should point outward from muscle)
            center1 = sum([v.co for v in loop1], Vector()) / len(loop1)
            center2 = sum([v.co for v in loop2], Vector()) / len(loop2)
            expected_direction = (center2 - center1).normalized()
            
            # If normals are pointing in opposite directions, we need to reverse winding
            reverse_winding = test_normal.dot(expected_direction) < 0
        else:
            reverse_winding = False
        
        # Create quad faces with proper winding order
        for i in range(count):
            next_i = (i + 1) % count
            
            if reverse_winding:
                # Reverse winding order
                v1 = loop1[i]
                v2 = loop2[i]
                v3 = loop2[next_i]
                v4 = loop1[next_i]
            else:
                # Normal winding order
                v1 = loop1[i]
                v2 = loop1[next_i] 
                v3 = loop2[next_i]
                v4 = loop2[i]
            
            try:
                # Check if vertices are coplanar and not degenerate
                if self.is_valid_quad(v1, v2, v3, v4):
                    bm.faces.new([v1, v2, v3, v4])
            except ValueError:
                # If quad creation fails, try creating triangles
                try:
                    bm.faces.new([v1, v2, v3])
                    bm.faces.new([v1, v3, v4])
                except ValueError:
                    continue  # Skip if face creation fails
    
    def is_valid_quad(self, v1, v2, v3, v4):
        """Check if four vertices form a valid quad"""
        # Check for degenerate cases
        if v1 == v2 or v2 == v3 or v3 == v4 or v4 == v1:
            return False
        
        # Check if vertices are roughly coplanar
        edge1 = v2.co - v1.co
        edge2 = v3.co - v1.co
        edge3 = v4.co - v1.co
        
        if edge1.length < 0.0001 or edge2.length < 0.0001 or edge3.length < 0.0001:
            return False
        
        normal1 = edge1.cross(edge2).normalized()
        normal2 = edge1.cross(edge3).normalized()
        
        # Check if normals are roughly aligned (coplanar)
        return abs(normal1.dot(normal2)) > 0.8
    


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
            
            # Only update on timer events to avoid excessive updates
            if event.type != 'TIMER':
                return {'PASS_THROUGH'}
            
            # Get muscle collection and objects
            muscles_collection = bpy.data.collections.get("muscles")
            if not muscles_collection or muscle_name not in muscles_collection.children:
                self.finish_preview(context)
                return {'FINISHED'}
            
            target_collection = muscles_collection.children[muscle_name]
            curve_obj = target_collection.objects.get(muscle_name + "_curve")
            
            if not curve_obj:
                return {'PASS_THROUGH'}
            
            # Check if curve has changed
            current_curve_hash = self.get_curve_hash(curve_obj)
            if current_curve_hash != self._last_curve_hash:
                self._last_curve_hash = current_curve_hash
                self.update_preview_mesh(context, muscle_name, target_collection)
                context.area.tag_redraw()
            
            return {'PASS_THROUGH'}
            
        except Exception as e:
            print(f"Preview modal error: {e}")
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
        
        # Add timer and modal handler with longer interval
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)  # Reduced frequency
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
        if self._preview_object and self._preview_object.name in bpy.data.objects:
            self._preview_object.name = self._preview_object.name.replace("_preview", "_preview_static")
            self._preview_object = None
    
    def get_curve_hash(self, curve_obj):
        """Create a more sensitive hash of curve point positions"""
        if not curve_obj or not curve_obj.data.splines:
            return 0
        
        hash_val = 0
        spline = curve_obj.data.splines[0]
        
        if spline.type in ['NURBS', 'POLY']:
            for i, point in enumerate(spline.points):
                world_co = curve_obj.matrix_world @ Vector(point.co[:3])
                # Use higher precision for more sensitive detection
                hash_val += hash((round(world_co.x, 6), round(world_co.y, 6), round(world_co.z, 6), i))
        elif spline.type == 'BEZIER':
            for i, point in enumerate(spline.bezier_points):
                world_co = curve_obj.matrix_world @ point.co
                # Include handle positions for Bezier curves
                handle_left = curve_obj.matrix_world @ point.handle_left
                handle_right = curve_obj.matrix_world @ point.handle_right
                hash_val += hash((
                    round(world_co.x, 6), round(world_co.y, 6), round(world_co.z, 6),
                    round(handle_left.x, 6), round(handle_left.y, 6), round(handle_left.z, 6),
                    round(handle_right.x, 6), round(handle_right.y, 6), round(handle_right.z, 6),
                    i
                ))
        
        return hash_val
    
    def update_preview_mesh(self, context, muscle_name, target_collection):
        """Update the preview mesh based on current curve"""
        try:
            # Get required objects
            curve_obj = target_collection.objects.get(muscle_name + "_curve")
            origin_contour = target_collection.objects.get(muscle_name + "_origin_contour")
            insertion_contour = target_collection.objects.get(muscle_name + "_insertion_contour")
            
            if not all([curve_obj, origin_contour, insertion_contour]):
                print("Missing required objects for preview")
                return False
            
            # Remove existing preview
            if self._preview_object and self._preview_object.name in bpy.data.objects:
                bpy.data.objects.remove(self._preview_object, do_unlink=True)
                self._preview_object = None
            
            # Create new preview mesh using simplified algorithm
            preview_mesh = self.create_simple_preview_mesh(
                context, curve_obj, origin_contour, insertion_contour
            )
            
            if preview_mesh:
                # Create preview object
                self._preview_object = bpy.data.objects.new(muscle_name + "_preview", preview_mesh)
                target_collection.objects.link(self._preview_object)
                
                # Set material to make it look like a preview
                self.apply_preview_material(self._preview_object)
                
                # Update viewport
                context.view_layer.update()
                return True
            
            return False
                
        except Exception as e:
            print(f"Error updating preview: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_simple_preview_mesh(self, context, curve_obj, origin_contour, insertion_contour):
        """Create preview mesh using simplified but working algorithm"""
        bm = bmesh.new()
        
        try:
            # Get fewer sample points for preview performance
            curve_points = self.get_curve_sample_points(curve_obj, 6)
            
            if len(curve_points) < 2:
                print("Not enough curve points")
                return None
            
            # Get contour vertices
            origin_loop = self.get_contour_vertices(origin_contour)
            insertion_loop = self.get_contour_vertices(insertion_contour)
            
            if not origin_loop or not insertion_loop:
                print("Missing contour vertices")
                return None
            
            # Calculate original centroids
            origin_centroid = sum(origin_loop, Vector()) / len(origin_loop)
            insertion_centroid = sum(insertion_loop, Vector()) / len(insertion_loop)
            
            # Ensure same vertex count (simple resampling)
            target_count = min(len(origin_loop), len(insertion_loop), 12)  # Limit for preview
            origin_resampled = self.simple_resample(origin_loop, target_count)
            insertion_resampled = self.simple_resample(insertion_loop, target_count)
            
            # Create vertex loops along curve
            vertex_loops = []
            
            for i, curve_point in enumerate(curve_points):
                t = i / (len(curve_points) - 1) if len(curve_points) > 1 else 0.0
                
                # Calculate interpolated centroid position
                interpolated_centroid = origin_centroid.lerp(insertion_centroid, t)
                
                # Calculate offset from original line to curve point
                original_line_point = origin_centroid.lerp(insertion_centroid, t)
                curve_offset = curve_point - original_line_point
                
                # Create interpolated loop that follows the curve
                interpolated_loop = []
                for j in range(target_count):
                    origin_vert = origin_resampled[j]
                    insertion_vert = insertion_resampled[j]
                    
                    # Interpolate position
                    interpolated_pos = origin_vert.lerp(insertion_vert, t)
                    
                    # Apply curve offset to make it follow the curve path
                    final_pos = interpolated_pos + curve_offset
                    interpolated_loop.append(final_pos)
                
                # Add vertices to bmesh
                loop_verts = []
                for vert_co in interpolated_loop:
                    vert = bm.verts.new(vert_co)
                    loop_verts.append(vert)
                
                vertex_loops.append(loop_verts)
            
            # Ensure bmesh is valid
            bm.verts.ensure_lookup_table()
            
            # Bridge loops with simple quad creation
            for i in range(len(vertex_loops) - 1):
                current_loop = vertex_loops[i]
                next_loop = vertex_loops[i + 1]
                
                if len(current_loop) == len(next_loop):
                    for j in range(len(current_loop)):
                        j_next = (j + 1) % len(current_loop)
                        
                        v1 = current_loop[j]
                        v2 = current_loop[j_next]
                        v3 = next_loop[j_next]
                        v4 = next_loop[j]
                        
                        try:
                            bm.faces.new([v1, v2, v3, v4])
                        except ValueError:
                            # Try triangles if quad fails
                            try:
                                bm.faces.new([v1, v2, v3])
                                bm.faces.new([v1, v3, v4])
                            except ValueError:
                                continue
            
            # Add end caps
            if len(vertex_loops) > 0 and len(vertex_loops[0]) > 2:
                try:
                    bm.faces.new(vertex_loops[0])
                except ValueError:
                    pass
                
                try:
                    bm.faces.new(reversed(vertex_loops[-1]))
                except ValueError:
                    pass
            
            # Clean up
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            
            # Create mesh
            mesh = bpy.data.meshes.new("preview_mesh")
            bm.to_mesh(mesh)
            mesh.update()
            
            return mesh
            
        except Exception as e:
            print(f"Error in create_simple_preview_mesh: {e}")
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
    
    def apply_preview_material(self, obj):
        """Apply a preview material to make it distinguishable"""
        mat_name = "MusclePreviewMaterial"
        
        # Create or get preview material
        if mat_name not in bpy.data.materials:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            
            # Simple orange material
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs[0].default_value = (1.0, 0.4, 0.0, 1.0)  # Orange
            bsdf.inputs[18].default_value = 0.3  # Alpha for transparency
            
            mat.blend_method = 'BLEND'
            mat.show_transparent_back = True
        else:
            mat = bpy.data.materials[mat_name]
        
        # Apply material
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
        
        # Set display properties
        obj.show_transparent = True


class Muscle_Finalize_Op(bpy.types.Operator):
    """Convert muscle to final mesh"""
    bl_idname = "view3d.muscle_finalize"
    bl_label = "Finalize Muscle"
    bl_description = "Convert the procedural muscle to a final mesh object"
    
    def execute(self, context):
        muscle_name = context.scene.muscle_Name
        
        # Get muscle collection
        muscles_collection = bpy.data.collections.get("muscles")
        if not muscles_collection or muscle_name not in muscles_collection.children:
            self.report({'ERROR'}, f"Collection '{muscle_name}' not found")
            return {'CANCELLED'}
        
        target_collection = muscles_collection.children[muscle_name]
        muscle_obj = target_collection.objects.get(muscle_name + "_muscle")
        
        if not muscle_obj:
            self.report({'ERROR'}, "Muscle object not found")
            return {'CANCELLED'}
        
        # Switch to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select muscle object
        muscle_obj.select_set(True)
        context.view_layer.objects.active = muscle_obj
        
        # Convert to mesh
        bpy.ops.object.convert(target='MESH')
        
        # Clean up the mesh
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.mesh.select_non_manifold()
        if context.object.data.total_edge_sel > 0:
            bpy.ops.mesh.edge_face_add()
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, f"Muscle '{muscle_name}' finalized as mesh")
        return {'FINISHED'}


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
                bpy.data.objects.remove(preview_obj, do_unlink=True)
        
        self.report({'INFO'}, "Preview stopped")
        return {'FINISHED'}
