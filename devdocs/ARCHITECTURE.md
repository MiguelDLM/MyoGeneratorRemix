# MyoGeneratorRemix — architecture and developer guide

MyoGeneratorRemix reconstructs jaw muscles as volumes in Blender (a fork of
MyoGenerator, Herbst et al. 2022) and measures them: volume, mass, path and
fibre length, attachment areas, PCSA and force. Results are exported to CSV
and stored in the `.blend` as **muscle records** (see
[MUSCLE_RECORD.md](MUSCLE_RECORD.md)), which other tools such as MUFIS read
without depending on this extension.

The API reference generated from the code is in [`reference/`](reference/index.md).

---

## 1. Repository layout

```
MyoGeneratorRemix/
├── AddonFolder/                  the extension package
│   ├── __init__.py                 register()/unregister(), preferences
│   ├── properties.py               scene settings (scene.myogen)
│   ├── core_operators.py           muscle ID, attachments, mirror, checks, export operators
│   ├── improved_muscle_workflow.py preview, path and final mesh operators (thin)
│   ├── preview.py                  attachment/bone geometry, default course, path writing (+ legacy loft)
│   ├── tube.py                     path sampling (arc length) and the tube swept along the path
│   ├── rings.py                    section rings sliding on the path (size, turn)
│   ├── volume_builder.py           solid belly: (tube or fan fibres ∪ attachment layers) − bones
│   ├── fan.py                      fibres of fan-shaped muscles (origin area → insertion)
│   ├── curve_utilities.py          path validation, Bezier sampling, twist-free frames
│   ├── contour_matching.py         origin/insertion contour correspondence for the loft (pure)
│   ├── muscle_utilities.py         selection helpers, contour alignment
│   ├── muscle_texture.py           procedural muscle materials (visual)
│   ├── fibre_texture.py            fibre coordinates per arrangement for the texture (visual)
│   ├── muscle_metrics.py           measurements, plausibility checks, CSV
│   ├── myo_record.py               the muscle-record contract (shared with MUFIS)
│   └── myoGenerator_panel.py       sidebar UI (drawing only)
├── tests/                        unit tests (no Blender) and tests/blender (headless)
├── tools/gen_api_docs.py         API reference generator (owned by MUFIS, copied here)
└── devdocs/                      this guide, the contract and the generated reference
```

Dependency rules:

* `myo_record.py` imports nothing from the add-on and works without `bpy` for
  its pure functions (formulas, side parsing, checks). It is the only module
  other tools may copy.
* `muscle_metrics.py` is the only place that measures muscles; operators call it.
* Operator idnames are `myogen.*`; settings live in `scene.myogen`.
* This extension never imports or references MUFIS.

---

## 2. Reconstruction workflow

```
Submit Muscle            myogen.submit_muscle            muscles/<M> collection (+ partial record)
Origin's Bone            scene.myogen.origin_object
Start Origin Selection   myogen.select_origin            Edit Mode, face select, lasso
Submit Origin            myogen.submit_origin            <M>_origin (faces) + <M>_origin_contour (boundary)
(same for the insertion) myogen.select_insertion / submit_insertion
Start / Stop Preview     myogen.muscle_preview_update    <M>_preview (solid, draft) + <M>_tube (wire, instant);
                         myogen.muscle_preview_stop      the default path <M>_curve is created if missing
Muscle type              scene.myogen.muscle_shape       Fusiform / Parallel (tube) · Fan (fibres)
Edit / Reset Path        myogen.edit_path, reset_path    the course of the belly (user's curve)
Shape with rings         scene.myogen.use_controls       rings on the path: G slides, S sizes, R turns
Select / Reset Rings     myogen.select_rings, reset_rings
Generate Final Mesh      myogen.muscle_mesh_generation   <M>_muscle at full resolution, anchored vertices
                                                         protected; preview, tube and rings removed,
                                                         path kept
Next Muscle              myogen.next_muscle
Check Muscles            myogen.check_muscles            measure + QA + write records
Calculate & Export CSV   myogen.calculate_muscle_parameters   same + <folder>/<file>.csv
```

### Path, rings, preview, final mesh

1. **Path** `<M>_curve`: the course of the belly, edited by the user
   (*Edit Path*); the default one (`preview.default_path_points`) is created
   when missing and never rewritten automatically. It is also the path used
   for path length → fibre length → PCSA.
