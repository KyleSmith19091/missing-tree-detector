from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

import utm


class Aerobotics(ABC):
    """Abstract interface for the Aerobotics survey API."""

    @abstractmethod
    def get_latest_survey(self, orchard_id: int) -> Survey | None:
        """Return the most recent survey for an orchard, or None if there are none."""
        pass

    @abstractmethod
    def get_all_tree_surveys(self, survey_id: int, *, limit: int = 100) -> Iterator[Tree]:
        """Yield every tree in a survey, transparently paging through results."""
        pass


@dataclass
class Tree:
    """A single tree observation from the Aerobotics api."""

    # unique identifier
    id: str
    # latitude of centre of tree: assuming SA zone
    lat: float | None
    # longitude of centre of tree: assuming SA zone
    lng: float | None

    @classmethod
    def from_json(cls, data: dict) -> Tree:
        """Build a Tree from a raw tree-survey API record.

        Only the fields we model are read; unknown keys are ignored so the
        parser tolerates the API adding fields. lat/lng use .get() because the
        API may omit a location for a tree.
        """

        if data.get("lat") is None:
            raise ValueError("expected tree to have latitude value, but got None")

        if data.get("lng") is None:
            raise ValueError("expected tree to have longitude value, but got None")

        return cls(
            id=data["id"],
            lat=data.get("lat"),
            lng=data.get("lng"),
        )

    def get_utm_position(self) -> tuple[float, float] | None:
        """Project the tree's lat/lng into UTM coordinates.

        Returns (easting, northing, zone_number, zone_letter), or None if the
        tree has no location. UTM gives a metric grid that's convenient for
        distance/area math without the distortion of raw lat/lng.
        """
        if self.lat is None or self.lng is None:
            return None

        # determine UTM coordinates from longitude and latitude
        easting, northing, _, _ = utm.from_latlon(float(self.lat), float(self.lng))

        return easting, northing


@dataclass
class Survey:
    """An orchard survey (a single capture flight) from the Aerobotics api."""

    # unique identifier
    id: int
    # orchard this survey belongs to
    orchard_id: int
    # capture date, as returned by the API (ISO-8601 string)
    date: str

    @classmethod
    def from_json(cls, data: dict) -> Survey:
        """Build a Survey from a raw survey API record, ignoring unknown keys."""
        return cls(
            id=data["id"],
            orchard_id=data["orchard_id"],
            date=data["date"],
        )
