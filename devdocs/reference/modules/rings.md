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

Each ring is a circle of radius 1 (local XY plane), so its X and Y scales are
the section radii in Blender units. After every rebuild the rings are put
back perpendicular to the path at their position (`align_rings`),
keeping their size and turn.

## Constants

| Name | Value |
|---|---|
| `RING_INFIX` | `'_ring_'` |
| `RING_ROLE` | `'ring'` |
| `RING_CURVE` | `'MyoGen ring'` |
| `RING_COLOR` | `(1.0, 0.5, 0.05, 1.0)` |

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

### `create_rings(collection, muscle_name, path_obj, sections)`

Replace the muscle's rings with one ring per section, placed on the path.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `path_obj` | `bpy.types.Object` | The muscle path. |
| `sections` | list of tuple | `(u, width, thickness, twist)`; the first and last are put at the ends of the path (u = 0 and 1). |

**Returns** (list of `bpy.types.Object`): The rings, origin to insertion.

### `default_rings(collection, muscle_name, path_obj, origin_surface, insertion_surface, shape, count)`

Replace the rings with `count` rings evenly spaced along the path,
sized by the muscle type's default profile.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `path_obj` | `bpy.types.Object` | The muscle path. |
| `origin_surface` | `bpy.types.Object` | Origin attachment surface. |
| `insertion_surface` | `bpy.types.Object` | Insertion attachment surface. |
| `shape` | str | Muscle type. |
| `count` | int | Number of rings (≥ 2). |

**Returns** (list of `bpy.types.Object`): 

### `ring_sections(rings, points)`

Sections `(u, width, thickness, twist)` given by the rings on a sampled path.

`u` is the arc-length fraction of the path point nearest to the ring;
the end rings are always at 0 and 1. Width and thickness are the ring's
X and Y scales; the twist is the angle of its X axis about the path,
from the path's parallel-transported normal.

| Parameter | Type | Description |
|---|---|---|
| `rings` | list of `bpy.types.Object` | Ring objects (origin to insertion by name). |
| `points` | list of `mathutils.Vector` | Arc-length samples of the path (`tube.sample_path`). |

**Returns** (list of tuple): 

### `align_rings(rings, points, sections=None)`

Put the rings back on the path, perpendicular to it, keeping size and turn.

| Parameter | Type | Description |
|---|---|---|
| `rings` | list of `bpy.types.Object` | Ring objects. |
| `points` | list of `mathutils.Vector` | Arc-length samples of the path. |
| `sections` | list of tuple | Their current sections (`ring_sections`), or None. |

### `set_visible(collection, muscle_name, visible)`

Show or hide the muscle's rings.

| Parameter | Type | Description |
|---|---|---|
| `collection` | `bpy.types.Collection` | Muscle collection. |
| `muscle_name` | str | Muscle name. |
| `visible` | bool | True to show them. |
