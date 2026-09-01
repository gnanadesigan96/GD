import logging

import httpx

from app.config import settings
from app.connectors.base import Connector, JobPosting

logger = logging.getLogger(__name__)

# Adzuna only publishes country-specific endpoints. Map free-text location
# hints (as typed into the profile's "target locations" field) to the
# country codes Adzuna supports, plus an optional "where" query refinement.
LOCATION_TO_ADZUNA = {
    "chennai": ("in", "Chennai"),
    "india": ("in", ""),
    "uk": ("gb", ""),
    "united kingdom": ("gb", ""),
    "britain": ("gb", ""),
    "germany": ("de", ""),
    "france": ("fr", ""),
    "netherlands": ("nl", ""),
    "spain": ("es", ""),
    "italy": ("it", ""),
    "poland": ("pl", ""),
}

# Adzuna has no generic "Europe" country. When the profile says "Europe"
# with no more specific country, fan out to this default set.
EUROPE_DEFAULT_COUNTRIES = ["gb", "de", "fr", "nl", "es", "it", "pl"]

# Countries Adzuna does not cover at all (e.g. UAE/Dubai) are silently
# skipped here; JoobleConnector picks those up instead.
UNSUPPORTED_HINTS = {"dubai", "uae", "united arab emirates"}


class AdzunaConnector(Connector):
    name = "adzuna"

    def is_configured(self) -> bool:
        return bool(settings.adzuna_app_id and settings.adzuna_app_key)

    def _countries_for_location(self, location: str) -> list[tuple[str, str]]:
        key = location.strip().lower()
        if key in UNSUPPORTED_HINTS:
            return []
        if key == "europe":
            return [(c, "") for c in EUROPE_DEFAULT_COUNTRIES]
        if key in LOCATION_TO_ADZUNA:
            return [LOCATION_TO_ADZUNA[key]]
        # Unknown free-text location: try it verbatim as a "where" filter
        # against India by default, since that's this tool's primary market.
        return [("in", location)]

    def search(self, keywords: str, location: str) -> list[JobPosting]:
        if not self.is_configured():
            return []

        results: list[JobPosting] = []
        for country, where in self._countries_for_location(location):
            params = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "what": keywords,
                "results_per_page": 20,
                "content-type": "application/json",
            }
            if where:
                params["where"] = where
            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
            try:
                resp = httpx.get(url, params=params, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("Adzuna search failed for %s/%s: %s", country, keywords, exc)
                continue

            for item in data.get("results", []):
                results.append(
                    JobPosting(
                        source=self.name,
                        external_id=str(item.get("id")),
                        title=item.get("title", "").strip(),
                        company=(item.get("company") or {}).get("display_name", ""),
                        location=(item.get("location") or {}).get("display_name", ""),
                        url=item.get("redirect_url", ""),
                        description=item.get("description", ""),
                        posted_at=item.get("created", ""),
                    )
                )
        return results
