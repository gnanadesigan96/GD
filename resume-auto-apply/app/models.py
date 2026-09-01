import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


class Profile(Base):
    """Single-row table holding the job seeker's info. id is always 1."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    experience_years: Mapped[int] = mapped_column(Integer, default=8)
    # Comma-separated free text, e.g. "Product Specialist, Business Analyst, Customer Success Manager"
    target_roles: Mapped[str] = mapped_column(Text, default="Product Specialist, Business Analyst, Customer Success Manager")
    # Comma-separated free text, e.g. "Chennai, India, Dubai, UAE, Germany, UK, Netherlands"
    target_locations: Mapped[str] = mapped_column(Text, default="Chennai, India, Dubai, UAE, Europe")
    resume_filename: Mapped[str] = mapped_column(String(300), default="")
    resume_raw_text: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    def roles_list(self) -> list[str]:
        return [r.strip() for r in self.target_roles.split(",") if r.strip()]

    def locations_list(self) -> list[str]:
        return [l.strip() for l in self.target_locations.split(",") if l.strip()]


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_job_source_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(300))
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(300), default="")
    location: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    matched_role: Mapped[str] = mapped_column(String(200), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    posted_at: Mapped[str] = mapped_column(String(50), default="")
    fetched_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)

    application: Mapped["Application"] = relationship(back_populates="job", uselist=False)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="new")
    tailored_resume_path: Mapped[str] = mapped_column(String(500), default="")
    tailored_cover_letter_path: Mapped[str] = mapped_column(String(500), default="")
    tailored_summary: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    job: Mapped["Job"] = relationship(back_populates="application")


STATUS_CHOICES = ["new", "tailored", "ready_to_apply", "applied", "interview", "rejected", "offer"]
