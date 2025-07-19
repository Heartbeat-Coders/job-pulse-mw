# app/routers/dashboard.py

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.database import get_db
from app import crud, models
from app.dependencies import get_current_user  # You must create this
from typing import List

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "recruiter":
        jobs = db.query(models.Job).filter(models.Job.created_by == current_user.id).all()
        job_ids = [job.id for job in jobs]
        applications = (
            db.query(models.Application)
            .filter(models.Application.job_id.in_(job_ids))
            .order_by(models.Application.created_at.desc())
            .all()
        )
        return templates.TemplateResponse("recruiter_dashboard.html", {
            "request": request,
            "user": current_user,
            "jobs": jobs,
            "applications": applications
        })

    elif current_user.role == "admin":
        all_jobs = db.query(models.Job).all()
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "user": current_user,
            "jobs": all_jobs
        })

    else:
        return templates.TemplateResponse("applicant_dashboard.html", {
            "request": request,
            "user": current_user
        })
