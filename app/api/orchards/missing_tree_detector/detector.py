from typing import Tuple, List
from abc import ABC,abstractmethod
from dataclasses import dataclass

import utm
import numpy as np

class Detector(ABC):
    @abstractmethod
    def detect_missing_trees(
        self,
        tree_positions: List["TreePosition"],
        utm_zone_number: int,
        utm_zone_letter: str,
    ) -> List[dict]:
        """Estimate positions of missing trees.

        Returns a list of {"lat": float, "lng": float} dicts for each
        estimated missing tree.
        """
        pass

@dataclass
class TreePosition:
    lat: float
    lng: float
    
    def as_utm(self) -> Tuple[float, float]:
        easting, northing, _, _ = utm.from_latlon(self.lat, self.lng)
        return (easting, northing)