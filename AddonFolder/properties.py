"""Scene settings of MyoGeneratorRemix, stored at ``scene.myogen``.

Measured results are not stored here: they go to the muscle records on each
muscle collection (see :mod:`myo_record`).
"""

import bpy

from . import myo_record
from .volume_builder import on_controls_toggled, on_setting_changed, on_shape_changed


def _set_role_visibility(roles, hide):
    """Show/hide every MyoGen object whose role is in ``roles``."""
    for coll in myo_record.iter_muscle_collections():
        for role, obj in myo_record.resolve_objects(coll).items():
            if role in roles:
                try:
                    obj.hide_viewport = hide
                    obj.hide_set(hide)
                except RuntimeError:
                    pass


def update_muscles_visibility(self, context):
    """Update callback of ``show_muscles``: show/hide every muscle belly.

    :arg self: The property group.
    :type self: :class:`MyoGeneratorProperties`
    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    """
    _set_role_visibility({"belly"}, not self.show_muscles)


def update_attachments_visibility(self, context):
    """Update callback of ``show_attachments``: show/hide attachment surfaces and contours.

    :arg self: The property group.
    :type self: :class:`MyoGeneratorProperties`
    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    """
    _set_role_visibility({"origin", "insertion", "origin_contour", "insertion_contour"},
                         not self.show_attachments)


def update_curves_visibility(self, context):
    """Update callback of ``show_curves``: show/hide every path curve.

    :arg self: The property group.
    :type self: :class:`MyoGeneratorProperties`
    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    """
    _set_role_visibility({"path"}, not self.show_curves)


