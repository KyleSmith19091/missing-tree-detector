from pydantic import BaseModel

from api.clients.aerobotics import Tree

__all__ = ["Tree", "MissingTree", "MissingTreesResponse"]


class MissingTree(BaseModel):
    """An estimated position of a tree that appears to be missing."""

    lat: float
    lng: float


class MissingTreesResponse(BaseModel):
    """Response for a missing-tree detection request."""

    missing_trees: list[MissingTree]
