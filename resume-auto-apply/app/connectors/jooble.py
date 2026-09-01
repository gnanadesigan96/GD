import logging

import httpx

from app.config import settings
from app.connectors.base import Connector, JobPosting

logger = logging.getLogger(__name__)


class JoobleConnector(Connector):
    """Jooble has much broader country coverage than Adzuna (incl. UAE/Dubai),
    at the cost of a less structured response. Used as the primary source for
    Dubai/UAE and as a supplement everywhere else."""

    name = "jooble"

    def is_configured(self) -> bool:
        return bool(settings.jooble_api_key)

    def search(self, keywords: str, location: str) -> list[JobPosting]:
        if not self.is_configured():
            return []

        url = f"https://jooble.org/api/{settings.jooble_api_key}"
        payload = {"keywords": keywords, "location": location}
        try:
            resp = httpx.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Jooble search failed for %s/%s: %s", location, keywords, exc)
            return []

        results = []
        for item in data.get("jobs", []):
            external_id = item.get("id") or item.get("link", "")
            results.append(
                JobPosting(
                    source=self.name,
                    external_id=str(external_id),
                    title=(item.get("title") or "").strip(),
                    company=item.get("company", ""),
                    location=item.get("location", ""),
                    url=item.get("link", ""),
                    description=item.get("snippet", ""),
                    posted_at=item.get("updated", ""),
                )
            )
        return results
