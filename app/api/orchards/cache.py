import threading

from api.orchards.model import MissingTree


class MissingTreesCache:
    """In-process cache of missing-tree detection results.

    Keyed by (survey_id, orchard_id) so a result is only reused for the exact
    survey it was computed from. When a newer survey appears for an orchard the
    key changes (cache miss), and the previous survey's entry for that orchard
    is evicted so the cache doesn't accumulate stale results.
    """

    def __init__(self):
        self._cache: dict[str, list[MissingTree]] = {}
        self._orchard_key: dict[int, str] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(survey_id: int, orchard_id: int) -> str:
        return f"{survey_id}:{orchard_id}"

    def get(self, survey_id: int, orchard_id: int) -> list[MissingTree] | None:
        """Return cached missing trees for this survey, or None on a miss."""
        return self._cache.get(self._key(survey_id, orchard_id))

    def set(
        self, survey_id: int, orchard_id: int, missing_trees: list[MissingTree]
    ) -> None:
        """Store results for a survey, evicting any older entry for the orchard."""
        key = self._key(survey_id, orchard_id)
        with self._lock:
            previous_key = self._orchard_key.get(orchard_id)
            if previous_key is not None and previous_key != key:
                # A newer survey supersedes the old one — drop the stale entry.
                self._cache.pop(previous_key, None)
            self._cache[key] = missing_trees
            self._orchard_key[orchard_id] = key
