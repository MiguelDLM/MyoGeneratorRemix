# `fibre_texture`

Source: `fibre_texture.py`

Fibre-oriented muscle texture (visual only).

The procedural muscle material (`muscle_texture`) draws elongated fibre
bundles. Here its texture coordinates follow the muscle's fibre architecture
instead of the object's axes: for every vertex of a belly
`fibre_coordinates` measures where it lies along the muscle path,
across the section's width and through its thickness, and turns that into a
*phase* (constant along a fibre, changing across fibres) and an *along*
coordinate for the chosen arrangement:

=============  =================================================================
Parallel       fibres along the path, evenly spaced across the width
Fusiform       fibres along the path, converging towards both ends
Convergent     fibres fanning out from the insertion (fan-shaped muscles)
Pennate        fibres at the pennation angle from a tendon along one side
Bipennate      fibres in a "V" from a central tendon
Multipennate   several internal tendons, fibres in alternating "V"s
=============  =================================================================

The coordinates are stored on the mesh as the point attributes
`myo_fibre` (vector: along, phase, depth, normalised 0-1 like object
coordinates), `myo_fibre_u` (0 at the origin, 1 at the insertion) and
`myo_tendon` (pale tendon colour weight), which the muscle material reads
(`muscle_texture.create_fibre_material`). Each belly carries its
choices in `Object.myogen_fibres`, `Object.myogen_pennation` and
`Object.myogen_tendon_origin` / `_insertion` / `_fade` (the tendon
colour follows the distance to each attachment surface); changing any recomputes
the attributes at once.

## Constants

| Name | Value |
|---|---|
| `ARRANGEMENTS` | `[('PARALLEL', 'Parallel', 'Fibres run along the muscle, evenly spaced across its width'...` |
| `PENNATE` | `{'PENNATE', 'BIPENNATE', 'MULTIPENNATE'}` |
| `MULTIPENNATE_TENDONS` | `3` |
| `SECTION_BINS` | `24` |
| `ROUND_SECTION` | `0.6` |
| `RADIUS_SMOOTHING` | `7` |
| `TYPE_ARRANGEMENT` | `{'FUSIFORM': 'FUSIFORM', 'PARALLEL': 'PARALLEL', 'FAN': 'CONVERGENT'}` |
| `DEFAULT_BUNDLES` | `30.0` |
| `MATERIAL_CELLS_ACROSS` | `144.0` |
| `BUMP_PER_BUNDLE` | `2.0` |
| `DEFAULT_TENDON_FADE` | `0.08` |
| `DEFAULT_TENDON` | `0.01` |
| `DEFAULT_PENNATION` | `20.0` |

## Functions

### `fibre_coordinates(vertices, path_points, arrangement, pennation_deg=DEFAULT_PENNATION, bundles=None)`

Fibre texture coordinates of points of a belly.

| Parameter | Type | Description |
|---|---|---|
| `vertices` | `numpy.ndarray` | World-space vertex positions, (N, 3). |
| `path_points` | list of `mathutils.Vector` | Arc-length samples of the muscle path (`tube.sample_path`). |
| `arrangement` | str | One of `ARRANGEMENTS`. |
| `pennation_deg` | float | Angle between fibres and tendon (pennate arrangements). |
| `bundles` | float | Fibre bundles across the muscle's width drawn by the material (default `DEFAULT_BUNDLES`); scales the across and depth coordinates. |

**Returns** (tuple of `numpy.ndarray`): `(coords, u)`: (N, 3) `(along, phase, depth)` in units such that `bundles` bundles span the mean width, and (N,) position along the path (0-1).

### `bundle_size(vertices, coords)`

World size of one unit of the fibre coordinates (Blender units per unit).

| Parameter | Type | Description |
|---|---|---|
| `vertices` | `numpy.ndarray` | World-space vertex positions, (N, 3). |
| `coords` | `numpy.ndarray` | Their fibre coordinates (`fibre_coordinates`). |

**Returns** (float): 

### `attachment_distance(vertices, surface_obj)`

Distance of each point to an attachment surface (Blender units).

| Parameter | Type | Description |
|---|---|---|
| `vertices` | `numpy.ndarray` | World-space points, (N, 3). |
| `surface_obj` | `bpy.types.Object` | Attachment surface. |

**Returns** (`numpy.ndarray`): 

### `tendon_mask(d_origin, d_insertion, origin_extent, insertion_extent, fade)`

Tendon colour weight (0-1) from the distance to each attachment.

Solid tendon within `*_extent` of the attachment surface (so it follows
the attachment's outline: a line, a "]", a patch), then a smooth fade
into the muscle over `fade`; all as fractions of the muscle length.
A 0 extent gives no tendon at that end.

| Parameter | Type | Description |
|---|---|---|
| `d_origin` | `numpy.ndarray` | Distance of each point to the origin attachment / muscle length. |
| `d_insertion` | `numpy.ndarray` | Distance to the insertion attachment / muscle length. |
| `origin_extent` | float | Solid tendon reach from the origin. |
| `insertion_extent` | float | Solid tendon reach from the insertion. |
| `fade` | float | Width of the fade into the muscle. |

**Returns** (`numpy.ndarray`): 

### `apply_fibre_texture(context, belly, arrangement=None, pennation_deg=None)`

Write the fibre coordinates on a belly and give it the fibre material.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context. |
| `belly` | `bpy.types.Object` | Final belly (its collection holds the muscle path). |
| `arrangement` | str | Arrangement (default: `belly.myogen_fibres`). |
| `pennation_deg` | float | Pennation angle (default: `belly.myogen_pennation`). |

**Returns** (bool): True if applied (False without a path).

### `default_arrangement(props)`

Arrangement used for a new belly of the current muscle type.

| Parameter | Type | Description |
|---|---|---|
| `props` | `properties.MyoGeneratorProperties` | Scene settings. |

**Returns** (str): 

### `set_defaults(belly, props)`

Give a new belly the default arrangement of its type (no recomputation).

| Parameter | Type | Description |
|---|---|---|
| `belly` | `bpy.types.Object` | Final belly. |
| `props` | `properties.MyoGeneratorProperties` | Scene settings (muscle type, pennation angle). |
