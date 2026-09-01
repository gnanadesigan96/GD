import json

from anthropic import Anthropic

from app.config import settings
from app.models import Job, Profile

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are a resume-tailoring assistant. You rewrite a candidate's \
existing resume to better match one specific job posting.

Hard rules:
- Never invent employers, titles, dates, degrees, certifications, or metrics that \
are not present in the source resume. You may rephrase, reorder, and re-emphasize \
existing content, and quantify things ONLY if a number is already implied in the \
source text.
- Prefer wording and keywords that appear in the job description, when they \
truthfully describe experience already in the source resume.
- Keep it ATS-friendly: plain language, no tables, no special characters.
- Output ONLY valid JSON matching the schema given in the user message. No prose, \
no markdown code fences.
"""

JSON_SCHEMA_HINT = """{
  "headline": "string, a one-line professional title for this role",
  "summary": "string, 3-5 sentence professional summary tailored to this job",
  "skills": ["string", "..."],
  "experience": [
    {"title": "string", "company": "string", "dates": "string", "bullets": ["string", "..."]}
  ],
  "education": ["string", "..."],
  "cover_letter": "string, a 3-4 paragraph cover letter addressed generically (no company contact name unless known), referencing the job title and company"
}"""


def tailor_resume(profile: Profile, job: Job) -> dict:
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file to enable resume tailoring."
        )

    client = Anthropic(api_key=settings.anthropic_api_key)

    user_message = f"""Source resume (candidate has {profile.experience_years} years of experience):
---
{profile.resume_raw_text}
---

Target job:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
---
{job.description}
---

Return JSON with exactly this shape:
{JSON_SCHEMA_HINT}
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    text = _strip_code_fence(text)
    return json.loads(text)


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return text
