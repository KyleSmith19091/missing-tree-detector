import utm
from loguru import logger

from api.clients.aerobotics import Aerobotics
from api.orchards.cache import MissingTreesCache
from api.orchards.missing_tree_detector.detector import Detector, TreePosition
from api.orchards.model import MissingTree, MissingTreesResponse

# minimum number of trees required to establish pattern in detection algorithm
_MIN_TREES_FOR_DETECTION = 3

class SurveyNotFoundError(Exception):
    """Raised when an orchard has no surveys to analyse."""

    def __init__(self, orchard_id: int):
        self.orchard_id = orchard_id
        super().__init__(f"no surveys found for orchard {orchard_id}")


class Service:
    """Orchestrates fetching survey data and running missing-tree detection."""

    def __init__(self, aerobotics: Aerobotics, detector: Detector, cache: MissingTreesCache | None = None):
        self._aerobotics = aerobotics
        self._detector = detector
        self._cache = cache if cache is not None else MissingTreesCache()

    def detect_missing_trees(self, orchard_id: int) -> MissingTreesResponse:
        survey = self._aerobotics.get_latest_survey(orchard_id)
        if survey is None:
            logger.error("survey not found for orchard with ID {}", orchard_id)
            raise SurveyNotFoundError(orchard_id)

        # return cached results for this survey if we've already computed them.
        cached = self._cache.get(survey.id, orchard_id)
        if cached is not None:
            logger.info("cache hit for orchard {} survey {}", orchard_id, survey.id)
            return MissingTreesResponse(missing_trees=cached)

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
            self._cache.set(survey.id, orchard_id, [])
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

        self._cache.set(survey.id, orchard_id, missing_trees)
        return MissingTreesResponse(missing_trees=missing_trees)
