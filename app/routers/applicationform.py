# app/routers/application_form.py

from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from uuid import UUID
import os

from app import crud, models
from app.database import get_db
from app.dependencies import get_current_user
from app.openai_utils import score_cv_with_openai

from starlette.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = "static/uploads"

# GET application form
@router.get("/apply/{job_id}", response_class=HTMLResponse)
def show_application_form(job_id: UUID, request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    job = crud.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("application_form.html", {
        "request": request,
        "user": user,
        "job": job
    })

# POST application
@router.post("/apply/{job_id}", response_class=HTMLResponse)
async def submit_application(
    job_id: UUID,
    request: Request,
    cover_letter: str = Form(...),
    cv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    job = crud.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Save uploaded CV file
    filename = f"{user.id}_{job_id}_{cv_file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        content = await cv_file.read()
        f.write(content)

    cv_text = content.decode(errors="ignore")  # crude fallback if plain text

    # Score the CV using OpenAI (optional)
    result = score_cv_with_openai(cv_text=cv_text, job_description=job.description)

    # Create application in DB
    app = crud.apply_to_job(
        db=db,
        user_id=user.id,
        job_id=job_id,
        cv_filename=filename,
        cover_letter=cover_letter
    )

    # Update score/reason
    if app and result:
        crud.update_application_status(
            db=db,
            application_id=app.id,
            status="submitted",
            score=result.get("score"),
            reason=result.get("reason")
        )

    return RedirectResponse(url="/status", status_code=HTTP_302_FOUND)
