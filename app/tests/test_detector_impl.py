"""Tests for the missing-tree detector.

The detector is a geometric heuristic, so the strategy is to build synthetic
orchards in UTM space (a regular grid), knock out known trees, convert the
survivors to lat/lng ``TreePosition``s, and assert the detector recovers the
gaps at (approximately) the right coordinates.
"""

import math
from typing import Iterable

import numpy as np
import pytest
import utm

from api.orchards.missing_tree_detector.detector import TreePosition
from api.orchards.missing_tree_detector.detector_impl import DetectorImpl, lerp

# Base location (Western Cape, SA) — all grids are built around this point.
BASE_LAT, BASE_LNG = -32.1, 18.9
_BASE_E, _BASE_N, ZONE_NUMBER, ZONE_LETTER = utm.from_latlon(BASE_LAT, BASE_LNG)

# Grid geometry (metres).
ALONG_SPACING = 5.0   # spacing between trees within a row (easting)
ACROSS_SPACING = 8.0  # spacing between rows (northing)

THRESHOLD_MULTIPLIER = 0.4


def _grid(
    n_rows: int,
    n_cols: int,
    *,
    drop: Iterable[tuple[int, int]] = (),
    rotation_deg: float = 0.0,
) -> list[TreePosition]:
    """Build a regular orchard grid as TreePositions, omitting ``drop`` cells.

    ``drop`` is a set of (row, col) indices to leave out. ``rotation_deg``
    rotates the whole grid about the base point to exercise orientation
    detection at non-axis-aligned angles.
    """
    dropped = set(drop)
    theta = math.radians(rotation_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)

    positions: list[TreePosition] = []
    for r in range(n_rows):
        for c in range(n_cols):
            if (r, c) in dropped:
                continue
            dx = c * ALONG_SPACING
            dy = r * ACROSS_SPACING
            # rotate offset about the origin then translate to base
            e = _BASE_E + dx * cos_t - dy * sin_t
            n = _BASE_N + dx * sin_t + dy * cos_t
            lat, lng = utm.to_latlon(e, n, ZONE_NUMBER, ZONE_LETTER)
            positions.append(TreePosition(lat=lat, lng=lng))
    return positions


def _cell_utm(r: int, c: int, rotation_deg: float = 0.0) -> tuple[float, float]:
    """UTM (easting, northing) of grid cell (r, c)."""
    theta = math.radians(rotation_deg)
    dx, dy = c * ALONG_SPACING, r * ACROSS_SPACING
    e = _BASE_E + dx * math.cos(theta) - dy * math.sin(theta)
    n = _BASE_N + dx * math.sin(theta) + dy * math.cos(theta)
    return e, n


def _to_utm(missing: dict) -> tuple[float, float]:
    e, n, _, _ = utm.from_latlon(missing["lat"], missing["lng"])
    return e, n


def _nearest_dist(missing: list[dict], target_utm: tuple[float, float]) -> float:
    """Smallest distance (m) from any detected tree to ``target_utm``."""
    tx, ty = target_utm
    return min(
        math.hypot(e - tx, n - ty)
        for e, n in (_to_utm(m) for m in missing)
    )


@pytest.fixture
def detector() -> DetectorImpl:
    return DetectorImpl(THRESHOLD_MULTIPLIER)

def test_returns_list_of_latlng_dicts(detector: DetectorImpl):
    missing = detector.detect_missing_trees(
        _grid(6, 6, drop=[(2, 3)]), ZONE_NUMBER, ZONE_LETTER
    )
    assert isinstance(missing, list)
    for m in missing:
        assert set(m) == {"lat", "lng"}
        assert isinstance(m["lat"], float)
        assert isinstance(m["lng"], float)

def test_perfect_grid_has_no_missing(detector: DetectorImpl):
    missing = detector.detect_missing_trees(_grid(7, 7), ZONE_NUMBER, ZONE_LETTER)
    assert missing == []

