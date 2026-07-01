import utm
from loguru import logger

from api.clients.aerobotics import Aerobotics
from api.trees.missing_tree_detector.detector import Detector, TreePosition
from api.trees.model import MissingTree, MissingTreesResponse

# minimum number of trees required to establish pattern in detection algorithm
_MIN_TREES_FOR_DETECTION = 3

class SurveyNotFoundError(Exception):
    """Raised when an orchard has no surveys to analyse."""

    def __init__(self, orchard_id: int):
        self.orchard_id = orchard_id
        super().__init__(f"no surveys found for orchard {orchard_id}")


class TreeService:
    """Orchestrates fetching survey data and running missing-tree detection."""

    def __init__(self, aerobotics: Aerobotics, detector: Detector):
        self._aerobotics = aerobotics
        self._detector = detector

    def detect_missing_trees(self, orchard_id: int) -> MissingTreesResponse:
        survey = self._aerobotics.get_latest_survey(orchard_id)
        if survey is None:
            raise SurveyNotFoundError(orchard_id)

        positions = [
            TreePosition(lat=tree.lat, lng=tree.lng)
            for tree in self._aerobotics.get_all_tree_surveys(survey.id)
            if tree.lat is not None and tree.lng is not None
        ]

        # ensure we have enough tree positions to actually detect missing trees
        if len(positions) < _MIN_TREES_FOR_DETECTION:
            logger.info(
                "Orchard {} survey {} has {} located trees; too few to detect gaps",
                orchard_id,
                survey.id,
                len(positions),
            )
            return MissingTreesResponse(missing_trees=[])

        # all trees in one orchard fall in the same UTM zone, so derive it
        _, _, zone_number, zone_letter = utm.from_latlon(
            positions[0].lat, positions[0].lng
        )

        # detect
        raw_missing = self._detector.detect_missing_trees(
            positions, zone_number, zone_letter
        )

        # construct response
        missing_trees = [
            MissingTree(lat=m["lat"], lng=m["lng"]) for m in raw_missing
        ]

        return MissingTreesResponse(missing_trees=missing_trees)
