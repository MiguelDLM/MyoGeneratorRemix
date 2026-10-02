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
`myo_fibre` (vector: phase, along, depth, scaled by the path length) and
`myo_fibre_u` (0 at the origin, 1 at the insertion, for the tendon tint),
which the material reads. Each belly carries its choice in
`Object.myogen_fibres` (and `Object.myogen_pennation`); changing either
recomputes the coordinates at once.

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
| `DEFAULT_PENNATION` | `20.0` |

## Functions

### `fibre_coordinates(vertices, path_points, arrangement, pennation_deg=DEFAULT_PENNATION)`

Fibre texture coordinates of points of a belly.

| Parameter | Type | Description |
|---|---|---|
| `vertices` | `numpy.ndarray` | World-space vertex positions, (N, 3). |
| `path_points` | list of `mathutils.Vector` | Arc-length samples of the muscle path (`tube.sample_path`). |
| `arrangement` | str | One of `ARRANGEMENTS`. |
| `pennation_deg` | float | Angle between fibres and tendon (pennate arrangements). |

**Returns** (tuple of `numpy.ndarray`): `(coords, u)`: (N, 3) `(phase, along, depth)` divided by the path length, and (N,) position along the path (0-1).

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
