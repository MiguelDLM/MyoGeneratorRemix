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

from . import belly_fibres, myo_record


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


def _surface_gap(surface_obj, point):
    """Distance (Blender units) from a point to a mesh surface."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(surface_obj.data)
    bm.transform(surface_obj.matrix_world)
    hit = BVHTree.FromBMesh(bm).find_nearest(point)
    bm.free()
    return hit[3] if hit[0] is not None else None


def measure_fibres(props, belly, origin, insertion, path_m, mpu):
    """Belly fibres of one muscle for the fibre length, with their QA findings.

    :arg props: Scene settings (``scene.myogen``).
    :type props: :class:`bpy.types.PropertyGroup`
    :arg belly: Belly mesh, or None.
    :type belly: :class:`bpy.types.Object`
    :arg origin: Origin attachment, or None.
    :type origin: :class:`bpy.types.Object`
    :arg insertion: Insertion attachment, or None.
    :type insertion: :class:`bpy.types.Object`
    :arg path_m: Path length (m), for the plausibility check.
    :type path_m: float
    :arg mpu: Metres per Blender unit.
    :type mpu: float
    :return: ``(fibres, findings)``; ``fibres`` (:func:`belly_fibres.belly_fibres`)
       is None when they cannot be traced (the path is then used).
    :rtype: tuple
    """
    if belly is None or origin is None or insertion is None:
        return None, []
    try:
        fibres = belly_fibres.belly_fibres(belly, origin, insertion, props.belly_fibre_count,
                                           props.fibre_seeding)
    except ValueError as e:
        return None, [(myo_record.QA_WARNING, f"Belly fibres could not be traced ({e}): path length used")]
    findings = []
    for role, key in (("origin", "origin_contact"), ("insertion", "insertion_contact")):
        if fibres[key] < myo_record.ATTACHMENT_CONTACT_MIN:
            findings.append((myo_record.QA_WARNING, f"The belly touches only {fibres[key] * 100:.0f}% of the {role} "
                                                    f"area: the {role} is painted larger than the belly, or the "
                                                    "belly falls short of it; no fibre can reach the rest"))
    if fibres["reached"] < myo_record.FIBER_REACHED_MIN:
        findings.append((myo_record.QA_WARNING, f"Only {fibres['reached'] * 100:.0f}% of the belly fibres reach "
                                                "the other attachment (Show in Scene > Fibres)"))
    if fibres["detoured"] > myo_record.FIBER_DETOURED_MAX:
        findings.append((myo_record.QA_WARNING, f"{fibres['detoured'] * 100:.0f}% of the belly fibres detour (longer "
                                                f"than {belly_fibres.DETOUR_MAX:g}x the straight distance between "
                                                "their ends) and are left out: check the belly shape "
                                                "(Show in Scene > Fibres, magenta)"))
    longest = float(fibres["lengths"].max()) * mpu
    if path_m > 0.0 and longest > myo_record.FIBER_MAX_TO_PATH * path_m:
        findings.append((myo_record.QA_WARNING, f"Longest belly fibre is {longest / path_m:.1f}x the path: the "
                                                "belly may detour (Show in Scene > Fibres)"))
    return fibres, findings


#: Cells across the largest side of the box where two bellies may overlap.
OVERLAP_CELLS_ACROSS = 64
#: Remesh voxel of the closed belly copies (fraction of the belly's size).
OVERLAP_REMESH = 1.0 / 192
#: A closed copy smaller than this fraction of the belly's own volume has collapsed.
OVERLAP_MIN_CLOSED = 0.25


def belly_overlaps(collections, metres_per_unit):
    """Volume shared by every pair of bellies whose bounding boxes intersect.

    Each belly is closed first (temporary voxel remesh,
    :func:`belly_fibres.closed_belly`: sculpted bellies may have holes or
    self-overlaps); both are rasterised on one grid over the intersection of
    their boxes (``OVERLAP_CELLS_ACROSS`` cells across) and the cells inside
    both are counted.

    :arg collections: Muscle collections.
    :type collections: list of :class:`bpy.types.Collection`
    :arg metres_per_unit: Metres per Blender unit.
    :type metres_per_unit: float
    :return: ``(shared, unchecked)``: ``(name_a, name_b)`` -> shared volume
       (m³) for pairs that share any, and the names of bellies whose closed
       copy collapsed (less than ``OVERLAP_MIN_CLOSED`` of their own volume:
       their overlaps cannot be measured).
    :rtype: tuple
    """
    import numpy as np
    from mathutils.bvhtree import BVHTree
    from . import volume_builder
    bellies = []
    for coll in collections:
        belly = myo_record.resolve_objects(coll).get("belly")
        if belly is not None and belly.type == 'MESH' and belly.data.polygons:
            corners = [belly.matrix_world @ Vector(c) for c in belly.bound_box]
            lo = np.array([min(c[i] for c in corners) for i in range(3)])
            hi = np.array([max(c[i] for c in corners) for i in range(3)])
            bellies.append((coll.name, belly, lo, hi))
    closed = {}
    unchecked = set()
    for name, belly, _lo, _hi in bellies:
        bm = belly_fibres.closed_belly(belly, max(belly.dimensions) * OVERLAP_REMESH)
        co = np.array([list(v.co) for v in bm.verts])
        if abs(bm.calc_volume(signed=True)) < OVERLAP_MIN_CLOSED * myo_record.mesh_stats(belly)[0]:
            unchecked.add(name)
        else:
            closed[name] = (BVHTree.FromBMesh(bm), co.min(0)[2])
        bm.free()

    out = {}
    for i, (na, ba, la, ha) in enumerate(bellies):
        for nb, bb, lb, hb in bellies[i + 1:]:
            if na in unchecked or nb in unchecked:
                continue
            lo, hi = np.maximum(la, lb), np.minimum(ha, hb)
            if np.any(hi <= lo):
                continue
            voxel = float((hi - lo).max()) / OVERLAP_CELLS_ACROSS
            jitter = voxel * 0.0137
            xs = np.arange(lo[0] + voxel / 2, hi[0], voxel) + jitter
            ys = np.arange(lo[1] + voxel / 2, hi[1], voxel) + 0.7 * jitter
            zs = np.arange(lo[2] + voxel / 2, hi[2], voxel)
            if not (len(xs) and len(ys) and len(zs)):
                continue
            inside = None
            for name in (na, nb):
                t, z_min = closed[name]
                occ = volume_builder.occupancy(t, xs, ys, zs, min(z_min, lo[2]) - voxel, signed=False,
                                               columns=None if inside is None else inside.any(axis=2))
                inside = occ if inside is None else inside & occ
                if not inside.any():
                    break
            shared = float(inside.sum()) * voxel ** 3 * metres_per_unit ** 3
            if shared > 0.0:
                out[(na, nb)] = shared
    return out, unchecked


def compute_muscles(context, write=True):
    """Measure every muscle, run the plausibility checks and write the records.

    Per muscle: volume and mass (belly; the voxel-enclosed volume replaces the
    signed-sum volume when a closed belly overlaps itself by more than
    ``myo_record.OVERLAP_VOLUME_TOLERANCE``), path length and straight length
    (between the path's terminal vertices, :func:`myo_record.curve_ends`; the
    attachment centroids without a path) with a check that the path ends lie
    on their attachment areas, fibre length
    and PCSA (:func:`myo_record.pcsa_from_volume` with the scene's ratio and
    pennation, or :func:`myo_record.pcsa_from_fibres` from the belly fibres
    when ``fiber_length_source`` is ``BELLY_FIBRES``; with ``write`` the fibres
    are then also exported as ``<M>_fibres`` for simulators,
    :func:`belly_fibres.export_fibres`), force, attachment areas and centroids, then
    :func:`myo_record.check_muscle`, the left/right comparison and the
    overlap between muscles (:func:`belly_overlaps`,
    :func:`myo_record.check_overlaps`).

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
        ends = myo_record.curve_ends(path)
        path_qa = []
        if ends is not None:                                     # straight line between the path's terminal vertices
            linear_m = (ends[1] - ends[0]).length * mpu
            if origin is not None and insertion is not None:
                path_qa = myo_record.check_path_ends(_surface_gap(origin, ends[0]) * mpu,
                                                     _surface_gap(insertion, ends[1]) * mpu, path_m)
        else:
            linear_m = (i_cent - o_cent).length * mpu if origin and insertion else 0.0
        pcsa_m2, fiber_m = myo_record.pcsa_from_volume(volume_m3, path_m, props.fiber_length_ratio,
                                                       props.pennation_deg)
        source, fibre_values, fibre_qa, fibres = "PATH", {}, [], None
        if props.fiber_length_source == 'BELLY_FIBRES':
            fibres, fibre_qa = measure_fibres(props, belly, origin, insertion, path_m, mpu)
            if fibres is not None:
                source = "BELLY_FIBRES"
                lengths_m = fibres["lengths"] * mpu
                pcsa_m2, fiber_m = myo_record.pcsa_from_fibres(
                    volume_m3, lengths_m, fibres["shares"], props.fiber_length_ratio, props.pennation_deg,
                    props.pcsa_model, weights=fibres["weights"])
                stats = belly_fibres.length_stats(lengths_m * props.fiber_length_ratio, fibres["weights"])
                fibre_values = {
                    "myo_fiber_count": len(lengths_m),
                    "myo_fiber_length_sd_m": stats["sd"],
                    "myo_fiber_length_min_m": stats["min"],
                    "myo_fiber_length_max_m": stats["max"],
                    "myo_fiber_reached": fibres["reached"],
                    "myo_fiber_detoured": fibres["detoured"],
                    "myo_origin_contact": fibres["origin_contact"],
                    "myo_insertion_contact": fibres["insertion_contact"],
                }
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
            "myo_pcsa_method": myo_record.pcsa_method_label(props.fiber_length_ratio, props.pennation_deg,
                                                            source, props.pcsa_model),
            "myo_fiber_length_ratio": props.fiber_length_ratio,
            "myo_fiber_length_source": source,
            "myo_pennation_deg": props.pennation_deg,
            "myo_density_g_cm3": props.density_g_cm3,
            "myo_specific_tension_n_cm2": props.specific_tension,
            "myo_force_n": myo_record.force_from_pcsa(pcsa_m2, props.specific_tension),
            "myo_origin_area_m2": o_area_bu * mpu ** 2,
            "myo_insertion_area_m2": i_area_bu * mpu ** 2,
            **fibre_values,
        }
        if write and fibres is not None and source == "BELLY_FIBRES":
            fibres_obj = belly_fibres.export_fibres(coll, coll.name, fibres, volume_m3, mpu,
                                                    props.fiber_length_ratio, props.pennation_deg)
            values["myo_fibres_obj"] = fibres_obj.name
        qa = myo_record.check_muscle(values, ref_m, belly_hole_error=hole_error,
                                     belly_signed_volume=signed_bu if belly else 1.0)
        qa.extend(overlap_qa)
        qa.extend(path_qa)
        qa.extend(fibre_qa)
        if belly is None:
            qa.insert(0, (myo_record.QA_ERROR, f"No belly mesh ('{coll.name}_muscle'): generate the final mesh"))
        if origin is None or insertion is None:
            qa.insert(0, (myo_record.QA_ERROR, "Origin or insertion surface missing"))
        rows.append(dict(values, collection=coll.name, origin_centroid=o_cent,
                         insertion_centroid=i_cent, qa=qa))

    bilateral = myo_record.check_bilateral({r["collection"]: r["myo_volume_m3"] for r in rows})
    shared, unchecked = belly_overlaps([bpy.data.collections[r["collection"]] for r in rows], mpu)
    overlaps = myo_record.check_overlaps(shared, {r["collection"]: r["myo_volume_m3"] for r in rows})
    for name in unchecked:
        overlaps.setdefault(name, []).append(
            (myo_record.QA_INFO, "Overlap with other muscles not checked: the belly mesh is too defective to "
                                 "close (repair it)"))
    for row in rows:
        row["qa"].extend(bilateral.get(row["collection"], []))
        row["qa"].extend(overlaps.get(row["collection"], []))
        if write:
            coll = bpy.data.collections[row["collection"]]
            myo_record.tag_roles(coll)
            record = {k: v for k, v in row.items() if k in myo_record.RECORD_KEYS}
            record["myo_qa"] = row["qa"]
            record["myo_updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            myo_record.write_record(coll, record)

    props.scene_qa = json.dumps(scene_findings)
    return rows, scene_findings



def _cm(metres):
    return "" if metres is None else metres * 100


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
    ("fiber_length_source", lambda r: r["myo_fiber_length_source"]),
    ("fiber_count", lambda r: r.get("myo_fiber_count", "")),
    ("fiber_length_sd_cm", lambda r: _cm(r.get("myo_fiber_length_sd_m"))),
    ("fiber_length_min_cm", lambda r: _cm(r.get("myo_fiber_length_min_m"))),
    ("fiber_length_max_cm", lambda r: _cm(r.get("myo_fiber_length_max_m"))),
    ("fiber_reached", lambda r: r.get("myo_fiber_reached", "")),
    ("fiber_detoured", lambda r: r.get("myo_fiber_detoured", "")),
    ("origin_contact", lambda r: r.get("myo_origin_contact", "")),
    ("insertion_contact", lambda r: r.get("myo_insertion_contact", "")),
    ("pcsa_method", lambda r: r["myo_pcsa_method"]),
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
