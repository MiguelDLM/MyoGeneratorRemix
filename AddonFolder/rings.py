"""Section rings on the muscle path.

The muscle path ``<M>_curve`` gives the course of the belly; rings placed on
it, ``<M>_ring_00`` … ``<M>_ring_NN``, give the size and turn of the section
there (:func:`ring_sections`), and the belly blends smoothly from ring to
ring (:func:`tube.path_tube`):

* the first and last rings sit at the two ends of the path and cannot move;
* the other rings **slide along the path** (G): a ring acts at the point of
  the path nearest to it, so while it is dragged the bulge slides along the
  path, and once released it snaps back onto the path (:func:`align_rings`);
  moving the middle ring towards the origin moves the bulge there;
* **S** scales a ring (S X X width, S Y Y thickness: local axes);
* **R** turns it about the path (the width direction).

Each ring is a circle of radius 1 (local XY plane), so its X and Y scales are
the section radii in Blender units. After every rebuild the rings are put
back perpendicular to the path at their position (:func:`align_rings`),
keeping their size and turn.
"""

import math

import bpy
from mathutils import Matrix, Vector

from . import myo_record, tube

#: Ring object names: ``<M>`` + ``RING_INFIX`` + two-digit index.
RING_INFIX = "_ring_"
#: ``myo_role`` of the ring objects.
RING_ROLE = "ring"
#: Shared circle curve of the rings (radius 1, XY plane).
RING_CURVE = "MyoGen ring"
#: Viewport colour of the rings.
RING_COLOR = (1.0, 0.5, 0.05, 1.0)


def _ring_curve():
    curve = bpy.data.curves.get(RING_CURVE)
    if curve is None:
        curve = bpy.data.curves.new(RING_CURVE, type='CURVE')
        curve.dimensions = '3D'
        spline = curve.splines.new('POLY')
        spline.points.add(31)
        for k, p in enumerate(spline.points):
            a = 2 * math.pi * k / 32
            p.co = (math.cos(a), math.sin(a), 0.0, 1.0)
        spline.use_cyclic_u = True
    return curve


def ring_objects(collection, muscle_name):
    """The muscle's rings, sorted by name.

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :rtype: list of :class:`bpy.types.Object`
    """
    prefix = muscle_name + RING_INFIX
    found = [o for o in collection.objects if o.name.startswith(prefix) and o.name[len(prefix):].isdigit()]
    return sorted(found, key=lambda o: int(o.name[len(prefix):]))


def is_ring(obj, muscle_name):
    """True if ``obj`` is one of the muscle's rings.

    :arg obj: Any object.
    :type obj: :class:`bpy.types.Object`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :rtype: bool
    """
    prefix = muscle_name + RING_INFIX
    return obj.name.startswith(prefix) and obj.name[len(prefix):].isdigit()


def _frame_at(points, tangents, normals, u):
    s = min(max(u, 0.0), 1.0) * (len(points) - 1)
    k = min(int(s), len(points) - 2)
    x = s - k
    t = tangents[k].lerp(tangents[k + 1], x).normalized()
    n = normals[k].lerp(normals[k + 1], x)
    n = (n - t * n.dot(t)).normalized()
    return points[k].lerp(points[k + 1], x), t, n


def _matrix(location, tangent, normal, twist, width, thickness):
    b = tangent.cross(normal)
    x = normal * math.cos(twist) + b * math.sin(twist)
    y = tangent.cross(x)
    rot = Matrix((x, y, tangent)).transposed().to_4x4()
    return Matrix.Translation(location) @ rot @ Matrix.Diagonal((width, thickness, 1.0, 1.0))


def remove_rings(collection, muscle_name):
    """Delete all of the muscle's rings (and the shared ring curve once unused).

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    """
    for obj in ring_objects(collection, muscle_name):
        bpy.data.objects.remove(obj, do_unlink=True)
    curve = bpy.data.curves.get(RING_CURVE)
    if curve is not None and curve.users == 0:               # no rings left in the file
        bpy.data.curves.remove(curve)


