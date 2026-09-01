import re

# Synonyms broaden the title match beyond the literal role name typed into
# the profile, since job titles for the same role vary a lot by company.
ROLE_SYNONYMS = {
    "product specialist": ["product specialist", "product consultant", "product analyst", "product support specialist"],
    "business analyst": ["business analyst", "business systems analyst", "ba ", "requirements analyst"],
    "customer success manager": ["customer success manager", "csm", "client success manager", "customer success lead"],
}


def _keywords_for_role(role: str) -> list[str]:
    role_lower = role.strip().lower()
    return ROLE_SYNONYMS.get(role_lower, [role_lower])


def matches_any_role(title: str, roles: list[str]) -> str:
    """Returns the profile role that matched this job title, or '' if none did."""
    title_lower = title.lower()
    for role in roles:
        for kw in _keywords_for_role(role):
            if kw.strip() and kw.strip() in title_lower:
                return role
    return ""


def location_matches(job_location: str, target_locations: list[str]) -> bool:
    if not target_locations:
        return True
    job_location_lower = job_location.lower()
    for loc in target_locations:
        loc_lower = loc.strip().lower()
        if loc_lower == "europe":
            # Job boards rarely say "Europe" verbatim; if the search already
            # scoped the query to a European country, trust it.
            return True
        if loc_lower and loc_lower in job_location_lower:
            return True
    return "remote" in job_location_lower


_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z+.#]{2,}")


def score_job(resume_text: str, job_title: str, job_description: str) -> float:
    """Cheap keyword-overlap score between the resume and the job, used only
    to rank/sort matches -- not a hard filter."""
    resume_words = set(w.lower() for w in _WORD_RE.findall(resume_text))
    job_words = _WORD_RE.findall(f"{job_title} {job_description}")
    if not job_words:
        return 0.0
    overlap = sum(1 for w in job_words if w.lower() in resume_words)
    return round(overlap / len(job_words) * 100, 2)
