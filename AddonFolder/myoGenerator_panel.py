"""The MyoGeneratorRemix sidebar panel (View3D > Sidebar > MyoGeneratorRemix).

Drawing only. Sections: units/scale status, data location, muscle ID,
origin and insertion areas, path and loft, finish, parameters (specific
tension, density, fibre ratio, pennation) with Check / Calculate & Export,
the per-muscle QA box, and the experimental tools.
"""
import json

import bpy

from . import myo_record


def _format_quantity(value, unit):
    if value == 0:
        return f"0 {unit}"
    if abs(value) < 1.0:
        return f"{value:.4f} {unit}"
    if abs(value) < 1000.0:
        return f"{value:.2f} {unit}"
    return f"{value:,.0f} {unit}"


def _draw_findings(layout, findings, max_lines=None):
    for level, message in findings[:max_lines]:
        row = layout.row()
        row.alert = level == myo_record.QA_ERROR
        row.label(text=message, icon=myo_record.LEVEL_ICONS.get(level, 'INFO'))


def draw_units_box(layout, context):
    """Draw the scene scale (1 BU = ... mm), the result of the last scale check and
    the "Set" unit-scale menu.

    :arg layout: Layout to draw into.
    :type layout: :class:`bpy.types.UILayout`
    :arg context: Draw context.
    :type context: :class:`bpy.types.Context`
    """
    scene = context.scene
    props = scene.myogen
    box = layout.box()
    mpu = myo_record.metres_per_unit(scene)
    header = box.row()
    header.label(text=f"Units: 1 BU = {mpu * 1000:g} mm", icon='DRIVER_DISTANCE')
    header.operator_menu_enum("myogen.set_unit_scale", "unit", text="Set", icon='PREFERENCES')
    try:
        findings = json.loads(props.scene_qa or "[]")
    except ValueError:
        findings = []
    if findings:
        _draw_findings(box, [f for f in findings if f[0] != myo_record.QA_OK] or findings)
    else:
        box.label(text="Run 'Check Muscles' to verify the scale", icon='INFO')


def draw_qa_box(layout, context):
    """Draw one line per muscle record with its PCSA and worst finding (details on demand).

    :arg layout: Layout to draw into.
    :type layout: :class:`bpy.types.UILayout`
    :arg context: Draw context.
    :type context: :class:`bpy.types.Context`
    """
    props = context.scene.myogen
    collections = myo_record.iter_muscle_collections()
    if not collections:
        return
    box = layout.box()
    row = box.row()
    row.label(text="Muscle QA", icon='VIEWZOOM')
    row.prop(props, "show_qa_details", text="", icon='TRIA_DOWN' if props.show_qa_details else 'TRIA_RIGHT',
             emboss=False)
    row.operator("myogen.check_muscles", text="", icon='FILE_REFRESH')
    for coll in collections:
        rec = myo_record.read_record(coll)
        findings = rec["qa"]
        level = myo_record.worst_level(findings) if rec.get("myo_updated") else None
        line = box.row()
        line.alert = level == myo_record.QA_ERROR
        if level is None:
            line.label(text=f"{coll.name}: not measured yet", icon='QUESTION')
            continue
        pcsa = f"{rec['myo_pcsa_m2'] * 1e4:.2f} cm²" if rec["has_pcsa"] else "no PCSA"
        line.label(text=f"{coll.name}: {pcsa}", icon=myo_record.LEVEL_ICONS[level])
        if props.show_qa_details:
            col = box.column(align=True)
            col.scale_y = 0.8
            for lvl, msg in findings:
                sub = col.row()
                sub.alert = lvl == myo_record.QA_ERROR
                sub.label(text="    " + msg, icon='BLANK1')


def _draw_fine_tune(layout, props):
    """Optional contour offsets/reversals, in a section closed by default."""
    title = "Fine-tune (optional)" if props.contour_matching == 'AUTO' else "Alignment"
    if hasattr(layout, "panel"):                       # Blender 4.1+
        header, body = layout.panel("myogen_fine_tune", default_closed=True)
        header.label(text=title)
    else:
        row = layout.row()
        row.prop(props, "show_fine_tune", text=title,
                 icon='TRIA_DOWN' if props.show_fine_tune else 'TRIA_RIGHT', emboss=False)
        body = layout.column() if props.show_fine_tune else None
    if body is None:
        return
    row = body.row(align=True)
    row.prop(props, "origin_contour_offset", text="Origin Offset")
    row.prop(props, "insertion_contour_offset", text="Insertion Offset")
    row = body.row(align=True)
    row.prop(props, "origin_reverse_orientation", text="Reverse Origin")
    row.prop(props, "insertion_reverse_orientation", text="Reverse Insertion")


def _hint(layout, text, icon='INFO'):
    row = layout.row()
    row.scale_y = 0.75
    row.label(text=text, icon=icon)


def _section(layout, idname, title, default_closed=True):
    """Collapsible sub-section (Blender 4.1+), or a plain column."""
    if hasattr(layout, "panel"):
        header, body = layout.panel(idname, default_closed=default_closed)
        header.label(text=title)
        return body
    layout.label(text=title)
    return layout.column()


def _draw_path_and_rings(col, context, props):
    col.label(text="Path")
    row = col.row(align=True)
    row.operator("myogen.edit_path", icon='EDITMODE_HLT')
    row.operator("myogen.reset_path", text="", icon='FILE_REFRESH')
    col.prop(props, "use_controls")
    if not props.use_controls:
        return
    row = col.row(align=True)
    row.operator("myogen.select_rings", icon='MESH_CIRCLE')
    row.operator("myogen.reset_rings", text="", icon='FILE_REFRESH')
    col.prop(props, "ring_count")
    _hint(col, "G slides a ring along the path, S sizes it, R turns it")
    if props.muscle_shape == 'FAN':
        _hint(col, "Fan: ring X = width of the fan, Y = thickness")