def create_rings(collection, muscle_name, path_obj, sections):
    """Replace the muscle's rings with one ring per section, placed on the path.

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg path_obj: The muscle path.
    :type path_obj: :class:`bpy.types.Object`
    :arg sections: ``(u, width, thickness, twist)``; the first and last are
       put at the ends of the path (u = 0 and 1).
    :type sections: list of tuple
    :return: The rings, origin to insertion.
    :rtype: list of :class:`bpy.types.Object`
    """
    remove_rings(collection, muscle_name)
    points = tube.sample_path(path_obj)
    tangents, normals = tube.frames(points)
    rings = []
    last = len(sections) - 1
    for k, (u, w, h, twist) in enumerate(sections):
        u = 0.0 if k == 0 else 1.0 if k == last else u
        obj = bpy.data.objects.new(f"{muscle_name}{RING_INFIX}{k:02d}", _ring_curve())
        collection.objects.link(obj)
        obj[myo_record.ROLE_KEY] = RING_ROLE
        obj.show_in_front = True
        obj.color = RING_COLOR
        p, t, n = _frame_at(points, tangents, normals, u)
        obj.matrix_world = _matrix(p, t, n, twist, w, h)
        if k in (0, last):
            obj.lock_location = (True, True, True)            # the ends stay at the attachments
        rings.append(obj)
    return rings


def default_rings(collection, muscle_name, path_obj, origin_surface, insertion_surface, shape, count):
    """Replace the rings with ``count`` rings evenly spaced along the path,
    sized by the muscle type's default profile.

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg path_obj: The muscle path.
    :type path_obj: :class:`bpy.types.Object`
    :arg origin_surface: Origin attachment surface.
    :type origin_surface: :class:`bpy.types.Object`
    :arg insertion_surface: Insertion attachment surface.
    :type insertion_surface: :class:`bpy.types.Object`
    :arg shape: Muscle type.
    :type shape: str
    :arg count: Number of rings (≥ 2).
    :type count: int
    :rtype: list of :class:`bpy.types.Object`
    """
    profile = tube.default_profile(origin_surface, insertion_surface, shape)
    count = max(2, count)
    sections = []
    for k in range(count):
        u = k / (count - 1)
        w, h, twist = tube._interp_sections(profile, u)
        sections.append((u, w, h, twist))
    return create_rings(collection, muscle_name, path_obj, sections)


def ring_sections(rings, points):
    """Sections ``(u, width, thickness, twist)`` given by the rings on a sampled path.

    ``u`` is the arc-length fraction of the path point nearest to the ring;
    the end rings are always at 0 and 1. Width and thickness are the ring's
    X and Y scales; the twist is the angle of its X axis about the path,
    from the path's parallel-transported normal.

    :arg rings: Ring objects (origin to insertion by name).
    :type rings: list of :class:`bpy.types.Object`
    :arg points: Arc-length samples of the path (:func:`tube.sample_path`).
    :type points: list of :class:`mathutils.Vector`
    :rtype: list of tuple
    """
    tangents, normals = tube.frames(points)
    out = []
    last = len(rings) - 1
    for k, ring in enumerate(rings):
        mw = ring.matrix_world
        u = 0.0 if k == 0 else 1.0 if k == last else tube.project_on_path(points, mw.translation)
        _p, t, n = _frame_at(points, tangents, normals, u)
        x = Vector(mw.col[0][:3])
        y = Vector(mw.col[1][:3])
        flat = x - t * x.dot(t)
        twist = math.atan2(flat.dot(t.cross(n)), flat.dot(n)) if flat.length > 1e-9 else 0.0
        out.append((u, max(x.length, 1e-6), max(y.length, 1e-6), twist))
    return out


def align_rings(rings, points, sections=None):
    """Put the rings back on the path, perpendicular to it, keeping size and turn.

    :arg rings: Ring objects.
    :type rings: list of :class:`bpy.types.Object`
    :arg points: Arc-length samples of the path.
    :type points: list of :class:`mathutils.Vector`
    :arg sections: Their current sections (:func:`ring_sections`), or None.
    :type sections: list of tuple
    """
    sections = sections or ring_sections(rings, points)
    tangents, normals = tube.frames(points)
    for ring, (u, w, h, twist) in zip(rings, sections):
        p, t, n = _frame_at(points, tangents, normals, u)
        ring.matrix_world = _matrix(p, t, n, twist, w, h)


def set_visible(collection, muscle_name, visible):
    """Show or hide the muscle's rings.

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg visible: True to show them.
    :type visible: bool
    """
    for ring in ring_objects(collection, muscle_name):
        try:
            ring.hide_set(not visible)
        except RuntimeError:
            ring.hide_viewport = not visible
