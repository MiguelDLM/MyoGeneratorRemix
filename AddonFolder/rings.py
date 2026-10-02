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

Rings store changes **relative to the muscle's natural section** (the
muscle type's profile, or the natural width, thickness and orientation of a
fan): an untouched ring changes nothing, scaling one ×1.5 makes the section
1.5 times its natural size there, turning it turns the section from its
natural orientation (:func:`ring_sections`). Each ring is a circle of radius
1 (local XY plane) drawn at the actual section size; after every rebuild the
rings are shown again on the path, perpendicular to it (:func:`align_rings`).
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
#: Ring property: scale (X width, Y thickness) relative to the natural section.
SCALE_KEY = "myo_ring_scale"
#: Ring property: turn (radians) relative to the natural orientation.
TURN_KEY = "myo_ring_turn"
#: Ring property: ``(half_width, half_thickness, twist)`` last shown.
SHOWN_KEY = "myo_ring_shown"


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


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def create_rings(collection, muscle_name, path_obj, us, natural):
    """Replace the muscle's rings with rings at ``us`` showing the natural section.

    A new ring changes nothing: its stored scale is (1, 1) and its turn 0
    (see :func:`ring_sections`).

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg path_obj: The muscle path.
    :type path_obj: :class:`bpy.types.Object`
    :arg us: Arc-length fractions; the first and last are put at 0 and 1.
    :type us: list of float
    :arg natural: ``natural(u) -> (half_width, half_thickness, angle)`` of the
       muscle without rings.
    :type natural: callable
    :return: The rings, origin to insertion.
    :rtype: list of :class:`bpy.types.Object`
    """
    remove_rings(collection, muscle_name)
    points = tube.sample_path(path_obj)
    rings = []
    last = len(us) - 1
    for k, u in enumerate(us):
        u = 0.0 if k == 0 else 1.0 if k == last else u
        obj = bpy.data.objects.new(f"{muscle_name}{RING_INFIX}{k:02d}", _ring_curve())
        collection.objects.link(obj)
        obj[myo_record.ROLE_KEY] = RING_ROLE
        obj[SCALE_KEY] = (1.0, 1.0)
        obj[TURN_KEY] = 0.0
        obj.show_in_front = True
        obj.color = RING_COLOR
        if k in (0, last):
            obj.lock_location = (True, True, True)            # the ends stay at the attachments
        rings.append(obj)
    w_h_a = [natural(0.0 if k == 0 else 1.0 if k == last else u) for k, u in enumerate(us)]
    align_rings(rings, points, [(0.0 if k == 0 else 1.0 if k == last else u, w, h, a)
                                for k, (u, (w, h, a)) in enumerate(zip(us, w_h_a))])
    return rings


def default_rings(collection, muscle_name, path_obj, natural, count):
    """Replace the rings with ``count`` rings evenly spaced along the path.

    :arg collection: Muscle collection.
    :type collection: :class:`bpy.types.Collection`
    :arg muscle_name: Muscle name.
    :type muscle_name: str
    :arg path_obj: The muscle path.
    :type path_obj: :class:`bpy.types.Object`
    :arg natural: See :func:`create_rings`.
    :type natural: callable
    :arg count: Number of rings (≥ 2).
    :type count: int
    :rtype: list of :class:`bpy.types.Object`
    """
    count = max(2, count)
    return create_rings(collection, muscle_name, path_obj, [k / (count - 1) for k in range(count)], natural)


def ring_sections(rings, points, natural):
    """Sections ``(u, half_width, half_thickness, twist)`` set by the rings.

    A ring stores a change relative to the muscle's natural section
    (``natural(u)``, which depends on the muscle type): a scale (X width,
    Y thickness) and a turn. A ring the user has not touched gives the
    natural section exactly, whatever the type. When the user scales or
    turns a ring, the change from what was last shown (:func:`align_rings`)
    multiplies the stored scale / adds to the stored turn, once: the current
    state becomes the shown one, so reading the rings again changes nothing.
    Rings without stored values (earlier versions) start from the natural
    section.

    ``u`` is the arc-length fraction of the path point nearest to the ring;
    the end rings are always at 0 and 1.

    :arg rings: Ring objects (origin to insertion by name).
    :type rings: list of :class:`bpy.types.Object`
    :arg points: Arc-length samples of the path (:func:`tube.sample_path`).
    :type points: list of :class:`mathutils.Vector`
    :arg natural: ``natural(u) -> (half_width, half_thickness, angle)``.
    :type natural: callable
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
        w, h = max(x.length, 1e-9), max(y.length, 1e-9)
        if SCALE_KEY not in ring or SHOWN_KEY not in ring:
            ring[SCALE_KEY], ring[TURN_KEY] = (1.0, 1.0), 0.0
        else:
            sx, sy = ring[SCALE_KEY]
            shown_w, shown_h, shown_twist = ring[SHOWN_KEY]
            if abs(w / shown_w - 1) > 1e-4 or abs(h / shown_h - 1) > 1e-4:
                sx, sy = sx * w / shown_w, sy * h / shown_h
            turn = ring[TURN_KEY] + _wrap(twist - shown_twist) if abs(_wrap(twist - shown_twist)) > 1e-4 \
                else ring[TURN_KEY]
            ring[SCALE_KEY], ring[TURN_KEY] = (sx, sy), turn
        ring[SHOWN_KEY] = (float(w), float(h), float(twist))   # absorbed: reading again changes nothing
        w0, h0, a0 = natural(u)
        sx, sy = ring[SCALE_KEY]
        out.append((u, max(w0 * sx, 1e-6), max(h0 * sy, 1e-6), a0 + ring[TURN_KEY]))
    return out


def align_rings(rings, points, sections):
    """Show the rings on the path, perpendicular to it, at their section's size and turn.

    What is shown is remembered (``SHOWN_KEY``) so later user changes can be
    told apart (:func:`ring_sections`).

    :arg rings: Ring objects.
    :type rings: list of :class:`bpy.types.Object`
    :arg points: Arc-length samples of the path.
    :type points: list of :class:`mathutils.Vector`
    :arg sections: Their sections ``(u, half_width, half_thickness, twist)``.
    :type sections: list of tuple
    """
    tangents, normals = tube.frames(points)
    for ring, (u, w, h, twist) in zip(rings, sections):
        p, t, n = _frame_at(points, tangents, normals, u)
        ring.matrix_world = _matrix(p, t, n, twist, w, h)
        ring[SHOWN_KEY] = (float(w), float(h), float(twist))


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
