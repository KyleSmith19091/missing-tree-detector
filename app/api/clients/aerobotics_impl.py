from collections.abc import Iterator

import httpx
from loguru import logger

from api.clients.aerobotics import Aerobotics, Survey, Tree
from api.core.config import settings


class AeroboticsClient(Aerobotics):
    """HTTP-backed implementation of the Aerobotics interface."""

    def __init__(self):
        # Reused across requests so the auth headers and base URL are applied
        # to every call and the connection pool is shared.
        self._client = httpx.Client(
            base_url=settings.aerobotics_base_url,
            headers={
                "Authorization": f"Bearer {settings.aerobotics_api_token}",
                "Content-Type": "application/json",
            },
        )

    def get_latest_survey(self, orchard_id: int) -> Survey | None:
        response = self._client.get(
            "/surveys/",
            params={"orchard_id": orchard_id, "limit": 100},
        )
        response.raise_for_status()
        surveys = response.json()["results"]
        if not surveys:
            return None
        # The API doesn't guarantee ordering, so pick the newest by date rather
        # than assuming the first/last result is the latest.
        latest = max(surveys, key=lambda s: s["date"])
        return Survey.from_json(latest)

    def get_all_tree_surveys(self, survey_id: int, *, limit: int = 100) -> Iterator[Tree]:
        # Walk the paginated endpoint offset-by-offset, yielding trees as we go
        # so callers can stream results without loading the whole survey.
        offset = 0
        while True:
            response = self._client.get(
                f"/surveys/{survey_id}/tree_surveys/",
                params={"limit": limit, "offset": offset},
            )
            # Some surveys are organised by row segments rather than individual
            # trees; those return 404 here. Treat that as "no trees" instead of
            # an error so callers get an empty iterator.
            if response.status_code == 404:
                logger.warning("Tree surveys not available (survey may use row segments instead)")
                return
            response.raise_for_status()
            data = response.json()
            for result in data["results"]:
                yield Tree.from_json(result)
            # A null `next` link means we've consumed the last page.
            if data["next"] is None:
                return
            offset += limit
