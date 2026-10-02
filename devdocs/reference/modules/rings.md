# `rings`

Source: `rings.py`

Section rings on the muscle path.

The muscle path `<M>_curve` gives the course of the belly; rings placed on
it, `<M>_ring_00` … `<M>_ring_NN`, give the size and turn of the section
there (`ring_sections`), and the belly blends smoothly from ring to
ring (`tube.path_tube`):

* the first and last rings sit at the two ends of the path and cannot move;
* the other rings **slide along the path** (G): a ring acts at the point of
  the path nearest to it, so while it is dragged the bulge slides along the
  path, and once released it snaps back onto the path (`align_rings`);
  moving the middle ring towards the origin moves the bulge there;
* **S** scales a ring (S X X width, S Y Y thickness: local axes);
* **R** turns it about the path (the width direction).

Rings store changes **relative to the muscle's natural section** (the
muscle type's profile, or the natural width, thickness and orientation of a
fan): an untouched ring changes nothing, scaling one ×1.5 makes the section
1.5 times its natural size there, turning it turns the section from its
natural orientation (`ring_sections`). Each ring is a circle of radius
1 (local XY plane) drawn at the actual section size; after every rebuild the
rings are shown again on the path, perpendicular to it (`align_rings`).

## Constants

| Name | Value |
|---|---|
| `RING_INFIX` | `'_ring_'` |
| `RING_ROLE` | `'ring'` |
| `RING_CURVE` | `'MyoGen ring'` |
| `RING_COLOR` | `(1.0, 0.5, 0.05, 1.0)` |
| `SCALE_KEY` | `'myo_ring_scale'` |
| `TURN_KEY` | `'myo_ring_turn'` |
| `SHOWN_KEY` | `'myo_ring_shown'` |

## Functions

### `ring_objects(collection, muscle_name)`

The muscle's rings, sorted by name.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |

**Returns** (list of `bpy.types.Object`): 

### `is_ring(obj, muscle_name)`

True if `obj` is one of the muscle's rings.

| Parameter | Type | Description |
|---|---|---|
| `obj` | `bpy.types.Object` | Any object. |
| `muscle_name` | str | Muscle name. |

**Returns** (bool): 

### `remove_rings(collection, muscle_name)`

Delete all of the muscle's rings (and the shared ring curve once unused).

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |

### `create_rings(collection, muscle_name, path_obj, us, natural)`

Replace the muscle's rings with rings at `us` showing the natural section.

A new ring changes nothing: its stored scale is (1, 1) and its turn 0
(see `ring_sections`).

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `path_obj` | `bpy.types.Object` | The muscle path. |
| `us` | list of float | Arc-length fractions; the first and last are put at 0 and 1. |
| `natural` | callable | `natural(u) -> (half_width, half_thickness, angle)` of the muscle without rings. |

**Returns** (list of `bpy.types.Object`): The rings, origin to insertion.

### `default_rings(collection, muscle_name, path_obj, natural, count)`

Replace the rings with `count` rings evenly spaced along the path.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `path_obj` | `bpy.types.Object` | The muscle path. |
| `natural` | callable | See `create_rings`. |
| `count` | int | Number of rings (≥ 2). |

**Returns** (list of `bpy.types.Object`): 

### `ring_sections(rings, points, natural)`

Sections `(u, half_width, half_thickness, twist)` set by the rings.

A ring stores a change relative to the muscle's natural section
(`natural(u)`, which depends on the muscle type): a scale (X width,
Y thickness) and a turn. A ring the user has not touched gives the
natural section exactly, whatever the type. When the user scales or
turns a ring, the change from what was last shown (`align_rings`)
multiplies the stored scale / adds to the stored turn, once: the current
state becomes the shown one, so reading the rings again changes nothing.
Rings without stored values (earlier versions) start from the natural
section.

`u` is the arc-length fraction of the path point nearest to the ring;
the end rings are always at 0 and 1.

| Parameter | Type | Description |
|---|---|---|
| `rings` | list of `bpy.types.Object` | Ring objects (origin to insertion by name). |
| `points` | list of `mathutils.Vector` | Arc-length samples of the path (`tube.sample_path`). |
| `natural` | callable | `natural(u) -> (half_width, half_thickness, angle)`. |

**Returns** (list of tuple): 

### `align_rings(rings, points, sections)`

Show the rings on the path, perpendicular to it, at their section's size and turn.

What is shown is remembered (`SHOWN_KEY`) so later user changes can be
told apart (`ring_sections`).

| Parameter | Type | Description |
|---|---|---|
| `rings` | list of `bpy.types.Object` | Ring objects. |
| `points` | list of `mathutils.Vector` | Arc-length samples of the path. |
| `sections` | list of tuple | Their sections `(u, half_width, half_thickness, twist)`. |

### `set_visible(collection, muscle_name, visible)`

Show or hide the muscle's rings.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `visible` | bool | True to show them. |
