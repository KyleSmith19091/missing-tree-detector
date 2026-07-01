import math
from collections import defaultdict

import numpy as np
import utm
from scipy.spatial import KDTree

from api.orchards.missing_tree_detector.detector import Detector, TreePosition


class DetectorImpl(Detector):
    def __init__(self, row_spacing_threshold_multiplier: float):
        super().__init__()
        self.row_spacing_threshold_multiplier = row_spacing_threshold_multiplier

    def detect_missing_trees(
        self, tree_positions: list[TreePosition], utm_zone_number: int, utm_zone_letter: str
    ) -> list[dict]:
        """
        detect_missing_trees implements a novel algorithm for trying
        to estimate possible missing trees from a list of tree positions
        within an orchard

        """

        # convert tree positions to UTM coordinates
        tree_positions_utm = np.array(
            [[point.as_utm()[0], point.as_utm()[1]] for point in tree_positions]
        )

        # determine dominant row orientation (assumes single dominant orientation)
        angle_perpendicular, angle_along = self._determine_dominant_row_orientations(
            tree_positions_utm
        )

        # project tree positions to vector perpendicular to dominant orientation direction vector
        projections_perpendicular = tree_positions_utm @ angle_perpendicular

        # estimate the row spacing between the rows of trees
        row_spacing = self._estimate_row_spacing(tree_positions_utm, projections_perpendicular)

        # construct rows using row spacing
        rows = self._cluster_rows_by_spacing(
            tree_positions_utm, row_spacing, projections_perpendicular
        )

        # check for missing trees along a row
        missing_trees_along_row = self._detect_missing_trees_along_rows(
            rows,
            angle_along,
            utm_zone_number,
            utm_zone_letter,
        )

        # check for trees missing at the edges of rows
        missing_trees_across_edges = self._detect_missing_trees_across_edges(
            rows,
            missing_trees_along_row,
            angle_along,
            utm_zone_number,
            utm_zone_letter,
        )

        missing_trees = []
        for _, missing_trees_in_row in missing_trees_along_row.items():
            missing_trees.extend(missing_trees_in_row)

        for missing_tree in missing_trees_across_edges:
            missing_trees.append(missing_tree)

        return missing_trees

    def _detect_missing_trees_along_rows(
        self, rows: dict, angle_along: np.ndarray, utm_zone_number: int, utm_zone_letter: str
    ) -> dict:
        # for each row, estimate the in-row spacing and interpolate trees into
        # any interior gap that is wide enough to hold one or more trees
        missing_trees_along_row = defaultdict(list)
        for label, positions_in_row in rows.items():
            # need at least three trees to establish a pattern
            if len(positions_in_row) < 3:
                continue

            projections_and_positions = []
            for position in positions_in_row:
                projection = np.dot(position, angle_along)
                projections_and_positions.append((projection, position))
            # sort projection values in ascending order (left to right)
            projections_and_positions.sort(key=lambda x: x[0])

            # Use the median (not mean) spacing as the "one tree" reference.
            # The mean is inflated by the very gaps we're trying to count, which
            # makes round(gap / spacing) under-count adjacent/clustered gaps.
            # The median ignores a minority of large gaps, so it stays at the
            # true single-tree spacing.
            spacings = np.diff([p for p, _ in projections_and_positions])
            typical_spacing = np.median(spacings)
            if typical_spacing <= 0:
                continue

            for i, distance in enumerate(spacings):
                number_missing = round(distance / typical_spacing) - 1
                if number_missing <= 0:
                    continue

                tree_before_position = projections_and_positions[i][1]
                tree_after_position = projections_and_positions[i + 1][1]

                for j in range(1, number_missing + 1):
                    step = j / (number_missing + 1)
                    missing_easting = lerp(tree_before_position[0], tree_after_position[0], step)
                    missing_northing = lerp(tree_before_position[1], tree_after_position[1], step)
                    lat, lng = utm.to_latlon(
                        missing_easting, missing_northing, utm_zone_number, utm_zone_letter
                    )
                    missing_trees_along_row[label].append({"lat": lat, "lng": lng})

        return missing_trees_along_row

    def _detect_missing_trees_across_edges(
        self,
        rows: dict,
        missing_trees_along_row: dict,
        angle_along: np.ndarray,
        utm_zone_number: int,
        utm_zone_letter: str,
    ) -> list:
        # scan rows in triplets; when the top and bottom neighbours agree on
        # tree count but the middle row is short, the deficit is attributed to
        # trees missing off the ends of the middle row
        missing_trees_across_edges = []
        sorted_row_labels = sorted(rows)
        for i in range(1, len(sorted_row_labels) - 1):
            top_label = sorted_row_labels[i - 1]
            top_positions = rows[top_label]
            top_num_trees = len(top_positions) + len(missing_trees_along_row[top_label])
            top_projections_along_row = np.dot(top_positions, angle_along)
            top_first_tree_position_projection = np.min(top_projections_along_row)
            top_last_tree_position_projection = np.max(top_projections_along_row)

            middle_label = sorted_row_labels[i]
            middle_positions = rows[middle_label]
            middle_num_trees = len(middle_positions) + len(missing_trees_along_row[middle_label])
            middle_projections_along_row = np.dot(middle_positions, angle_along)
            middle_first_tree_position_projection = np.min(middle_projections_along_row)
            middle_last_tree_position_projection = np.max(middle_projections_along_row)
            middle_mean_spacing = np.mean(np.diff(np.sort(middle_projections_along_row)))

            bottom_label = sorted_row_labels[i + 1]
            bottom_positions = rows[bottom_label]
            bottom_num_trees = len(bottom_positions) + len(missing_trees_along_row[bottom_label])
            bottom_projections_along_row = np.dot(bottom_positions, angle_along)
            bottom_first_tree_position_projection = np.min(bottom_projections_along_row)
            bottom_last_tree_position_projection = np.max(bottom_projections_along_row)

            # if the top and middle don't have the same number of trees we can not establish pattern
            if top_num_trees != bottom_num_trees:
                continue

            deficit = top_num_trees - middle_num_trees
            if deficit <= 0:  # middle has more trees than top/bottom, so no reliable pattern here
                continue

            start_gap = middle_first_tree_position_projection - min(
                top_first_tree_position_projection, bottom_first_tree_position_projection
            )
            missing_at_start = max(0, round(start_gap / middle_mean_spacing))

            end_gap = (
                max(top_last_tree_position_projection, bottom_last_tree_position_projection)
                - middle_last_tree_position_projection
            )
            missing_at_end = max(0, round(end_gap / middle_mean_spacing))

            if missing_at_start > 0:
                first_tree_position = middle_positions[np.argmin(middle_projections_along_row)]
                for j in range(1, missing_at_start + 1):
                    utm_e = first_tree_position[0] - j * middle_mean_spacing * angle_along[0]
                    utm_n = first_tree_position[1] - j * middle_mean_spacing * angle_along[1]
                    lat, lng = utm.to_latlon(utm_e, utm_n, utm_zone_number, utm_zone_letter)
                    missing_trees_across_edges.append({"lat": lat, "lng": lng})

            if missing_at_end > 0:
                last_tree_position = middle_positions[np.argmax(middle_projections_along_row)]
                for j in range(1, missing_at_end + 1):
                    utm_e = last_tree_position[0] + j * middle_mean_spacing * angle_along[0]
                    utm_n = last_tree_position[1] + j * middle_mean_spacing * angle_along[1]
                    lat, lng = utm.to_latlon(utm_e, utm_n, utm_zone_number, utm_zone_letter)
                    missing_trees_across_edges.append({"lat": lat, "lng": lng})

        return missing_trees_across_edges

    def _determine_dominant_row_orientations(
        self, tree_positions: np.ndarray
    ) -> tuple[float, float]:
        # KDTree will organise points according to their relative distances
        kdtree = KDTree(tree_positions)

        # select K nearby tree positions for each
        # tree position in the tree. Four is chosen
        # since the idea is that the trees are in a pretty uniform grid
        # so the closest trees should be above, below, left and right
        K = 4
        _, indices = kdtree.query(tree_positions, k=K + 1)

        # calculate the relative angle between each tree and the selected neighbour trees
        angles = []
        for i, neighbours in enumerate(indices):
            for j in neighbours[1:]:  # skip self
                dx = tree_positions[j, 0] - tree_positions[i, 0]
                dy = tree_positions[j, 1] - tree_positions[i, 1]
                angle = math.atan2(dy, dx) % math.pi  # pi == 180 degrees, radials used by default
                angles.append(angle)

        # group angles, values are in radial form, but would still result in 180 possible values
        hist, bins = np.histogram(angles, bins=180, range=(0, math.pi))

        # determine most popular bin
        row_angle = bins[np.argmax(hist)]

        # determine the orientation of the row
        along = np.array([math.cos(row_angle), math.sin(row_angle)])

        # determine the direction perpendicular to row orientation
        up = np.array([-math.sin(row_angle), math.cos(row_angle)])

        return (up, along)

    def _estimate_row_spacing(
        self, tree_positions: np.ndarray, projections_perpendicular: np.ndarray
    ) -> float:
        # group perpendicular projections
        hist, bins = np.histogram(
            projections_perpendicular,
            bins=max(100, len(tree_positions) // 2),
        )

        # subtract each bin with the mean bin so we get negative values
        # for empty bins during the correlation calculation
        hist_centered = hist - hist.mean()

        autocorr = np.correlate(hist_centered, hist_centered, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]  # positive lags only

        # find peaks: a point greater than the previous value but less than the next
        bin_width = bins[1] - bins[0]
        min_lag = max(1, int(1.0 / bin_width))
        peaks = []
        for i in range(min_lag, len(autocorr) - 1):
            if autocorr[i] > autocorr[i - 1] and autocorr[i] > autocorr[i + 1]:
                peaks.append((i, autocorr[i]))

        if peaks:
            row_spacing = max(peaks, key=lambda p: p[1])[0] * bin_width
        else:
            # if no peaks are found then just select the median
            row_spacing = np.median(np.diff(np.sort(projections_perpendicular)))

        return row_spacing

    def _cluster_rows_by_spacing(
        self, tree_positions: np.ndarray, row_spacing: float, projections_perpendicular: np.ndarray
    ) -> dict:
        threshold = row_spacing * self.row_spacing_threshold_multiplier

        # sort projections by magnitude (via index so we don't reorder the array)
        sorted_index = np.argsort(projections_perpendicular)
        sorted_projections = projections_perpendicular[sorted_index]

        # used to map a projection to a row given the index of the projection
        sorted_row_labels = np.zeros_like(sorted_projections, dtype=int)

        curr_row_label = 0
        sorted_row_labels[0] = curr_row_label
        for i in range(1, len(sorted_projections)):
            # since we've sorted the projection, the first value for which this
            # is true will be the first projection of the next row
            if (sorted_projections[i] - sorted_projections[i - 1]) > threshold:
                curr_row_label += 1
            sorted_row_labels[i] = curr_row_label

        # create rows index using the labels to group tree positions
        rows = defaultdict(list)
        row_labels = np.zeros_like(sorted_projections, dtype=int)
        row_labels[sorted_index] = sorted_row_labels
        for position, label in zip(tree_positions, row_labels, strict=False):
            rows[label].append(position)

        return rows


def lerp(a: float | None, b: float | None, t: float) -> float | None:
    if a is None or b is None:
        return None
    return float(a) + (float(b) - float(a)) * t
