from collections.abc import Iterator

import httpx
from loguru import logger

from api.clients.aerobotics import (
    Aerobotics,
    Survey,
    SurveyNotFoundError,
    Tree,
    TreeSurveysNotFoundError,
    UpstreamAuthError,
)
from api.core.config import settings


class AeroboticsClient(Aerobotics):
    """HTTP-backed implementation of the Aerobotics interface."""

    def __init__(self):
        self._client = httpx.Client(
            base_url=settings.aerobotics_base_url,
            headers={
                "Authorization": f"Bearer {settings.aerobotics_api_token}",
                "Content-Type": "application/json",
            },
        )

    @staticmethod
    def _check_auth(response: httpx.Response) -> None:
        # A 401 means the Aerobotics API rejected our token. Translate it into a
        # domain error here so it never surfaces to our callers as a 401.
        if response.status_code == 401:
            logger.error("Aerobotics API rejected credentials (401)")
            raise UpstreamAuthError()

    def get_latest_survey(self, orchard_id: int) -> Survey | None:
        response = self._client.get(
            "/surveys/",
            params={"orchard_id": orchard_id, "limit": 100},
        )
        self._check_auth(response)
        if response.status_code == 404:
            logger.error("survey not found for orchard with ID {}", orchard_id)
            raise SurveyNotFoundError(orchard_id)

        response.raise_for_status()
        surveys = response.json()["results"]
        if not surveys:
            logger.error("survey not found for orchard with ID {}", orchard_id)
            raise SurveyNotFoundError(orchard_id)

        # choose entry with greatest date
        latest = max(surveys, key=lambda s: s["date"])
        return Survey.from_json(latest)

    def get_all_tree_surveys(self, survey_id: int, *, limit: int = 100) -> Iterator[Tree]:
        offset = 0
        while True:
            response = self._client.get(
                f"/surveys/{survey_id}/tree_surveys/",
                params={"limit": limit, "offset": offset},
            )
            self._check_auth(response)
            if response.status_code == 404:
                logger.error("Tree surveys not available for survey {}", survey_id)
                raise TreeSurveysNotFoundError(survey_id)

            response.raise_for_status()
            data = response.json()
            for result in data["results"]:
                yield Tree.from_json(result)

            # A null `next` link means we've consumed the last page.
            if data["next"] is None:
                return
            offset += limit

