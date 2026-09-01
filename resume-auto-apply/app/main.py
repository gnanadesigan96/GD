import json
import logging
import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors import ALL_CONNECTORS
from app.db import get_db, init_db
from app.docgen import generate_cover_letter_docx, generate_resume_docx
from app.matcher import location_matches, matches_any_role, score_job
from app.models import STATUS_CHOICES, Application, Job, Profile
from app.resume_parser import extract_text
from app.tailor import tailor_resume

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Resume Auto-Apply Assistant")

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def on_startup():
    init_db()


def get_profile(db: Session) -> Profile:
    profile = db.get(Profile, 1)
    if not profile:
        profile = Profile(id=1)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@app.get("/")
def dashboard(request: Request, status: str = "", db: Session = Depends(get_db)):
    profile = get_profile(db)
    query = db.query(Job).order_by(Job.score.desc(), Job.fetched_at.desc())
    jobs = query.all()
    if status:
        jobs = [j for j in jobs if j.application and j.application.status == status]
    connector_status = {c.name: c.is_configured() for c in ALL_CONNECTORS}
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "profile": profile,
            "jobs": jobs,
            "status_choices": STATUS_CHOICES,
            "selected_status": status,
            "connector_status": connector_status,
            "resume_ready": bool(profile.resume_raw_text),
        },
    )


@app.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db)):
    profile = get_profile(db)
    connector_status = {c.name: c.is_configured() for c in ALL_CONNECTORS}
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "profile": profile,
            "connector_status": connector_status,
            "has_api_key": bool(settings.anthropic_api_key),
            "saved": False,
        },
    )


@app.post("/settings")
async def save_settings(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    experience_years: int = Form(8),
    target_roles: str = Form(""),
    target_locations: str = Form(""),
    resume_file: UploadFile | None = File(None),
):
    profile = get_profile(db)
    profile.full_name = full_name
    profile.email = email
    profile.phone = phone
    profile.experience_years = experience_years
    profile.target_roles = target_roles
    profile.target_locations = target_locations

    if resume_file is not None and resume_file.filename:
        safe_name = Path(resume_file.filename).name
        dest = settings.resumes_path / safe_name
        with dest.open("wb") as f:
            shutil.copyfileobj(resume_file.file, f)
        profile.resume_filename = safe_name
        profile.resume_raw_text = extract_text(dest)

    db.commit()
    connector_status = {c.name: c.is_configured() for c in ALL_CONNECTORS}
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "profile": profile,
            "connector_status": connector_status,
            "has_api_key": bool(settings.anthropic_api_key),
            "saved": True,
        },
    )


@app.post("/jobs/fetch")
def fetch_jobs(db: Session = Depends(get_db)):
    profile = get_profile(db)
    roles = profile.roles_list()
    locations = profile.locations_list()

    fetched = 0
    for connector in ALL_CONNECTORS:
        if not connector.is_configured():
            continue
        for role in roles:
            for location in locations:
                postings = connector.search(keywords=role, location=location)
                for posting in postings:
                    matched_role = matches_any_role(posting.title, roles) or role
                    if not location_matches(posting.location, locations):
                        continue

                    existing = (
                        db.query(Job)
                        .filter_by(source=posting.source, external_id=posting.external_id)
                        .one_or_none()
                    )
                    job = existing or Job(source=posting.source, external_id=posting.external_id)
                    job.title = posting.title
                    job.company = posting.company
                    job.location = posting.location
                    job.url = posting.url
                    job.description = posting.description
                    job.matched_role = matched_role
                    job.posted_at = posting.posted_at
                    job.score = score_job(profile.resume_raw_text, posting.title, posting.description)
                    if not existing:
                        db.add(job)
                        fetched += 1
        db.commit()

    logger.info("Fetched %d new jobs", fetched)
    return RedirectResponse(url="/", status_code=303)


@app.get("/jobs/{job_id}")
def job_detail(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    profile = get_profile(db)
    tailored = None
    if job.application and job.application.tailored_summary:
        tailored = json.loads(job.application.tailored_summary)
    return templates.TemplateResponse(
        "job_detail.html",
        {
            "request": request,
            "job": job,
            "profile": profile,
            "tailored": tailored,
            "status_choices": STATUS_CHOICES,
            "has_resume": bool(profile.resume_raw_text),
            "has_api_key": bool(settings.anthropic_api_key),
        },
    )


@app.post("/jobs/{job_id}/tailor")
def tailor(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    profile = get_profile(db)

    result = tailor_resume(profile, job)

    application = job.application or Application(job_id=job.id)
    application.tailored_summary = json.dumps(result)
    application.status = "tailored" if application.status == "new" else application.status

    safe_title = "".join(c if c.isalnum() else "_" for c in f"{job.company}_{job.title}")[:80]
    resume_path = settings.generated_path / f"resume_{job.id}_{safe_title}.docx"
    cover_path = settings.generated_path / f"cover_letter_{job.id}_{safe_title}.docx"

    generate_resume_docx(profile, result, resume_path)
    generate_cover_letter_docx(profile, job, result.get("cover_letter", ""), cover_path)

    application.tailored_resume_path = str(resume_path)
    application.tailored_cover_letter_path = str(cover_path)

    if not job.application:
        db.add(application)
    db.commit()

    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/status")
def update_status(job_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    application = job.application or Application(job_id=job.id)
    application.status = status
    if not job.application:
        db.add(application)
    db.commit()
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.get("/applications/{job_id}/resume")
def download_resume(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    path = job.application.tailored_resume_path
    return FileResponse(path, filename=Path(path).name)


@app.get("/applications/{job_id}/cover-letter")
def download_cover_letter(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    path = job.application.tailored_cover_letter_path
    return FileResponse(path, filename=Path(path).name)
