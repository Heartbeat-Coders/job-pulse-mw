# # app/routers/jobs.py

# from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
# from fastapi.responses import HTMLResponse, RedirectResponse
# from sqlalchemy.orm import Session
# from uuid import UUID
# from datetime import datetime

# from app import crud, models, schemas
# from app.database import get_db
# # from app.dependencies import get_current_user
# # from app.openai_utils import score_cv_with_openai

# from starlette.templating import Jinja2Templates
# from starlette.status import HTTP_302_FOUND
# import os

# router = APIRouter()
# templates = Jinja2Templates(directory="app/templates")

# UPLOAD_DIR = "static/uploads"


# # ───────────────────────────────────────
# # GET ALL JOBS (Applicant & Public View)
# # ───────────────────────────────────────

# @router.get("/jobs", response_class=HTMLResponse)
# def list_jobs(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
#     jobs = crud.get_all_jobs(db)
#     return templates.TemplateResponse("job_listings.html", {
#         "request": request,
#         "user": user,
#         "jobs": jobs
#     })


# # ───────────────────────────────────────
# # RECRUITER: POST NEW JOB (GET + POST)
# # ───────────────────────────────────────

# @router.get("/jobs/post", response_class=HTMLResponse)
# def post_job_form(request: Request, user: models.User = Depends(get_current_user)):
#     if user.role != "recruiter":
#         raise HTTPException(status_code=403, detail="Access denied")
#     return templates.TemplateResponse("job_register.html", {"request": request, "user": user})


# @router.post("/jobs/post", response_class=HTMLResponse)
# def post_job(
#     request: Request,
#     title: str = Form(...),
#     description: str = Form(...),
#     deadline: str = Form(...),
#     db: Session = Depends(get_db),
#     user: models.User = Depends(get_current_user)
# ):
#     if user.role != "recruiter":
#         raise HTTPException(status_code=403, detail="Only recruiters can post jobs")

#     job_data = schemas.JobCreate(
#         title=title,
#         description=description,
#         deadline=datetime.strptime(deadline, "%Y-%m-%d").date()
#     )
#     crud.create_job(db=db, job_data=job_data, recruiter_id=user.id)
#     return RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)


# # ───────────────────────────────────────
# # APPLICANT: APPLY TO JOB (GET + POST)
# # ───────────────────────────────────────

# @router.get("/apply/{job_id}", response_class=HTMLResponse)
# def application_form(job_id: UUID, request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
#     job = crud.get_job_by_id(db, job_id)
#     if not job:
#         raise HTTPException(status_code=404, detail="Job not found")
#     return templates.TemplateResponse("application_form.html", {"request": request, "job": job, "user": user})


# @router.post("/apply/{job_id}")
# async def submit_application(
#     job_id: UUID,
#     cover_letter: str = Form(...),
#     cv_file: UploadFile = File(...),
#     db: Session = Depends(get_db),
#     user: models.User = Depends(get_current_user)
# ):
#     # Save uploaded file
#     filename = f"{user.id}_{job_id}_{cv_file.filename}"
#     file_path = os.path.join(UPLOAD_DIR, filename)

#     with open(file_path, "wb") as f:
#         content = await cv_file.read()
#         f.write(content)

#     # Read CV text from file (assume it's plain text or PDF text already extracted)
#     cv_text = content.decode(errors="ignore")

#     # Get job description
#     job = crud.get_job_by_id(db, job_id)
#     job_description = job.description

#     # Score the CV
#     result = score_cv_with_openai(cv_text=cv_text, job_description=job_description)

#     # Save the application
#     crud.apply_to_job(
#         db=db,
#         user_id=user.id,
#         job_id=job_id,
#         cv_filename=filename,
#         cover_letter=cover_letter
#     )

#     # Optional: update with AI score
#     app = db.query(models.Application).filter(
#         models.Application.user_id == user.id,
#         models.Application.job_id == job_id
#     ).first()

#     if app:
#         app.score = result.get("score")
#         app.reason = result.get("reason")
#         db.commit()

#     return RedirectResponse(url="/status", status_code=HTTP_302_FOUND)
