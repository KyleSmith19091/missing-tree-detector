from functools import lru_cache

from fastapi import APIRouter, Depends

from api.clients.aerobotics_impl import AeroboticsClient
from api.core.config import settings
from api.trees.missing_tree_detector.detector_impl import DetectorImpl
from api.trees.model import MissingTreesResponse
from api.trees.service import TreeService

router = APIRouter(prefix="/orchards", tags=["trees"])

@lru_cache
def build_tree_service() -> TreeService:
    """Build the TreeService

    Cached so the Aerobotics HTTP client (and its connection pool) is reused
    across requests. Override this dependency in tests to inject fakes.

    Safe to cache since there is no state in the Aerobotics client or detector
    """
    return TreeService(
        aerobotics=AeroboticsClient(),
        detector=DetectorImpl(settings.row_spacing_threshold_multiplier),
    )


@router.get("/{orchard_id}/missing-trees", response_model=MissingTreesResponse)
def get_missing_trees(
    orchard_id: int,
    service: TreeService = Depends(build_tree_service),
) -> MissingTreesResponse:
    """Detect estimated positions of missing trees for an orchard's latest survey.

    Failures are converted to ``{"error": "..."}`` by the app-level exception
    handlers registered in ``api.main``.
    """
    return service.detect_missing_trees(orchard_id)