class MyoGeneratorProperties(bpy.types.PropertyGroup):
    """All MyoGeneratorRemix scene settings, stored under ``scene.myogen``."""

    conf_path: bpy.props.StringProperty(
        name="Path", default="", subtype="DIR_PATH", maxlen=1024,
        description="Folder where the CSV file is saved")
    file_name: bpy.props.StringProperty(
        name="File Name", subtype="FILE_NAME",
        description="CSV file name (without extension)")

    origin_object: bpy.props.PointerProperty(type=bpy.types.Object, name="Origin Bone", description="Bone on which the origin area is painted (also the reference size for the scale check)")
    insertion_object: bpy.props.PointerProperty(type=bpy.types.Object, name="Insertion Bone", description="Bone on which the insertion area is painted")
    muscle_name: bpy.props.StringProperty(
        name="Muscle Name", default="Insert muscle name",
        description="Name of the muscle being reconstructed. Use a _left/_right suffix "
                    "for bilateral muscles (e.g. temp_sup_left)")

    muscle_curve_subdivisions: bpy.props.IntProperty(
        name="Curve Subdivisions", default=12, min=4, max=100, update=on_setting_changed,
        description="Number of subdivisions along the muscle curve")
    muscle_contour_resolution: bpy.props.IntProperty(
        name="Contour Resolution", default=16, min=4, max=100, update=on_setting_changed,
        description="Resolution of the contour loops (vertex count)")
    origin_contour_offset: bpy.props.IntProperty(
        name="Origin Offset", default=0, min=0, max=64, update=on_setting_changed,
        description="Shift origin contour vertices for better alignment")
    insertion_contour_offset: bpy.props.IntProperty(
        name="Insertion Offset", default=0, min=0, max=64, update=on_setting_changed,
        description="Shift insertion contour vertices for better alignment")
    origin_reverse_orientation: bpy.props.BoolProperty(
        name="Reverse Origin", default=False, update=on_setting_changed,
        description="Reverse origin contour vertex order")
    insertion_reverse_orientation: bpy.props.BoolProperty(
        name="Reverse Insertion", default=False, update=on_setting_changed,
        description="Reverse insertion contour vertex order")
    contour_matching: bpy.props.EnumProperty(
        name="Contour Matching",
        items=[
            ('AUTO', "Automatic",
             "Resample both contours evenly by arc length and choose the start point and direction of the "
             "insertion contour that best match the origin in the frame of the muscle path: no twist or "
             "hourglass, whatever the vertex order or count. Offsets below are optional fine-tuning"),
            ('INDEX', "By index (legacy)",
             "Join contour points by index, as in earlier versions; use the offsets and reversals to fix "
             "twists by hand"),
        ],
        default='AUTO', update=on_setting_changed,
        description="How points of the origin contour are joined to points of the insertion contour")
    contour_match_info: bpy.props.StringProperty(
        name="Last contour match", default="", options={'SKIP_SAVE'},
        description="Summary of the last loft: shift/reversal chosen and waist index (1 = no hourglass)")
    muscle_connection_mode: bpy.props.EnumProperty(
        name="Connection Mode", update=on_setting_changed,
        description="Choose how the muscle loft connects origin and insertion",
        items=[
            ('FOLLOW_PATH', "Follow Path", "Loft along the curve path (default)"),
            ('DIRECT_CONNECTION', "Direct Connection",
             "Connect origin and insertion directly, ignoring curve curvature"),
        ],
        default='FOLLOW_PATH')
    # --- Legacy loft (preview.build_loft): not used by the panel any more ---
    anchor_falloff: bpy.props.FloatProperty(
        name="Anchored length", default=0.15, min=0.0, max=0.5, subtype='FACTOR',
        update=on_setting_changed,
        description="Along the path: fraction of the length, from each attachment, over which the belly "
                    "keeps the attachment's outline before following the path and the belly settings")
    muscle_shape: bpy.props.EnumProperty(
        name="Muscle type",
        items=[('FUSIFORM', "Fusiform", "A belly along the path, thick in the middle (e.g. digastric, "
                                         "brachioradialis)"),
               ('PARALLEL', "Parallel / strap", "A belly along the path of even width, somewhat flattened "
                                                  "(e.g. pterygoids)"),
               ('FAN', "Fan (convergent)", "Fibres from the whole origin converging on the insertion along "
                                           "the path (e.g. temporalis, pectoralis major)")],
        default='FUSIFORM', update=on_shape_changed,
        description="How the belly is built along the path. Fusiform and Parallel: a belly whose section "
                    "the rings set. Fan: fibres spread over the origin; the rings set the fan's width (X) and "
                    "thickness (Y). Switching type keeps the path and the rings")
    belly_bulge: bpy.props.FloatProperty(
        name="Belly", default=0.35, min=-0.7, max=1.5, soft_min=-0.6, soft_max=1.0,
        update=on_setting_changed,
        description="Along the path: how much thicker (positive) or thinner (negative) the middle is than "
                    "a straight blend of the two attachments. 0.3 = 30 % larger at its widest point")
    bulge_position: bpy.props.FloatProperty(
        name="Belly position", default=0.5, min=0.05, max=0.95, subtype='FACTOR',
        update=on_setting_changed,
        description="Along the path: where the belly is widest, 0 = at the origin, 1 = at the insertion")
    flatness: bpy.props.FloatProperty(
        name="Flatness", default=0.75, min=0.1, max=1.0, subtype='FACTOR',
        update=on_setting_changed,
        description="Along the path: thickness / width of the cross-section (1 = round, 0.2 = flat). The "
                    "flat side turns with the curve's Tilt (Ctrl+T in Edit Mode)")
    use_controls: bpy.props.BoolProperty(
        name="Shape with rings", default=False, update=on_controls_toggled,
        description="Put rings on the path to set the size and turn of the belly where you want: they slide "
                    "along the path. Off: the muscle type's default profile. The rings are kept when off and "
                    "removed by Generate Final Mesh")
    ring_count: bpy.props.IntProperty(
        name="Rings", default=3, min=2, max=12,
        description="Number of rings created along the path (when they are created or reset); the first and "
                    "last stay at the attachments")
    attachment_thickness_mm: bpy.props.FloatProperty(
        name="Min. thickness (mm)", default=0.0, min=0.0, soft_max=20.0, precision=2,
        update=on_setting_changed,
        description="Least thickness of muscle over each attachment surface, so the whole attachment is "
                    "covered. 0 = automatic (3 voxels)")
    surface_smoothing_mm: bpy.props.FloatProperty(
        name="Smoothing (mm)", default=1.5, min=0.0, soft_max=6.0, precision=1,
        update=on_setting_changed,
        description="Rounds off the outer surface over this distance, joining the belly and the attachments "
                    "smoothly (the face on the bone is never smoothed)")
    voxel_size_mm: bpy.props.FloatProperty(
        name="Detail (mm)", default=0.0, min=0.0, soft_max=5.0, precision=2,
        update=on_setting_changed,
        description="Size of the voxels the belly is built from: smaller = finer and slower. The preview "
                    "uses 1.8 x this. 0 = automatic (about 1/110 of the muscle and at most 1/6 of the thinnest "
                    "section)")
    bone_clearance_mm: bpy.props.FloatProperty(
        name="Bone gap (mm)", default=0.1, min=0.0, soft_max=2.0, precision=2,
        update=on_setting_changed,
        description="Gap kept between the muscle surface and the bones")
    preview_live: bpy.props.BoolProperty(
        name="Live preview", default=False, options={'SKIP_SAVE'},
        description="True while the preview rebuilds itself when a setting, the path or an attachment changes")
    preview_status: bpy.props.StringProperty(
        name="Preview status", default="", options={'SKIP_SAVE'},
        description="Size, resolution and build time of the last preview, and any warning")
    show_fine_tune: bpy.props.BoolProperty(
        name="Show fine-tune", default=False,
        description="Show the optional contour offsets and reversals (Blender < 4.1 only; newer versions "
                    "use a collapsible section)")

    # --- Physiological parameters (Herbst et al. 2022 defaults) ---
    specific_tension: bpy.props.FloatProperty(
        name="Specific Tension (N/cm²)", default=myo_record.DEFAULT_SPECIFIC_TENSION_N_CM2,
        min=0.0, max=100.0, precision=2, step=10,
        description="Maximum isometric muscle stress used for F = PCSA x tension. "
                    "30 N/cm² (0.3 N/mm²) is the usual value; 25 and 37 N/cm² are also used")
    density_g_cm3: bpy.props.FloatProperty(
        name="Muscle Density (g/cm³)", default=myo_record.DEFAULT_DENSITY_G_CM3,
        min=0.0, precision=4, step=0.01,
        description="Density used to compute mass from volume")
    fiber_length_ratio: bpy.props.FloatProperty(
        name="Fibre/Muscle Length Ratio", default=myo_record.DEFAULT_FIBER_LENGTH_RATIO,
        min=0.05, max=1.0, precision=2, step=1,
        description="Fibre length as a fraction of the muscle path length. 1.0 reproduces "
                    "Herbst et al. (2022); 0.7-0.9 is reported for masticatory muscles")
    fiber_length_source: bpy.props.EnumProperty(
        name="Fibre length from",
        items=[('PATH', "Path (MyoGenerator)",
                "Fibre length = length of the muscle path x ratio, as in the original MyoGenerator"),
               ('BELLY_FIBRES', "Belly fibres",
                "Fibre length = mean length of fibres traced through the finished (sculpted) belly from "
                "the origin to the insertion (Laplacian field, Choi & Blemker 2013) x ratio")],
        default='PATH',
        description="Where the fibre length used for the PCSA comes from")
    pcsa_model: bpy.props.EnumProperty(
        name="PCSA",
        items=[('MEAN', "Volume / mean length", "PCSA = V cos(pennation) / mean fibre length"),
               ('WEIGHTED', "Sum over fibres",
                "PCSA = cos(pennation) x sum of (volume share / length) of every fibre: short fibres "
                "count more, as in a fan-shaped muscle")],
        default='MEAN',
        description="How the belly fibres give the PCSA")
    belly_fibre_count: bpy.props.IntProperty(
        name="Fibres", default=150, min=20, max=1000,
        description="Number of belly fibres, spread evenly over the origin attachment")
    pennation_deg: bpy.props.FloatProperty(
        name="Pennation Angle (°)", default=myo_record.DEFAULT_PENNATION_DEG,
        min=0.0, max=60.0, precision=1,
        description="Fibre pennation angle; PCSA is multiplied by cos(angle). 0 = parallel fibres")

    # --- Advanced panel read-outs ---
    advanced_selected_volume: bpy.props.FloatProperty(
        name="Selected Volume", default=0.0, precision=6, options={'SKIP_SAVE'},
        description="Last computed total volume of the selected objects (m³)")
    advanced_selected_mass: bpy.props.FloatProperty(
        name="Selected Mass", default=0.0, precision=6, options={'SKIP_SAVE'},
        description="Last computed total mass of the selected objects (kg)")
    advanced_selected_pcsa: bpy.props.StringProperty(
        name="Selected PCSA", default="", maxlen=4096, options={'SKIP_SAVE'},
        description="Read-out of the summed PCSA of the selected objects")

    show_muscles: bpy.props.BoolProperty(
        name="Show Muscles", default=True, update=update_muscles_visibility,
        description="Show/hide the muscle bellies")
    show_attachments: bpy.props.BoolProperty(
        name="Show Attachments", default=True, update=update_attachments_visibility,
        description="Show/hide origin and insertion surfaces and their contours")
    show_curves: bpy.props.BoolProperty(
        name="Show Curves", default=True, update=update_curves_visibility,
        description="Show/hide the muscle path curves")
    mirror_axis: bpy.props.EnumProperty(
        name="Mirror Axis",
        description="World axis across which Mirror Duplicate reflects the selection",
        items=[('X', 'X', 'Mirror across X'), ('Y', 'Y', 'Mirror across Y'), ('Z', 'Z', 'Mirror across Z')],
        default='X')

    # Scene-level QA (JSON list of [level, message]); written by the check operators.
    scene_qa: bpy.props.StringProperty(default="[]", description="JSON list of [level, message] from the last scene scale/parameter check")
    show_qa_details: bpy.props.BoolProperty(name="Show details", default=True, description="List every finding under each muscle in the QA box")