def draw_muscle_creation(layout, context):
    """Preview first, then the muscle type, the controls and the settings, then the final mesh.

    The preview is the belly as it will be generated (draft resolution); its
    ring controls deform it in real time.

    :arg layout: Layout to draw into.
    :type layout: :class:`bpy.types.UILayout`
    :arg context: Draw context.
    :type context: :class:`bpy.types.Context`
    """
    props = context.scene.myogen
    box = layout.box()
    box.label(text="Muscle Creation", icon='CURVE_BEZCURVE')

    row = box.row(align=True)
    row.scale_y = 1.3
    if props.preview_live:
        row.operator("myogen.muscle_preview_stop", text="Stop Preview", icon='PAUSE')
    else:
        row.operator("myogen.muscle_preview_update", text="Start Preview", icon='PLAY')
    if props.preview_status:
        _hint(box, props.preview_status, icon='ERROR' if "fail" in props.preview_status
              or "pieces" in props.preview_status else 'INFO')

    col = box.column()
    col.prop(props, "muscle_shape", text="Type")
    _draw_path_and_rings(col, context, props)
    more = _section(col, "myogen_more", "More settings")
    if more is not None:
        more.prop(props, "attachment_thickness_mm")
        more.prop(props, "surface_smoothing_mm")
        more.prop(props, "voxel_size_mm")
        more.prop(props, "bone_clearance_mm")

    row = box.row()
    row.scale_y = 1.2
    row.operator("myogen.muscle_mesh_generation", text="Generate Final Mesh", icon='MESH_CUBE')


class MYOGENERATOR_PT_panel(bpy.types.Panel):
    bl_idname = "MYOGENERATOR_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "MyoGeneratorRemix"
    bl_category = "MyoGeneratorRemix"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.myogen

        draw_units_box(layout, context)

        box = layout.box()
        box.label(text="Data Storage Location")
        box.prop(props, "conf_path", text="Folder path")
        box.prop(props, "file_name", text="File name", icon='GREASEPENCIL')

        box = layout.box()
        box.label(text="Muscle ID")
        row = box.row()
        row.prop(props, "muscle_name", text="Muscle Name", icon='GREASEPENCIL')
        row.enabled = props.file_name != ""
        row = box.row()
        row.operator('myogen.submit_muscle', text="Submit Muscle")
        row.enabled = props.muscle_name != "Insert muscle name"

        box = layout.box()
        box.label(text="Origin Creation")
        box.prop(props, "origin_object", text="Origin's Bone")
        row = box.row()
        row.enabled = props.origin_object is not None
        row.operator("myogen.select_origin", text="Start Origin Selection")
        row.operator('myogen.submit_origin', text="Submit Origin")

        box = layout.box()
        box.label(text="Insertion Creation")
        box.prop(props, "insertion_object", text="Insertion's Bone")
        row = box.row()
        row.enabled = props.insertion_object is not None
        row.operator("myogen.select_insertion", text="Start Insertion Selection")
        row.operator('myogen.submit_insertion', text="Submit Insertion")

        draw_muscle_creation(layout, context)

        box = layout.box()
        box.label(text="Finish")
        box.operator("myogen.next_muscle", text="Next Muscle")

        box = layout.box()
        box.label(text="Muscle parameters", icon='FORCE_FORCE')
        col = box.column(align=True)
        col.prop(props, "specific_tension")
        col.prop(props, "density_g_cm3")
        col.prop(props, "fiber_length_ratio")
        col.prop(props, "pennation_deg")
        info = box.column(align=True)
        info.scale_y = 0.75
        info.label(text="PCSA = V·cos(pennation) / (path length × ratio).", icon='INFO')
        info.label(text="Ratio 1 and 0° reproduce Herbst et al. (2022).", icon='BLANK1')
        row = box.row(align=True)
        row.operator("myogen.check_muscles", text="Check Muscles", icon='VIEWZOOM')
        row.operator("myogen.calculate_muscle_parameters", text="Calculate & Export CSV", icon='EXPORT')

        draw_qa_box(layout, context)

        addon = context.preferences.addons.get(__package__)
        if not (addon and addon.preferences.show_advanced):
            return

        adv_box = layout.box()
        adv_box.label(text="Advanced (experimental)")
        adv_box.label(text=f"Selected Total Volume: "
                           f"{_format_quantity(props.advanced_selected_volume * 1e6, 'cm³')}")
        adv_box.label(text=f"Estimated Total Mass: {_format_quantity(props.advanced_selected_mass * 1e3, 'g')}")
        adv_box.label(text=props.advanced_selected_pcsa or "Total PCSA: NA")
        adv_box.operator("myogen.estimate_selected_volumes", text="Estimate Selected Volumes")

        adv_box.label(text="Object Visibility:", icon='HIDE_OFF')
        row = adv_box.row(align=True)
        row.prop(props, "show_muscles", text="Muscles", icon='MESH_CUBE')
        row.prop(props, "show_attachments", text="Attachments", icon='CONSTRAINT_BONE')
        row.prop(props, "show_curves", text="Curves", icon='CURVE_BEZCURVE')

        row = adv_box.row(align=True)
        row.prop(props, "mirror_axis", expand=True)
        op = row.operator("myogen.mirror_duplicate", text="Mirror Duplicate")
        op.axis = props.mirror_axis
