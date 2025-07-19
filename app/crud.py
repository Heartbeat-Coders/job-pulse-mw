# app/crud.py

from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.models import Application, Job, User
from app.schemas import JobCreate


# ───────────────────────────
# USER CRUD
# ───────────────────────────

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user(db: Session, user_id: uuid.UUID):
    return db.query(User).filter(User.id == user_id).first()

# ───────────────────────────
# JOB CRUD
# ───────────────────────────

def create_job(db: Session, job_data: JobCreate, recruiter_id: uuid.UUID):
    job = Job(
        title=job_data.title,
        description=job_data.description,
        deadline=job_data.deadline,
        created_by=recruiter_id,
        created_at=datetime.now()
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def get_all_jobs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Job).offset(skip).limit(limit).all()

def get_job_by_id(db: Session, job_id: uuid.UUID):
    return db.query(Job).filter(Job.id == job_id).first()

# ───────────────────────────
# APPLICATION CRUD
# ───────────────────────────

def apply_to_job(db: Session, user_id: uuid.UUID, job_id: uuid.UUID, cv_filename: str, cover_letter: str):
    application = Application(
        user_id=user_id,
        job_id=job_id,
        status="submitted",
        cv_filename=cv_filename,
        reason=None,
        score=None,
        created_at=datetime.utcnow()
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application

def get_user_applications(db: Session, user_id: uuid.UUID):
    return (
        db.query(Application)
        .join(Job)
        .filter(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
        .all()
    )

def get_applications_for_job(db: Session, job_id: uuid.UUID):
    return (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .order_by(Application.score.desc().nullslast())
        .all()
    )

def update_application_status(db: Session, application_id: uuid.UUID, status: str, score: int = None, reason: str = None):
    application = db.query(Application).filter(Application.id == application_id).first()
    if application:
        application.status = status
        application.score = score
        application.reason = reason
        db.commit()
        db.refresh(application)
    return application
