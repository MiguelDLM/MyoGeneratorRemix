"""Muscle measurements, plausibility checks and CSV export.

:func:`compute_muscles` is the single place where MyoGeneratorRemix measures
its muscles: it reads every muscle collection (via :mod:`myo_record`),
computes volume, mass, lengths, areas, PCSA and force in SI units, runs the
plausibility checks and writes the muscle records that other tools (MUFIS)
read. Operators in :mod:`core_operators` only call it and report.
"""

import csv
import json
from datetime import datetime, timezone

import bpy
from mathutils import Vector

from . import myo_record


# --------------------------------------------------------------------------

def scene_scale_findings(context, collections):
    """Scale check of the current scene.

    The reference is the longest bone picked as origin/insertion bone; without
    them, the joint extent of the attachment surfaces (which spans most of the
    skull) is used instead.

    :arg context: Context.
    :type context: :class:`bpy.types.Context`
    :arg collections: Muscle collections (for the attachment extent).
    :type collections: list of :class:`bpy.types.Collection`
    :return: ``(reference length in m or None, findings)``.
    :rtype: tuple
    """
    props = context.scene.myogen
    bones = [o for o in (props.origin_object, props.insertion_object) if o is not None]
    if bones:
        return myo_record.check_scene_scale(context.scene, max(myo_record.max_dimension(o) for o in bones))
    pts = []
    for coll in collections:
        for role in ("origin", "insertion"):
            obj = myo_record.resolve_objects(coll).get(role)
            if obj is not None and obj.type == 'MESH':
                pts.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)
    if not pts:
        return None, [(myo_record.QA_INFO, "No bones or attachments yet: scale not checked")]
    extent = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))
    return myo_record.check_scene_scale(context.scene, extent, what="Extent of the attachment areas")