2. **Sections**: with *Shape with rings* (`use_controls`, off by default)
   rings `<M>_ring_NN` (`rings.py`) change the section at their place on
   the path **relative to the muscle's natural section**
   (`volume_builder.natural_section`: the type's profile, or the natural
   width, thickness and orientation of a fan): each ring stores a scale
   (X width, Y thickness) and a turn (`myo_ring_scale`, `myo_ring_turn`);
   an untouched ring changes nothing, and switching type keeps the change
   without inflating the section. Rings are drawn at the actual section
   size; a user edit is detected against what was last shown
   (`myo_ring_shown`) and absorbed once; the end rings stay at the path ends and
   the others slide: a ring acts at the path point nearest to it
   (`rings.ring_sections`, arc-length fraction `u`) and is snapped back onto
   the path, perpendicular to it, after each rebuild (`rings.align_rings`).
   Without rings, the muscle type's profile (`tube.default_profile`).
3. **Tube** (`tube.path_tube`): the path sampled by arc length
   (`tube.sample_path`), parallel-transported frames, sections blended
   smoothly between their `u`.
   **Fan** (`fan.py`): instead of a tube, the union of fibres, one from
   every part of the origin attachment (`fan.sample_surface`, lifted off
   the bone by the half-thickness) to the matching part of the insertion
   (footprints matched in one fixed frame, scaled to each other's extent);
   each fibre runs straight from start to end plus the path's bend (its
   offset from its chord), so the fibres curve with the path, converge and
   never twist around each other. Rings set the fan's width (X, along
   its widest direction), half-thickness (Y) and turn; without rings the
   natural width and `fan.default_thickness` (0.08 × path length, +30 %
   in the middle). Fibres are rasterised as spheres along their courses
   (`fan.occupancy`). The origin attachment should be the whole area the
   muscle arises from (e.g. the temporal fossa, the sternum and clavicle).
4. **Preview** (`volume_builder.start_live`): a wire `<M>_tube` refreshed
   `TUBE_DELAY` s after a change (instant feedback while dragging) and the
   solid `<M>_preview` at draft resolution `LIVE_DELAY` s after the last
   change. Changes are detected by a `depsgraph_update_post` handler that
   compares a signature of the path, rings and attachments
   (`_state`) with the one left by the last rebuild, so the rebuild's own
   edits (ring snapping) do not loop; settings call
   `volume_builder.on_setting_changed`.
5. **Final mesh** (`volume_builder.generate_final`): the same at full
   resolution; the anchored vertices are protected for sculpting and the
   construction helpers (preview, wire tube, rings) are deleted; the path
   stays (measurements).

The automatic voxel is at most the thinnest section radius / 6
(`VOXELS_PER_RADIUS`), so long thin muscles keep their detail.

The former loft (`preview.build_loft`, contour matching, belly / flatness /
loft settings) is no longer used by the panel; it is kept, with its tests,
until the new workflow is validated.

### Default path (`preview.default_path_points`)

The ends of the path are **not** the attachment centroids: the centroid of a
concave or wrapping attachment (a fossa, the temporalis insertion around the
coronoid process) lies inside the bone. `preview.attachment_anchor` takes the
point of the surface nearest to the centroid moved towards the other
attachment, with the outward normal there (`preview.outward_sign`: face
normals tested against the bone by ray parity). The end is lifted by
`PATH_LIFT` × the attachment size along that normal, and the second and
fourth points bulge along the normals (`PATH_BEND`). All radii start at 1:
the muscle type gives the belly.

### Legacy loft (`preview.build_loft`, not used by the panel)

* Anchoring: the first and last sections are exactly the matched contour
  points, and each end is closed by a cap draped over the attachment surface
  (concentric rings projected onto it). The path position/radius/shape and
  smoothing only act away from the ends (weights rising over
  `scene.myogen.anchor_falloff` of the length).
* The loft may cross itself or enter the bone when an attachment wraps a
  process: the solid belly removes both (winding-number occupancy, bone
  subtraction). A warning is shown only when the matching is twisted.

### Solid final belly (`volume_builder.py`)

