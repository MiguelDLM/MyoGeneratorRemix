"""Point correspondence between the origin and insertion contours of a loft.

The muscle belly is lofted between two closed contours (the boundaries of the
attachment areas). The loft joins point ``j`` of one contour to point ``j``
of the other, so the result depends on where each contour starts, which way
it runs and how many vertices it has. Matching by vertex index produced
twisted, hourglass-shaped bellies unless the index was rotated by hand.

This module removes that dependence:

1. :func:`resample_closed_loop` - both contours are resampled to the same
   number of points, evenly spaced by arc length (independent of the original
   vertex count and density).
2. Both contours are centred on their centroids. By default they are compared
   in 3D (they are rarely planar: a temporal fossa boundary is strongly
   curved); :func:`local_coordinates` can instead express them in 2D frames,
   for lofts that rotate their sections with the path.
3. Direction: both contours must circulate the same way, i.e. their vector
   areas (:func:`vector_area`, the contours' own normals) must point to the
   same side. Elongated contours otherwise "match" just as well backwards,
   and the loft folds into a figure-eight with almost no area in the middle
   (its RMS size looks fine, its volume does not). This also holds for
   sheet-like muscles such as the temporalis, whose attachment contours are
   seen edge-on from the origin-insertion axis. Only when the two normals are
   nearly perpendicular is the direction left to the search.
4. :func:`best_cyclic_match` - the starting point is chosen to minimise the
   sum of squared distances between corresponding centred points, i.e. to
   maximise ``sum a_j . b_j``, the size of the loft's mid-way section
   ``(a + b) / 2``. The cost is invariant to translation and scale.

Diagnostics: :func:`waist_index` (RMS size of the mid-way section relative to
the ends; < 1 = hourglass) and :func:`section_area_ratio` (area of the mid-way
section relative to the ends; near 0 = folded or twisted).

No dependency on ``bpy``: works on sequences of 3-vectors and is unit-tested
outside Blender (``tests/test_contour_matching.py``).
"""

import math

import numpy as np


def _array(points):
    return np.array([tuple(p)[:3] for p in points], dtype=float)


def resample_closed_loop(points, n):
    """Resample a closed polyline to ``n`` points evenly spaced by arc length.

    :arg points: Contour points in order (the last point is joined to the first).
    :type points: sequence of 3-vectors
    :arg n: Number of output points (>= 3).
    :type n: int
    :return: ``n`` points; starts at ``points[0]``.
    :rtype: numpy.ndarray of shape (n, 3)
    :raises ValueError: With fewer than 3 points or a zero-length contour.
    """
    pts = _array(points)
    if len(pts) < 3:
        raise ValueError("a closed contour needs at least 3 points")
    closed = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    total = seg.sum()
    if total <= 0.0:
        raise ValueError("zero-length contour")
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    targets = np.arange(n) * total / n
    out = np.empty((n, 3))
    k = 0
    for i, s in enumerate(targets):
        while cum[k + 1] < s:
            k += 1
        t = (s - cum[k]) / seg[k] if seg[k] > 0.0 else 0.0
        out[i] = closed[k] + t * (closed[k + 1] - closed[k])
    return out


def local_coordinates(points, normal, binormal):
    """2D coordinates of a contour around its centroid in a frame.

    :arg points: Contour points.
    :type points: array-like of shape (n, 3)
    :arg normal: First in-plane axis (e.g. the path normal at that end).
    :type normal: 3-vector
    :arg binormal: Second in-plane axis (the path binormal at that end).
    :type binormal: 3-vector
    :return: ``(n, 2)`` coordinates; the component along the path tangent is dropped.
    :rtype: numpy.ndarray
    """
    pts = _array(points)
    centred = pts - pts.mean(axis=0)
    return np.column_stack([centred @ _array([normal])[0], centred @ _array([binormal])[0]])