def test_single_interior_gap_detected(detector: DetectorImpl):
    missing = detector.detect_missing_trees(
        _grid(7, 7, drop=[(3, 3)]), ZONE_NUMBER, ZONE_LETTER
    )
    assert len(missing) == 1
    assert _nearest_dist(missing, _cell_utm(3, 3)) < 0.5

def test_consecutive_interior_gap_detects_two_trees(detector: DetectorImpl):
    # Remove two adjacent interior trees (a ~3x-spacing gap) in a short row.
    # Regression test: with a mean-based spacing estimate the inflated mean
    # under-counts this to 1; the median-based estimate recovers both.
    missing = detector.detect_missing_trees(
        _grid(7, 8, drop=[(3, 3), (3, 4)]), ZONE_NUMBER, ZONE_LETTER
    )
    assert len(missing) == 2
    assert _nearest_dist(missing, _cell_utm(3, 3)) < 0.5
    assert _nearest_dist(missing, _cell_utm(3, 4)) < 0.5

def test_multiple_rows_with_interior_gaps(detector: DetectorImpl):
    missing = detector.detect_missing_trees(
        _grid(8, 8, drop=[(2, 4), (5, 2)]), ZONE_NUMBER, ZONE_LETTER
    )
    assert len(missing) == 2
    assert _nearest_dist(missing, _cell_utm(2, 4)) < 0.5
    assert _nearest_dist(missing, _cell_utm(5, 2)) < 0.5

def test_two_separate_gaps_in_short_row(detector: DetectorImpl):
    # Two single gaps in one short row: the inflated mean would report 0,
    # the median recovers both.
    missing = detector.detect_missing_trees(
        _grid(7, 8, drop=[(3, 2), (3, 5)]), ZONE_NUMBER, ZONE_LETTER
    )
    assert len(missing) == 2
    assert _nearest_dist(missing, _cell_utm(3, 2)) < 0.5
    assert _nearest_dist(missing, _cell_utm(3, 5)) < 0.5

def test_end_of_row_gap_detected(detector: DetectorImpl):
    # Middle row (r=3) is missing its last two trees; neighbouring rows are
    # full and equal length, so the deficit is attributed to the row's end.
    missing = detector.detect_missing_trees(
        _grid(7, 8, drop=[(3, 6), (3, 7)]), ZONE_NUMBER, ZONE_LETTER
    )
    assert len(missing) == 2
    assert _nearest_dist(missing, _cell_utm(3, 6)) < 0.5
    assert _nearest_dist(missing, _cell_utm(3, 7)) < 0.5

@pytest.mark.parametrize("rotation_deg", [15.0, 30.0, 47.0])
def test_interior_gap_detected_on_rotated_orchard(detector: DetectorImpl, rotation_deg: float):
    missing = detector.detect_missing_trees(
        _grid(7, 7, drop=[(3, 3)], rotation_deg=rotation_deg),
        ZONE_NUMBER,
        ZONE_LETTER,
    )
    assert len(missing) == 1
    assert _nearest_dist(missing, _cell_utm(3, 3, rotation_deg)) < 0.5

def test_rows_with_fewer_than_three_trees_are_ignored(detector: DetectorImpl):
    # A 2-column grid: every row has only 2 trees, below the minimum needed
    # to establish an in-row pattern, so nothing is reported (and no crash).
    missing = detector.detect_missing_trees(_grid(6, 2), ZONE_NUMBER, ZONE_LETTER)
    assert missing == []

@pytest.mark.parametrize(
    "a,b,t,expected",
    [
        (0.0, 10.0, 0.0, 0.0),
        (0.0, 10.0, 1.0, 10.0),
        (0.0, 10.0, 0.5, 5.0),
        (2.0, 4.0, 0.25, 2.5),
    ],
)
def test_lerp_interpolates(a, b, t, expected):
    assert lerp(a, b, t) == pytest.approx(expected)

@pytest.mark.parametrize("a,b", [(None, 1.0), (1.0, None), (None, None)])
def test_lerp_returns_none_when_endpoint_missing(a, b):
    assert lerp(a, b, 0.5) is None
