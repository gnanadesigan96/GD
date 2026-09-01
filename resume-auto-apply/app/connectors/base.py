from dataclasses import dataclass


@dataclass
class JobPosting:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    posted_at: str = ""


class Connector:
    name = "base"

    def is_configured(self) -> bool:
        raise NotImplementedError

    def search(self, keywords: str, location: str) -> list[JobPosting]:
        """Return normalized job postings for one (keywords, location) query.

        Must never raise on a single failed request beyond what the caller can
        reasonably surface as a warning; return [] on error.
        """
        raise NotImplementedError