The preview and `Generate Final Mesh` build the belly on a voxel grid
(`voxel_size_mm`; automatic = 1/110 of the muscle, at most the thinnest
section radius / 6, or the fibre radius / 3 for fans; never more than
`MAX_CELLS` cells):

| step | |
|---|---|
| body | the tube (winding number: self-overlaps are a union) or the fan fibres, Gaussian-smoothed by `surface_smoothing_mm` **before** the bones are cut (so the face on the bone stays exact) |
| attachments | ∪ a layer over each attachment, up to `attachment_thickness_mm` outwards (`attachment_layer`: voxels within that distance of the attachment and inside a 60° cone of its outward normal, so it never folds; automatic 3 voxels) |
| bones | − the origin and insertion bones (ray parity, scanlines along +Z) |

The field is meshed by surface nets and rebuilt by Blender's voxel remesher
(`manifold_remesh`, always closed and manifold); vertices within one voxel of
an attachment are snapped onto it and anchored (`myo_deform` 0 →
`myo_anchored` group and sculpt mask); pieces that reach no attachment are
dropped (`report["pieces"] > 1` = parts that do not join); the
free surface is smoothed (`SMOOTH_PASSES`) and pushed out of the bones by
`bone_clearance_mm`. Vertices lying on the bone outside the attachments are
contact, not penetration (`preview.DIAGNOSIS_CONTACT_MM`).

Reference (Canis temporalis superficialis, compared with the hand-sculpted
muscle of the same specimen, aligned on the cranium; origin = the bone under
the sculpt): the former loft had a mean dihedral angle of 17° (sculpt 3.4°)
and 14 cm³ (sculpt 59.6 cm³); Fan with the default thickness gives
48.9 cm³, 3.2°, one closed piece, 64 % of the sculpt within 3 mm, in about
1 s (preview) / 3.3 s (final).
Fusiform on the same attachments: 27 cm³, two pieces, 59 %.

### Fibre texture (`fibre_texture.py`, visual only)

Each finished belly has a fibre arrangement (`Object.myogen_fibres`:
Parallel, Fusiform, Convergent, Pennate, Bipennate, Multipennate), a
pennation angle for the pennate ones (`Object.myogen_pennation`), a bundle
density (`Object.myogen_fibre_bundles`, bundles across the width), a relief
factor (`Object.myogen_relief`) and the tendon colour, all set in the
muscle list (QA box). The tendon colour follows the **distance to each
attachment surface** (`fibre_texture.attachment_distance`), so it runs along
the whole outline of an attachment of any shape (a line, a "]", a patch):
solid within `Object.myogen_tendon_origin` / `_insertion` of it, then a fade
of width `Object.myogen_tendon_fade` (all fractions of the muscle length;
extent and softness are independent).

`fibre_texture.fibre_coordinates` measures every vertex along the muscle,
across the section's width and through its thickness (width direction per
section, kept for round sections and smoothed along the path). The position
along the muscle is `d_origin / (d_origin + d_insertion)` from the distances
to the two attachment surfaces (`attachment_position`): smooth everywhere
(the nearest point of a curved path jumps across broad muscles, which drew a
line across the texture). For Convergent, the phase is the position across
the fan model's fibre bundle at that place (`fan_fibre_field`: centre,
widest direction and half-width of the fibres of `fan.fibres`), so the
texture's fibres spread over the whole origin and converge on the
insertion.
Longitudinal arrangements use the angle around the section's axis (times a
smoothed local radius for Parallel, a constant one for Fusiform/Convergent,
so fibres converge as the section narrows); pennate ones use the position
across the width from one side (Pennate), from the centre (Bipennate) or
from several internal tendons (Multipennate), turned by the pennation angle.
The coordinates (X along the fibres, Y across, Z through) share one unit,
so the bundles keep the material's elongation whatever the muscle's
proportions. Point attributes: `myo_fibre` (vector), `myo_fibre_u` (0–1
along the path), `myo_tendon` (tendon colour weight) and `myo_bump` (relief
depth, a fraction of the bundle size).

`muscle_texture.create_fibre_material` is the original muscle material (Ned
Poreyra's node set-up) with its coordinates, tendon colour and bump distance
taken from those attributes instead of the object's generated coordinates
(versioned: older fibre materials are rebuilt). Generate Final Mesh picks
the type's default (Fusiform → Fusiform, Parallel → Parallel, Fan →
Convergent).

