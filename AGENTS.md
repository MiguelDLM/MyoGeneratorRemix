# AGENTS.md — MyoGeneratorRemix

Blender extension (Blender ≥ 4.2, tested on 5.1) to reconstruct muscles as
volumes and measure them (volume, mass, lengths, areas, PCSA, force). The
extension package is `AddonFolder/`. Read `devdocs/ARCHITECTURE.md` first;
the data contract is `devdocs/MUSCLE_RECORD.md`; the API reference is
generated in `devdocs/reference/`.

## Map

| need to change… | look in |
|---|---|
| a measurement or the PCSA model | `AddonFolder/muscle_metrics.py`, `AddonFolder/myo_record.py` |
| plausibility checks / thresholds | `AddonFolder/myo_record.py` (`check_*`, constants) |
| the record keys | `AddonFolder/myo_record.py` + `devdocs/MUSCLE_RECORD.md` |
| attachment / mirror / export operators | `AddonFolder/core_operators.py` |
| path, final mesh operators | `AddonFolder/improved_muscle_workflow.py`, `AddonFolder/curve_utilities.py` |
| attachment/bone geometry, default course, path writing (legacy loft) | `AddonFolder/preview.py` |
| path sampling, tube along the path, type profiles | `AddonFolder/tube.py` |
| section rings on the path (slide, size, turn) | `AddonFolder/rings.py` |
| solid belly (tube or fibres, bone subtraction, meshing), live preview, final mesh | `AddonFolder/volume_builder.py` |
| fan-shaped muscles (fibres from the origin area to the insertion) | `AddonFolder/fan.py` |
| muscle texture by fibre arrangement | `AddonFolder/fibre_texture.py`, `AddonFolder/muscle_texture.py` |
| how loft contours are joined | `AddonFolder/contour_matching.py` (pure, unit-tested) |
| volume of defective bellies | `myo_record.mesh_defects`, `robust_volume`, `enclosed_volume`, `winding_volume` |
| settings | `AddonFolder/properties.py` (`scene.myogen`) |
| UI | `AddonFolder/myoGenerator_panel.py` |

## Invariants (do not break)

1. `myo_record.py` is the contract other tools (MUFIS) read from `.blend`
   files. It must not import anything from the add-on, its pure functions must
   work without `bpy`, and changes must follow "Changing the contract" in
   `devdocs/MUSCLE_RECORD.md`. After editing it, run
   `python tools/sync_shared.py --update` in the MUFIS checkout.
2. This extension never imports or references MUFIS.
3. Find objects by `myo_role` (falling back to the `<M>_origin`… names via
   `myo_record.resolve_objects`); never fail because of collections or
   objects that are not MyoGen muscles.
4. SI units in records; CSV columns carry their unit; state units in docstrings.
5. Operator idnames `myogen.*`; settings only in `scene.myogen`.
6. Public functions, classes, operators and properties need Blender-style
   docstrings / descriptions; `tools/gen_api_docs.py --check` enforces it.
   `tools/gen_api_docs.py` itself is owned by MUFIS (copied here).

## Before finishing a change

```bash
python -m unittest discover -s tests -p "test_*.py"
blender -b --factory-startup --python tests/blender/run.py
python tools/gen_api_docs.py --check && python tools/gen_api_docs.py
```

Never run the add-on against users' specimen files in place: copy them to a
temporary folder first.
