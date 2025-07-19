# app/routers/users.py

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND

from app import schemas, auth, crud, models
from app.database import get_db
from app.dependencies import get_current_user  # Your session/token logic

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ────────────────────────────────
# Register New User (GET + POST)
# ────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register", response_class=HTMLResponse)
def register_user(
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("applicant"),  # optional field: applicant or recruiter
    db: Session = Depends(get_db)
):
    user_data = schemas.UserCreate(
        fullname=fullname,
        email=email,
        password=password,
        role=role
    )

    try:
        user = auth.register_user(db, user_data)
    except HTTPException as e:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": e.detail
        })

    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)


# ────────────────────────────────
# View Profile (Optional)
# ────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
def user_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user
    })