def best_cyclic_match(a, b, directions=(False, True)):
    """Cyclic shift and direction of ``b`` that best matches ``a``.

    Minimises ``sum_j |a[j] - b[(s + d*j) mod n]|^2`` over shifts ``s`` and
    directions ``d`` in {+1, -1}.

    :arg a: Reference contour (e.g. origin), any dimension.
    :type a: array-like of shape (n, k)
    :arg b: Contour to re-index (e.g. insertion), same shape.
    :type b: array-like of shape (n, k)
    :arg directions: Directions to try: ``False`` = as given, ``True`` = reversed.
    :type directions: tuple of bool
    :return: ``(shift, reversed, mean_distance)``; apply with :func:`apply_match`.
       ``mean_distance`` is the RMS distance between matched points.
    :rtype: tuple of (int, bool, float)
    :raises ValueError: If the shapes differ.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise ValueError("contours must have the same number of points (resample them first)")
    n = len(a)
    best = None
    for rev in directions:
        order = np.arange(n) if not rev else -np.arange(n)
        for s in range(n):
            cost = ((a - b[(s + order) % n]) ** 2).sum()
            if best is None or cost < best[0] - 1e-12:
                best = (cost, s, rev)
    cost, shift, rev = best
    return shift, rev, math.sqrt(cost / n)


def apply_match(points, shift, reverse):
    """Re-index a contour with the result of :func:`best_cyclic_match`.

    :arg points: Contour points (``n`` of them).
    :type points: sequence
    :arg shift: Index of the point matched to reference point 0.
    :type shift: int
    :arg reverse: Whether the contour runs backwards.
    :type reverse: bool
    :return: Re-indexed points (same element type as the input).
    :rtype: list
    """
    pts = list(points)
    n = len(pts)
    step = -1 if reverse else 1
    return [pts[(shift + step * j) % n] for j in range(n)]


def waist_index(origin, insertion):
    """Hourglass diagnostic of a straight loft between matched contours.

    :arg origin: Origin contour points, matched order.
    :type origin: array-like of shape (n, 3)
    :arg insertion: Insertion contour points, same order.
    :type insertion: array-like of shape (n, 3)
    :return: RMS radius of the mid-way contour divided by the mean RMS radius
       of the two ends: 1 = no narrowing, values well below 1 = hourglass (twist).
    :rtype: float
    """
    o, i = _array(origin), _array(insertion)

    def radius(p):
        return float(np.sqrt(((p - p.mean(axis=0)) ** 2).sum(axis=1).mean()))
    ends = (radius(o) + radius(i)) / 2
    return radius((o + i) / 2) / ends if ends > 0.0 else 1.0


def vector_area(points):
    """Vector area of a closed contour (around its centroid).

    Its direction is the contour's circulation axis (right-hand rule) and its
    length the area of a planar contour.

    :arg points: Contour points in order.
    :type points: array-like of shape (n, 3)
    :rtype: numpy.ndarray of shape (3,)
    """
    p = _array(points)
    p = p - p.mean(axis=0)
    return 0.5 * np.cross(p, np.roll(p, -1, axis=0)).sum(axis=0)


def section_area_ratio(origin, insertion):
    """Area of the mid-way loft section relative to the ends.

    :arg origin: Origin contour points, matched order.
    :type origin: array-like of shape (n, 3)
    :arg insertion: Insertion contour points, same order.
    :type insertion: array-like of shape (n, 3)
    :return: ``|A_mid| / mean(|A_origin|, |A_insertion|)`` with ``A`` the vector
       areas; about 1 for a well-formed loft (can exceed 1 when the end contours
       are differently oriented), near 0 when the middle section folds into a
       figure-eight.
    :rtype: float
    """
    o, i = _array(origin), _array(insertion)
    ends = (np.linalg.norm(vector_area(o)) + np.linalg.norm(vector_area(i))) / 2
    return float(np.linalg.norm(vector_area((o + i) / 2)) / ends) if ends > 0.0 else 1.0


def circulation_directions(origin, insertion, perpendicular=0.2):
    """Directions of the insertion contour worth trying.

    :arg origin: Origin contour points (resampled).
    :type origin: array-like of shape (n, 3)
    :arg insertion: Insertion contour points (resampled).
    :type insertion: array-like of shape (n, 3)
    :arg perpendicular: If the cosine between the two contour normals is below
       this value they count as perpendicular (direction undetermined).
    :type perpendicular: float
    :return: ``(False,)`` if both circulate the same way (normals on the same
       side), ``(True,)`` if oppositely, ``(False, True)`` if undetermined.
    :rtype: tuple of bool
    """
    ao, ai = vector_area(origin), vector_area(insertion)
    norm = np.linalg.norm(ao) * np.linalg.norm(ai)
    if norm == 0.0:
        return (False, True)
    cosine = (ao @ ai) / norm
    if abs(cosine) < perpendicular:
        return (False, True)
    return (False,) if cosine > 0.0 else (True,)


def match_contours(origin_points, insertion_points, n, origin_frame=None, insertion_frame=None):
    """Resample both contours to ``n`` points and re-index the insertion one.

    :arg origin_points: Origin contour, in order.
    :type origin_points: sequence of 3-vectors
    :arg insertion_points: Insertion contour, in order (any start, direction, count).
    :type insertion_points: sequence of 3-vectors
    :arg n: Points per contour in the loft.
    :type n: int
    :arg origin_frame: ``(normal, binormal)`` of the path at the origin end, to
       compare the contours in 2D path frames; None (default) compares the
       centred contours in 3D, which suits lofts that interpolate in world space.
    :type origin_frame: tuple of 3-vectors or None
    :arg insertion_frame: ``(normal, binormal)`` of the path at the insertion end
       (parallel-transported from the origin, so both frames are consistent).
    :type insertion_frame: tuple of 3-vectors or None
    :return: ``(origin, insertion, info)``: ``(n, 3)`` arrays in matched order and
       a dict with ``shift``, ``reversed``, ``rms_mismatch`` (contour units),
       ``waist`` (:func:`waist_index`) and ``section_area``
       (:func:`section_area_ratio`) of the matched pair.
    :rtype: tuple
    """
    origin = resample_closed_loop(origin_points, n)
    insertion = resample_closed_loop(insertion_points, n)
    if origin_frame is None or insertion_frame is None:
        a, b = origin - origin.mean(axis=0), insertion - insertion.mean(axis=0)
    else:
        a = local_coordinates(origin, *origin_frame)
        b = local_coordinates(insertion, *insertion_frame)
    shift, rev, rms = best_cyclic_match(a, b, circulation_directions(origin, insertion))
    insertion = np.array(apply_match(insertion, shift, rev))
    return origin, insertion, {"shift": shift, "reversed": rev, "rms_mismatch": rms,
                               "waist": waist_index(origin, insertion),
                               "section_area": section_area_ratio(origin, insertion)}