### Contour correspondence (`contour_matching.py`)

With `Contour Matching = Automatic` (default):

1. both contours are resampled to the same number of points, evenly spaced
   by arc length (independent of vertex count, order and density);
2. their circulation is made consistent: their vector areas (own normals)
   must point to the same side, otherwise elongated contours fold the loft
   into a figure-eight (this also works for sheet-like muscles such as the
   temporalis, whose contours are edge-on to the origin-insertion axis);
3. the start point of the insertion contour minimises the sum of squared
   distances between centred corresponding points, which maximises the size
   of the loft's mid-way section.

The panel shows the result: shift, reversal, waist index (mid-section RMS
size / ends; < 0.8 = hourglass) and mid-section area ratio (< 0.5 = twisted
or folded). The offsets/reversal fields remain as optional fine-tuning.
`By index (legacy)` restores the former index-based joining. On the
reconstructed specimens the automatic matching removed the twist from the 8
of 15 muscles that index matching twisted (Magericyon, Vulpes).

Bilateral muscles: reconstruct `<M>_left`, select its objects and use
*Mirror Duplicate*; `<M>_right` is created with mirrored objects and the
roles copied.

---

## 3. Measurements (`muscle_metrics.compute_muscles`)

| quantity | definition |
|---|---|
| units | 1 BU = `scene.unit_settings.scale_length` m; everything stored in SI |
| volume | `|signed volume|` of the belly (bmesh, world space). If the mesh has self-intersections or non-manifold edges, `myo_record.robust_volume` measures the volume actually enclosed (voxel union at two resolutions, or the generalized winding number when that fails) and uses it when it differs by more than 2 % |
| hole error | relative volume change after filling the belly's holes |
| path length | evaluated Bezier length of `<M>_curve` (sampled, not control points) |
| linear length | straight distance between origin and insertion centroids |
| fibre length | `Fibre length from` = **Path (MyoGenerator)**, the default: `path length × ratio` (ratio 1 = the original MyoGenerator, Herbst et al. 2022); or **Belly fibres**: weighted `mean(L_i) × ratio`, `L_i` the fibres traced through the finished belly (see *Belly fibres* below) |
| PCSA | `volume × cos(pennation) / fibre length` (defaults: parallel fibres, no tendon); with belly fibres, optionally **Sum over fibres**: `cos(pennation) × Σ V_i / (L_i × ratio)`, `V_i` each fibre's share of the volume (`myo_record.pcsa_from_fibres`) |
| force | `PCSA × specific tension` (default 30 N/cm² = 0.3 N/mm²) |
| mass | `volume × density` (default 1.0597 g/cm³) |

CSV columns: `name, side, volume_cm3, volume_raw_cm3, volume_method, mass_g, path_length_cm, fiber_length_cm,
linear_length_cm, origin_area_cm2, insertion_area_cm2, pcsa_cm2, force_N,
origin_centroid_BU, insertion_centroid_BU, density_g_cm3,
specific_tension_N_cm2, fiber_length_ratio, pennation_deg, fiber_length_source,
fiber_count, fiber_length_sd_cm, fiber_length_min_cm, fiber_length_max_cm,
fiber_reached, fiber_detoured, origin_contact, insertion_contact, pcsa_method, qa`.

### Belly fibres

`belly_fibres.belly_fibres` follows Choi & Blemker (2013, PLoS ONE 8:
e77576): the finished belly (closed first by a temporary voxel remesh, so
sculpted meshes with holes or self-overlaps work) is voxelised; Laplace's
equation is solved inside it (conjugate gradients) with `u = 0` on the voxels
touching the origin attachment, `u = 1` on those touching the insertion and
no flux through the rest of its surface; fibres are the streamlines of
`grad u`, each started at the field's front next to its seed point (the
fixed layer has no gradient) and closed onto the other attachment.

**Where a fibre ends is not chosen**: it follows the field. The field's
flux gathers on the parts of an attachment nearest to (and most open to)
the bulk of the belly, like field lines between two electrodes, so fibres
seeded evenly over the origin bunch up on part of the insertion (on the
MUDYS specimens they reached about half of it) and the mean length depends
on the side seeded (×2 on a temporalis). Fibres are therefore seeded
evenly over **both** attachments (origin → insertion, and insertion →
origin reversed), each set with half of the weight: both areas are covered
and the weighted mean length is symmetric.