def compute_muscles(context, write=True):
    """Measure every muscle, run the plausibility checks and write the records.

    Per muscle: volume and mass (belly; the voxel-enclosed volume replaces the
    signed-sum volume when a closed belly overlaps itself by more than
    ``myo_record.OVERLAP_VOLUME_TOLERANCE``), path and straight lengths, fibre length
    and PCSA (:func:`myo_record.pcsa_from_volume` with the scene's ratio and
    pennation), force, attachment areas and centroids, then
    :func:`myo_record.check_muscle` and the left/right comparison.

    :arg context: Context (reads ``scene.myogen``).
    :type context: :class:`bpy.types.Context`
    :arg write: Tag the objects' roles and store the muscle records on the collections.
    :type write: bool
    :return: ``(rows, scene_findings)``; each row holds the record values (SI) plus
       ``collection``, ``origin_centroid``, ``insertion_centroid`` (Blender units)
       and ``qa`` (list of ``(level, message)``). The scene findings are also
       stored in ``scene.myogen.scene_qa``.
    :rtype: tuple
    """
    scene = context.scene
    props = scene.myogen
    mpu = myo_record.metres_per_unit(scene)
    collections = myo_record.iter_muscle_collections()

    ref_m, scene_findings = scene_scale_findings(context, collections)
    scene_findings = scene_findings + myo_record.check_parameters(
        props.density_g_cm3, props.specific_tension, props.fiber_length_ratio)

    rows = []
    for coll in collections:
        objs = myo_record.resolve_objects(coll)
        belly, path = objs.get("belly"), objs.get("path")
        origin, insertion = objs.get("origin"), objs.get("insertion")

        vol_bu, signed_bu, _a, _c, hole_error = myo_record.mesh_stats(belly)
        _v, _s, o_area_bu, o_cent, _cl = myo_record.mesh_stats(origin)
        _v, _s, i_area_bu, i_cent, _cl = myo_record.mesh_stats(insertion)

        volume_m3 = raw_volume_m3 = vol_bu * mpu ** 3
        volume_method = "mesh"
        overlap_qa = []
        if belly is not None:
            crossings, non_manifold, boundary = myo_record.mesh_defects(belly)
            if crossings or non_manifold:
                defects = f"{crossings} crossing face pairs, {non_manifold} non-manifold edges, {boundary} open edges"
                checked, method, error = myo_record.robust_volume(belly, vol_bu)
                if method == "mesh":
                    overlap_qa.append((myo_record.QA_INFO, f"Belly has minor defects ({defects}); enclosed volume "
                                                           "checked, difference < 2%"))
                else:
                    volume_m3 = checked * mpu ** 3
                    volume_method = f"{method} (defective mesh)"
                    uncertainty = f" +-{error * 100:.0f}%" if error else ""
                    overlap_qa.append((myo_record.QA_WARNING,
                                       f"Belly mesh is defective ({defects}): enclosed volume {volume_m3 * 1e6:.2f} cm3"
                                       f"{uncertainty} ({method}) used instead of {raw_volume_m3 * 1e6:.2f} cm3 "
                                       f"({(raw_volume_m3 / volume_m3 - 1) * 100:+.0f}%). Repair the mesh to remove "
                                       "the uncertainty"))

        path_m = myo_record.curve_length(path) * mpu
        linear_m = (i_cent - o_cent).length * mpu if origin and insertion else 0.0
        pcsa_m2, fiber_m = myo_record.pcsa_from_volume(volume_m3, path_m, props.fiber_length_ratio,
                                                       props.pennation_deg)
        values = {
            "myo_name": coll.name,
            "myo_side": myo_record.parse_side(coll.name),
            "myo_origin_obj": origin.name if origin else "",
            "myo_insertion_obj": insertion.name if insertion else "",
            "myo_path_obj": path.name if path else "",
            "myo_belly_obj": belly.name if belly else "",
            "myo_volume_m3": volume_m3,
            "myo_volume_raw_m3": raw_volume_m3,
            "myo_volume_method": volume_method,
            "myo_mass_kg": volume_m3 * props.density_g_cm3 * 1000.0,
            "myo_path_length_m": path_m,
            "myo_linear_length_m": linear_m,
            "myo_fiber_length_m": fiber_m,
            "myo_pcsa_m2": pcsa_m2,
            "myo_pcsa_method": myo_record.pcsa_method_label(props.fiber_length_ratio, props.pennation_deg),
            "myo_fiber_length_ratio": props.fiber_length_ratio,
            "myo_pennation_deg": props.pennation_deg,
            "myo_density_g_cm3": props.density_g_cm3,
            "myo_specific_tension_n_cm2": props.specific_tension,
            "myo_force_n": myo_record.force_from_pcsa(pcsa_m2, props.specific_tension),
            "myo_origin_area_m2": o_area_bu * mpu ** 2,
            "myo_insertion_area_m2": i_area_bu * mpu ** 2,
        }
        qa = myo_record.check_muscle(values, ref_m, belly_hole_error=hole_error,
                                     belly_signed_volume=signed_bu if belly else 1.0)
        qa.extend(overlap_qa)
        if belly is None:
            qa.insert(0, (myo_record.QA_ERROR, f"No belly mesh ('{coll.name}_muscle'): generate the final mesh"))
        if origin is None or insertion is None:
            qa.insert(0, (myo_record.QA_ERROR, "Origin or insertion surface missing"))
        rows.append(dict(values, collection=coll.name, origin_centroid=o_cent,
                         insertion_centroid=i_cent, qa=qa))

    bilateral = myo_record.check_bilateral({r["collection"]: r["myo_volume_m3"] for r in rows})
    for row in rows:
        row["qa"].extend(bilateral.get(row["collection"], []))
        if write:
            coll = bpy.data.collections[row["collection"]]
            myo_record.tag_roles(coll)
            record = {k: v for k, v in row.items() if k in myo_record.RECORD_KEYS}
            record["myo_qa"] = row["qa"]
            record["myo_updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            myo_record.write_record(coll, record)

    props.scene_qa = json.dumps(scene_findings)
    return rows, scene_findings



CSV_FIELDS = [
    ("name", lambda r: r["collection"]),
    ("side", lambda r: r["myo_side"]),
    ("volume_cm3", lambda r: r["myo_volume_m3"] * 1e6),
    ("volume_raw_cm3", lambda r: r["myo_volume_raw_m3"] * 1e6),
    ("volume_method", lambda r: r["myo_volume_method"]),
    ("mass_g", lambda r: r["myo_mass_kg"] * 1e3),
    ("path_length_cm", lambda r: r["myo_path_length_m"] * 100),
    ("fiber_length_cm", lambda r: r["myo_fiber_length_m"] * 100),
    ("linear_length_cm", lambda r: r["myo_linear_length_m"] * 100),
    ("origin_area_cm2", lambda r: r["myo_origin_area_m2"] * 1e4),
    ("insertion_area_cm2", lambda r: r["myo_insertion_area_m2"] * 1e4),
    ("pcsa_cm2", lambda r: r["myo_pcsa_m2"] * 1e4),
    ("force_N", lambda r: r["myo_force_n"]),
    ("origin_centroid_BU", lambda r: "({:.4f}, {:.4f}, {:.4f})".format(*r["origin_centroid"])),
    ("insertion_centroid_BU", lambda r: "({:.4f}, {:.4f}, {:.4f})".format(*r["insertion_centroid"])),
    ("density_g_cm3", lambda r: r["myo_density_g_cm3"]),
    ("specific_tension_N_cm2", lambda r: r["myo_specific_tension_n_cm2"]),
    ("fiber_length_ratio", lambda r: r["myo_fiber_length_ratio"]),
    ("pennation_deg", lambda r: r["myo_pennation_deg"]),
    ("qa", lambda r: " | ".join(f"{lvl}: {msg}" for lvl, msg in r["qa"])),
]


def write_csv(path, rows):
    """Write muscle rows to a CSV file (columns from :data:`CSV_FIELDS`).

    :arg path: Destination file.
    :type path: str
    :arg rows: Rows returned by :func:`compute_muscles`.
    :type rows: list of dict
    :raises OSError: If the file cannot be written.
    """
    with open(path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([name for name, _f in CSV_FIELDS])
        for row in rows:
            writer.writerow([f(row) for _name, f in CSV_FIELDS])