Fibres longer than `DETOUR_MAX` (2) × the straight distance between their
ends are **detours** (the field following a thin curved sheet round a
bend): they are left out of the lengths and of the volume shares, and shown
in magenta. Each kept fibre gets the belly voxels nearest to it as its
volume share. `origin_contact` / `insertion_contact` measure how much of
each attachment's area the belly touches: no fibre can reach the rest.
Results are cached until the belly or the attachments change. **Show Belly
Fibres** draws them as `<M>_belly_fibres` (+ `_detours`).

The fibres run attachment to attachment, tendon included: they measure the
belly, not fascicles. The ratio still converts them to fascicle length, and
pennate muscles (fascicles between aponeuroses, not modelled) still need the
pennation and a ratio. QA warns when the belly touches < 50 % of an
attachment's area, < 80 % of the fibres arrive, > 10 % detour, or the
longest fibre exceeds 2.5 × the path; when the fibres cannot be traced the
path is used, with a warning.

### Plausibility checks (`myo_record.check_*`)

All checks are ratios, so the same thresholds hold from a shrew to a
tyrannosaur. The reference length is the longest of the origin/insertion
bones or, without them, the extent of all attachment surfaces.

| check | level | threshold (`myo_record`) |
|---|---|---|
| reference length (skull size) | ERROR | outside 3 mm – 6 m (`REF_LENGTH_RANGE_M`), with the Unit Scale that would fix it |
| belly missing / zero volume | ERROR | |
| path missing / zero length | ERROR | |
| belly holes | WARNING / INFO | volume change > 2 % (`HOLE_VOLUME_TOLERANCE`) / smaller |
| self-intersecting / non-manifold belly | WARNING / INFO | enclosed volume differs > 2 % (`OVERLAP_VOLUME_TOLERANCE`) from the signed sum: the enclosed volume is used / minor defects |
| inverted normals | INFO | negative signed volume |
| path / linear length | WARNING | outside 0.9 – 1.8 (`PATH_TO_LINEAR`) |
| fibre length / skull | WARNING | outside 0.03 – 1.2 (`FIBER_TO_REF`) |
| ∛volume / skull | WARNING | outside 0.01 – 0.6 (`CBRT_VOLUME_TO_REF`) |
| left / right volume | WARNING | ratio > 1.5 (`BILATERAL_VOLUME_RATIO`) |
| density, tension, fibre ratio | WARNING | 1.0–1.1 g/cm³, 10–60 N/cm², 0.3–1.0 |

Findings are stored in `myo_qa`, shown in the panel's QA box and exported in
the `qa` CSV column. Scene-level findings go to `scene.myogen.scene_qa`.

---

## 4. Customising

**Add a measurement** — compute it in `muscle_metrics.compute_muscles` (SI
units), add a `myo_*` key to `myo_record.RECORD_KEYS` and to
[MUSCLE_RECORD.md](MUSCLE_RECORD.md), add a column to `CSV_FIELDS`, then sync
the contract into MUFIS (`python tools/sync_shared.py --update` in MUFIS).

**Add a plausibility check** — add a dimensionless threshold constant and a
branch in `myo_record.check_muscle` (or a new `check_*` function called from
`compute_muscles`), and a unit test in `tests/test_myo_record.py`.

**Change the PCSA model** — `myo_record.pcsa_from_volume` and
`pcsa_method_label`; expose new parameters in `properties.py` and record them
as `myo_*` keys so readers know the assumptions.

**Add an operator** — class with `bl_idname = "myogen.<name>"`, a
`bl_description` and described properties; add it to `classes` in
`__init__.py` and a button in `myoGenerator_panel.py`.

---

## 5. Tooling

```bash
python -m unittest discover -s tests -p "test_*.py"        # contract formulas and checks
blender -b --factory-startup --python tests/blender/run.py # synthetic cylinder muscle, mirror, CSV
python tools/gen_api_docs.py --check                       # every public API documented?
python tools/gen_api_docs.py                               # regenerate devdocs/reference
```

Docstrings follow Blender's convention (`:arg:`, `:type:`, `:return:`,
`:rtype:`, `:raises:`); state units for every physical quantity.
