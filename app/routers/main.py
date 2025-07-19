# app/routes/main.py
# app/routes/main.py - Updated sections for CV upload

import os
import shutil
from datetime import datetime, timedelta
import uuid
from fastapi import APIRouter, Form, HTTPException, Request, Depends, status, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.security import HTTPBearer
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
import aiofiles

from app.database import get_db
from app.auth import authenticate_user, create_access_token, get_current_user, register_user
from app.models import Application, Job, User
from app.schemas import UserCreate

security = HTTPBearer()
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads/cvs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed file extensions and maximum file size
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_cv_file(file: UploadFile) -> bool:
    """Validate uploaded CV file"""
    if not file.filename:
        return False
    
    # Check file extension
    file_extension = '.' + file.filename.split('.')[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        return False
    
    return True

def generate_unique_filename(original_filename: str, user_id: str) -> str:
    """Generate unique filename for CV"""
    file_extension = '.' + original_filename.split('.')[-1].lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{user_id}_{timestamp}{file_extension}"
    return unique_filename

async def save_cv_file(file: UploadFile, filename: str) -> str:
    """Save CV file to uploads directory"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    async with aiofiles.open(file_path, 'wb') as buffer:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 5MB)")
        await buffer.write(content)
    
    return file_path




@router.post("/api/applications/{application_id}/score")
async def score_application(
    application_id: str,
    score_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Score an application (1-5)"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can score applications")
    
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    # Find application and verify recruiter owns the job
    application = db.query(Application).join(Job).filter(
        Application.id == application_uuid,
        Job.created_by == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found or access denied")
    
    # Validate score (1-5)
    score = score_data.get("score")
    if score is None or not (1 <= score <= 5):
        raise HTTPException(status_code=400, detail="Score must be between 1 and 5")
    
    # Update score
    application.score = score
    
    try:
        db.commit()
        return {"message": "Score updated successfully", "score": score}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating score")
    
    
@router.get("/recruiter/dashboard", response_class=HTMLResponse)
async def recruiter_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Recruiter dashboard with sidebar navigation"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Access denied. Recruiters only.")
    
    # Get stats for the dashboard
    total_jobs = db.query(Job).filter(Job.created_by == current_user.id).count()
    total_applications = db.query(Application).join(Job).filter(
        Job.created_by == current_user.id
    ).count()
    
    # Get recent applications
    applications = db.query(Application).join(Job).join(User).filter(
        Job.created_by == current_user.id
    ).order_by(Application.created_at.desc()).limit(10).all()
    
    # Format application data
    app_data = [{
        "id": str(app.id),
        "status": app.status,
        "score": app.score,
        "created_at": app.created_at.isoformat(),
        "user": {
            "id": str(app.user.id),
            "first_name": app.user.first_name,
            "last_name": app.user.last_name
        },
        "job": {
            "id": str(app.job.id),
            "title": app.job.title
        }
    } for app in applications]
    
    return templates.TemplateResponse(
        "recruiter_dashboard.html",
        {
            "request": request,
            "user": current_user,
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "applications": app_data
        }
    )

@router.get("/recruiter/applications", response_class=HTMLResponse)
async def recruiter_applications_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List of all applications for recruiter to review"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Access denied. Recruiters only.")
    
    # Get all applications for jobs created by this recruiter
    applications = db.query(Application).join(Job).join(User).filter(
        Job.created_by == current_user.id
    ).order_by(Application.created_at.desc()).all()
    
    # Format application data
    app_data = [{
        "id": str(app.id),
        "status": app.status,
        "score": app.score,
        "created_at": app.created_at.isoformat(),
        "user": {
            "id": str(app.user.id),
            "first_name": app.user.first_name,
            "last_name": app.user.last_name,
            "email": app.user.email,
            "phone": app.user.phone
        },
        "job": {
            "id": str(app.job.id),
            "title": app.job.title,
            "description": app.job.description
        }
    } for app in applications]
    
    return templates.TemplateResponse(
        "recruiter_applications.html",
        {
            "request": request,
            "user": current_user,
            "applications": app_data
        }
    )

@router.get("/api/recruiter/applications")
async def get_recruiter_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API endpoint to get applications for the recruiter"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can access applications")
    
    applications = db.query(Application).join(Job).join(User).filter(
        Job.created_by == current_user.id
    ).order_by(Application.created_at.desc()).all()
    
    return [{
        "id": str(app.id),
        "status": app.status,
        "score": app.score,
        "created_at": app.created_at.isoformat(),
        "user": {
            "id": str(app.user.id),
            "first_name": app.user.first_name,
            "last_name": app.user.last_name
        },
        "job": {
            "id": str(app.job.id),
            "title": app.job.title
        }
    } for app in applications]

@router.get("/recruiter/applications/{application_id}", response_class=HTMLResponse)
async def view_application_details(
    application_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can access this page")
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    application = db.query(Application).join(Job).join(User).filter(
        Application.id == application_uuid,
        Job.created_by == current_user.id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found or access denied")
    app_data = {
        "id": str(application.id),
        "status": application.status,
        "score": application.score,
        "reason": application.reason,
        "created_at": application.created_at.strftime("%Y-%m-%d %H:%M"),
        "cv_filename": application.cv_filename,
        "has_cv": bool(application.cv_filename),
        "user": {
            "id": str(application.user.id),
            "name": f"{application.user.first_name} {application.user.last_name}",
            "email": application.user.email,
            "phone": application.user.phone
        },
        "job": {
            "id": str(application.job.id),
            "title": application.job.title
        }
    }
    return templates.TemplateResponse(
        "recruiter_application_detail.html",
        {"request": request, "application": app_data, "user": current_user}
    )

# Updated application submission endpoint
@router.post("/apply/{job_id}")
async def submit_application(
    job_id: str,
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    job_position: str = Form(...),
    cover_letter: str = Form(...),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit job application with CV upload"""
    
    # Validate job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if user already applied for this job
    existing_application = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.job_id == job.id
    ).first()
    
    if existing_application:
        raise HTTPException(status_code=400, detail="You have already applied for this job")
    
    # Validate CV file
    if not validate_cv_file(cv):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file format. Please upload PDF, DOC, or DOCX files only."
        )
    
    # Generate unique filename and save CV
    try:
        unique_filename = generate_unique_filename(cv.filename, str(current_user.id))
        await save_cv_file(cv, unique_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error uploading CV file")
    
    # Create application record
    try:
        application = Application(
            user_id=current_user.id,
            job_id=job.id,
            status="submitted",
            reason=cover_letter,
            cv_filename=unique_filename,
            score=None
        )
        db.add(application)
        db.commit()
        db.refresh(application)
        
        return RedirectResponse(url="/dashboard?success=application_submitted", status_code=303)
        
    except Exception as e:
        # If database operation fails, try to delete the uploaded file
        try:
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        db.rollback()
        raise HTTPException(status_code=500, detail="Error submitting application")

@router.get("/recruiter/applications/{application_id}/details", response_class=HTMLResponse)
async def view_application_details(
    application_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can access this page")
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    application = db.query(Application).join(Job).join(User).filter(
        Application.id == application_uuid,
        Job.created_by == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found or access denied")
    
    app_data = {
        "id": str(application.id),
        "status": application.status,
        "score": application.score,
        "reason": application.reason,
        "created_at": application.created_at.strftime("%Y-%m-%d %H:%M"),
        "cv_filename": application.cv_filename,
        "has_cv": bool(application.cv_filename),
        "user": {
            "id": str(application.user.id),
            "name": f"{application.user.first_name} {application.user.last_name}",
            "email": application.user.email,
            "phone": application.user.phone
        },
        "job": {
            "id": str(application.job.id),
            "title": application.job.title
        }
    }
    return templates.TemplateResponse(
        "recruiter_application_detail.html",
        {"request": request, "application": app_data, "user": current_user}
    )

# Download CV endpoint
@router.get("/applications/{application_id}/cv")
async def download_cv(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download CV file for an application"""
    
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    # Find application
    application = db.query(Application).join(Job).filter(
        Application.id == application_uuid
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check permissions - only applicant, job creator, or admin can download
    if not (
        current_user.id == application.user_id or  # Applicant
        current_user.id == application.job.created_by or  # Job creator (recruiter)
        current_user.role == "admin"  # Admin
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not application.cv_filename:
        raise HTTPException(status_code=404, detail="No CV file found for this application")
    
    file_path = os.path.join(UPLOAD_DIR, application.cv_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="CV file not found on server")
    
    # Generate download filename
    user_name = f"{application.user.first_name}_{application.user.last_name}"
    job_title = application.job.title.replace(" ", "_")
    file_extension = '.' + application.cv_filename.split('.')[-1]
    download_filename = f"CV_{user_name}_{job_title}{file_extension}"
    
    return FileResponse(
        file_path,
        filename=download_filename,
        media_type='application/octet-stream'
    )

# Get application details with CV info
@router.get("/api/applications/{application_id}")
async def get_application_details(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed application information"""
    
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    # Find application with related data
    application = db.query(Application).join(Job).join(User).filter(
        Application.id == application_uuid
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check permissions
    if not (
        current_user.id == application.user_id or
        current_user.id == application.job.created_by or
        current_user.role == "admin"
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": str(application.id),
        "status": application.status,
        "score": application.score,
        "reason": application.reason,
        "cv_filename": application.cv_filename,
        "has_cv": bool(application.cv_filename),
        "cv_download_url": f"/applications/{application.id}/cv" if application.cv_filename else None,
        "created_at": application.created_at.isoformat(),
        "user": {
            "id": str(application.user.id),
            "first_name": application.user.first_name,
            "last_name": application.user.last_name,
            "email": application.user.email,
            "phone": application.user.phone
        },
        "job": {
            "id": str(application.job.id),
            "title": application.job.title,
            "description": application.job.description,
            "deadline": application.job.deadline.isoformat()
        }
    }

# Delete application (cleanup CV file)
@router.delete("/applications/{application_id}")
async def delete_application_with_cv(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete application and associated CV file"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    application = db.query(Application).filter(Application.id == application_uuid).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Delete CV file if exists
    if application.cv_filename:
        file_path = os.path.join(UPLOAD_DIR, application.cv_filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not delete CV file {file_path}: {e}")
    
    # Delete application record
    try:
        db.delete(application)
        db.commit()
        return {"message": "Application deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting application")

# Bulk download CVs for a job (recruiter feature)
@router.get("/jobs/{job_id}/cvs/download")
async def bulk_download_cvs(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a ZIP file with all CVs for a specific job"""
    import zipfile
    import tempfile
    
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    # Verify job exists and user has permission
    job = db.query(Job).filter(
        Job.id == job_uuid,
        Job.created_by == current_user.id
    ).first()
    
    if not job and current_user.role != "admin":
        raise HTTPException(status_code=404, detail="Job not found or access denied")
    
    if not job:
        job = db.query(Job).filter(Job.id == job_uuid).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    
    # Get all applications with CVs for this job
    applications = db.query(Application).join(User).filter(
        Application.job_id == job_uuid,
        Application.cv_filename.isnot(None)
    ).all()
    
    if not applications:
        raise HTTPException(status_code=404, detail="No CV files found for this job")
    
    # Create temporary ZIP file
    temp_dir = tempfile.mkdtemp()
    zip_filename = f"CVs_{job.title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.zip"
    zip_path = os.path.join(temp_dir, zip_filename)
    
    try:
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for app in applications:
                if app.cv_filename:
                    cv_path = os.path.join(UPLOAD_DIR, app.cv_filename)
                    if os.path.exists(cv_path):
                        # Create meaningful filename for ZIP
                        user_name = f"{app.user.first_name}_{app.user.last_name}"
                        file_extension = '.' + app.cv_filename.split('.')[-1]
                        archive_filename = f"{user_name}_CV{file_extension}"
                        zip_file.write(cv_path, archive_filename)
        
        return FileResponse(
            zip_path,
            filename=zip_filename,
            media_type='application/zip'
        )
        
    except Exception as e:
        # Cleanup temp directory on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Error creating CV archive")

# File cleanup utility (for maintenance)
@router.post("/admin/cleanup-orphaned-cvs")
async def cleanup_orphaned_cvs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up CV files that are no longer referenced in database"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get all CV filenames from database
        db_filenames = set()
        applications = db.query(Application).filter(Application.cv_filename.isnot(None)).all()
        for app in applications:
            if app.cv_filename:
                db_filenames.add(app.cv_filename)
        
        # Get all files in uploads directory
        uploaded_files = set()
        if os.path.exists(UPLOAD_DIR):
            uploaded_files = set(os.listdir(UPLOAD_DIR))
        
        # Find orphaned files
        orphaned_files = uploaded_files - db_filenames
        
        # Delete orphaned files
        deleted_count = 0
        for filename in orphaned_files:
            file_path = os.path.join(UPLOAD_DIR, filename)
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"Warning: Could not delete orphaned file {filename}: {e}")
        
        return {
            "message": f"Cleanup completed",
            "total_files": len(uploaded_files),
            "orphaned_files": len(orphaned_files),
            "deleted_files": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error during cleanup operation")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register_user_form(
    request: Request,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    user_data = UserCreate(
        first_name=form_data.get("first_name"),
        last_name=form_data.get("last_name"),
        email=form_data.get("email"),
        password=form_data.get("password"),
        phone=form_data.get("phone")
    )
    try:
        user = register_user(db, user_data)
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": e.detail},
            status_code=e.status_code
        )

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/apply/{job_id}", response_class=HTMLResponse)
async def apply_page(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("application_form.html", {"request": request, "job": job})

@router.post("/apply/{job_id}")
async def submit_application(
    job_id: str,
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    job_position: str = Form(...),
    cover_letter: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Save application
    application = Application(
        user_id=current_user.id,
        job_id=job.id,
        status="submitted",
        reason=cover_letter,
        score=None
    )
    db.add(application)
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)

@router.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request, db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return templates.TemplateResponse("job_listings.html", {"request": request, "jobs": jobs})

@router.post("/login")
async def login_user_form(
    request: Request,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    
    user = authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Create token and set cookie
    access_token_expires = timedelta(minutes=67)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Role-based redirection
    if user.role == "recruiter":
        redirect_url = "recruiter/dashboard"
    elif user.role == 'admin':
        redirect_url = '/admin'
    else:
        redirect_url = "/dashboard"

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=60 * 60,
        secure=False,  # Set to True in production with HTTPS
    )
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(
        url="/login?message=Logged%20out%20successfully",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie("access_token")
    return response

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch user's applications with related job data
    applications = db.query(Application).join(Job).filter(
        Application.user_id == current_user.id
    ).order_by(Application.created_at.desc()).all()
    
    return templates.TemplateResponse(
        "applicant_dashboard.html", 
        {
            "request": request, 
            "user": current_user,
            "applications": applications
        }
    )

@router.get("/recruiter_dashboard", response_class=HTMLResponse)
async def recruiter_dashboard(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("recruiter_dashboard.html", {"request": request, "user": current_user})

@router.post("/applications/{application_id}/withdraw")
async def withdraw_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the application
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check if application can be withdrawn
    if application.status in ['rejected', 'withdrawn']:
        raise HTTPException(
            status_code=400, 
            detail="Cannot withdraw this application"
        )
    
    # Update application status
    application.status = "withdrawn"
    db.commit()
    
    return {"message": "Application withdrawn successfully"}

@router.get("/jobs/create", response_class=HTMLResponse)
async def create_job_form(request: Request, current_user: User = Depends(get_current_user)):
    # if current_user.role != "recruiter":
    #     raise HTTPException(status_code=403, detail="Only recruiters can create jobs")
    # print(f"Current user: {current_user.__dict__}")  # Debug print
    return templates.TemplateResponse(
        "create_job.html",
        {"request": request, "user": current_user}
    )

@router.post("/jobs/create")
async def create_job_enhanced(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    deadline: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can create jobs")
    if not title.strip():
        raise HTTPException(status_code=400, detail="Job title is required")
    if not description.strip():
        raise HTTPException(status_code=400, detail="Job description is required")
    try:
        deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
        if deadline_dt.date() <= datetime.now().date():
            raise HTTPException(status_code=400, detail="Deadline must be in the future")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    job = Job(
        title=title.strip(),
        description=description.strip(),
        deadline=deadline_dt,
        created_by=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return RedirectResponse(url="/recruiter/dashboard?success=job_created", status_code=303)


# Pydantic models for admin operations
class UserUpdate(BaseModel):
    first_name: str
    last_name: str
    email: str
    role: str

class ApplicationStatusUpdate(BaseModel):
    status: str

# Admin middleware to check if user is admin
def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    # Get statistics
    stats = {
        "total_users": db.query(User).count(),
        "active_jobs": db.query(Job).filter(Job.deadline >= datetime.now()).count(),
        "total_applications": db.query(Application).count(),
        "pending_applications": db.query(Application).filter(Application.status == "submitted").count()
    }
    
    # Get all users
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    # Get all jobs with creator info
    jobs = db.query(Job).join(User, Job.created_by == User.id).order_by(Job.created_at.desc()).all()
    
    # Get all applications with user and job info
    applications = db.query(Application).join(User).join(Job).order_by(Application.created_at.desc()).all()
    
    return templates.TemplateResponse(
        "admin.html", 
        {
            "request": request, 
            "user": current_user,
            "stats": stats,
            "users": users,
            "jobs": jobs,
            "applications": applications
        }
    )

# Get specific user data for editing
@router.get("/admin/users/{user_id}")
async def get_user_details(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active
    }

# Update user
@router.put("/admin/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if email already exists (excluding current user)
    existing_user = db.query(User).filter(
        User.email == user_data.email,
        User.id != user_uuid
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Validate role
    valid_roles = ["admin", "recruiter", "applicant"]
    if user_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Update user data
    user.first_name = user_data.first_name
    user.last_name = user_data.last_name
    user.email = user_data.email
    user.role = user_data.role
    
    try:
        db.commit()
        db.refresh(user)
        return {"message": "User updated successfully", "user_id": str(user.id)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating user")

# Toggle user status (activate/deactivate)
@router.post("/admin/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't allow admin to deactivate themselves
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    user.is_active = not user.is_active
    
    try:
        db.commit()
        db.refresh(user)
        status = "activated" if user.is_active else "deactivated"
        return {"message": f"User {status} successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating user status")

# Delete user
@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't allow admin to delete themselves
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Check if user has applications
    applications_count = db.query(Application).filter(Application.user_id == user_uuid).count()
    if applications_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete user with {applications_count} applications. Deactivate instead."
        )
    
    try:
        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting user")

# Delete job
@router.delete("/admin/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = db.query(Job).filter(Job.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if job has applications
    applications_count = db.query(Application).filter(Application.job_id == job_uuid).count()
    if applications_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete job with {applications_count} applications"
        )
    
    try:
        db.delete(job)
        db.commit()
        return {"message": "Job deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting job")

# Update application status
@router.post("/admin/applications/{application_id}/status")
async def update_application_status(
    application_id: str,
    status_data: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    application = db.query(Application).filter(Application.id == application_uuid).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Validate status
    valid_statuses = ["submitted", "shortlisted", "rejected", "withdrawn"]
    if status_data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    application.status = status_data.status
    
    try:
        db.commit()
        db.refresh(application)
        return {"message": "Application status updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating application status")

# Delete application
@router.delete("/admin/applications/{application_id}")
async def delete_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    application = db.query(Application).filter(Application.id == application_uuid).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    try:
        db.delete(application)
        db.commit()
        return {"message": "Application deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting application")

# Get job details (for viewing)
@router.get("/admin/jobs/{job_id}/details")
async def get_job_details(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = db.query(Job).filter(Job.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get job creator info
    creator = db.query(User).filter(User.id == job.created_by).first()
    
    # Get applications for this job
    applications = db.query(Application).filter(Application.job_id == job_uuid).all()
    
    return {
        "id": str(job.id),
        "title": job.title,
        "description": job.description,
        "deadline": job.deadline.isoformat(),
        "created_at": job.created_at.isoformat(),
        "creator": {
            "id": str(creator.id) if creator else None,
            "name": f"{creator.first_name} {creator.last_name}" if creator else "Unknown",
            "email": creator.email if creator else None
        },
        "applications_count": len(applications),
        "applications": [
            {
                "id": str(app.id),
                "user_name": f"{app.user.first_name} {app.user.last_name}",
                "user_email": app.user.email,
                "status": app.status,
                "score": app.score,
                "applied_at": app.created_at.isoformat()
            } for app in applications
        ]
    }

# Get system statistics
@router.get("/admin/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    # Basic stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.deadline >= datetime.now()).count()
    total_applications = db.query(Application).count()
    
    # Applications by status
    applications_by_status = db.query(
        Application.status,
        func.count(Application.id).label('count')
    ).group_by(Application.status).all()
    
    # Users by role
    users_by_role = db.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "by_role": {role: count for role, count in users_by_role}
        },
        "jobs": {
            "total": total_jobs,
            "active": active_jobs,
            "expired": total_jobs - active_jobs
        },
        "applications": {
            "total": total_applications,
            "by_status": {status: count for status, count in applications_by_status}
        }
    }
    


# API endpoint to get recruiter's jobs with applications
@router.get("/api/recruiter/jobs")
async def get_recruiter_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all jobs posted by the current recruiter with their applications"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can access this endpoint")
    
    # Get jobs created by this recruiter
    jobs = db.query(Job).filter(Job.created_by == current_user.id).order_by(Job.created_at.desc()).all()
    
    result = []
    for job in jobs:
        # Get applications for this job with user data
        applications = db.query(Application).join(User).filter(
            Application.job_id == job.id
        ).order_by(Application.created_at.desc()).all()
        
        job_dict = {
            "id": str(job.id),
            "title": job.title,
            "description": job.description,
            "deadline": job.deadline.isoformat(),
            "created_at": job.created_at.isoformat(),
            "applications": []
        }
        
        for app in applications:
            job_dict["applications"].append({
                "id": str(app.id),
                "status": app.status,
                "score": app.score,
                "reason": app.reason,
                "created_at": app.created_at.isoformat(),
                "user": {
                    "id": str(app.user.id),
                    "first_name": app.user.first_name,
                    "last_name": app.user.last_name,
                    "email": app.user.email,
                    "phone": app.user.phone
                }
            })
        
        result.append(job_dict)
    
    return result

# API endpoint to update application status (for recruiters)
@router.post("/api/applications/{application_id}/status")
async def update_application_status(
    application_id: str,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update application status"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can update application status")
    
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    # Find application and verify recruiter owns the job
    application = db.query(Application).join(Job).filter(
        Application.id == application_uuid,
        Job.created_by == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found or access denied")
    
    # Validate status
    valid_statuses = ["submitted", "shortlisted", "rejected"]
    new_status = status_data.get("status")
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Update status
    application.status = new_status
    
    try:
        db.commit()
        return {"message": f"Application status updated to {new_status}", "status": new_status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating application status")


@router.post("/api/applications/{application_id}/notes")
async def save_application_notes(
    application_id: str,
    notes_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save recruiter notes for an application"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can save notes")
    
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    # Find application and verify recruiter owns the job
    application = db.query(Application).join(Job).filter(
        Application.id == application_uuid,
        Job.created_by == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found or access denied")
    
    # Update notes
    application.notes = notes_data.get("notes", "")
    
    try:
        db.commit()
        return {"message": "Notes saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error saving notes")
# API endpoint to delete a job (for recruiters)
@router.delete("/api/jobs/{job_id}")
async def delete_job_recruiter(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a job - for recruiters"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can delete jobs")
    
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    # Find the job and verify ownership
    job = db.query(Job).filter(
        Job.id == job_uuid,
        Job.created_by == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or access denied")
    
    # Check if job has applications
    applications_count = db.query(Application).filter(Application.job_id == job_uuid).count()
    if applications_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete job with {applications_count} applications. Contact admin if needed."
        )
    
    try:
        db.delete(job)
        db.commit()
        return {"message": "Job deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting job")

# Update the recruiter dashboard template endpoint
@router.get("/recruiter_dashboard", response_class=HTMLResponse)
async def recruiter_dashboard(
    request: Request, 
    current_user: User = Depends(get_current_user)
):
    """Recruiter dashboard page"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Access denied. Recruiters only.")
    
    return templates.TemplateResponse(
        "recruiter_dashboard.html", 
        {"request": request, "user": current_user}
    )

# # Enhanced job creation endpoint
# @router.post("/jobs/create")
# async def create_job_enhanced(
#     request: Request,
#     title: str = Form(...),
#     description: str = Form(...),
#     deadline: str = Form(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Create a new job posting"""
#     if current_user.role != "recruiter":
#         raise HTTPException(status_code=403, detail="Only recruiters can create jobs")

#     # Validate inputs
#     if not title.strip():
#         raise HTTPException(status_code=400, detail="Job title is required")
    
#     if not description.strip():
#         raise HTTPException(status_code=400, detail="Job description is required")

#     try:
#         deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
#         # Ensure deadline is in the future
#         if deadline_dt.date() <= datetime.now().date():
#             raise HTTPException(status_code=400, detail="Deadline must be in the future")
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

#     # Create job
#     job = Job(
#         title=title.strip(),
#         description=description.strip(),
#         deadline=deadline_dt,
#         created_by=current_user.id
#     )
    
#     try:
#         db.add(job)
#         db.commit()
#         db.refresh(job)
        
#         # Return success response for API calls
#         if request.headers.get("content-type") == "application/json":
#             return {"message": "Job created successfully", "job_id": str(job.id)}
#         else:
#             # Redirect for form submissions
#             return RedirectResponse(url="/recruiter_dashboard?success=job_created", status_code=303)
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail="Error creating job")

# Get job details for recruiters
@router.get("/api/jobs/{job_id}/details")
async def get_job_details_recruiter(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed job information for recruiters"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can access job details")
    
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    # Find the job and verify ownership
    job = db.query(Job).filter(
        Job.id == job_uuid,
        Job.created_by == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or access denied")
    
    # Get applications with user details
    applications = db.query(Application).join(User).filter(
        Application.job_id == job_uuid
    ).order_by(Application.created_at.desc()).all()
    
    # Prepare response
    job_details = {
        "id": str(job.id),
        "title": job.title,
        "description": job.description,
        "deadline": job.deadline.isoformat(),
        "created_at": job.created_at.isoformat(),
        "applications_count": len(applications),
        "applications": []
    }
    
    for app in applications:
        job_details["applications"].append({
            "id": str(app.id),
            "status": app.status,
            "score": app.score,
            "reason": app.reason,
            "cv_filename": app.cv_filename,
            "created_at": app.created_at.isoformat(),
            "user": {
                "id": str(app.user.id),
                "first_name": app.user.first_name,
                "last_name": app.user.last_name,
                "email": app.user.email,
                "phone": app.user.phone
            }
        })
    
    return job_details

# Get application details for recruiters (including CV download)
@router.get("/api/applications/{application_id}/details")
async def get_application_details_recruiter(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed application information for recruiters"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can access application details")
    
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    # Find the application and verify the recruiter owns the job
    application = db.query(Application).join(Job).join(User).filter(
        Application.id == application_uuid,
        Job.created_by == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found or access denied")
    
    return {
        "id": str(application.id),
        "status": application.status,
        "score": application.score,
        "reason": application.reason,
        "cv_filename": application.cv_filename,
        "created_at": application.created_at.isoformat(),
        "user": {
            "id": str(application.user.id),
            "first_name": application.user.first_name,
            "last_name": application.user.last_name,
            "email": application.user.email,
            "phone": application.user.phone
        },
        "job": {
            "id": str(application.job.id),
            "title": application.job.title,
            "description": application.job.description,
            "deadline": application.job.deadline.isoformat()
        }
    }

# Bulk update application statuses
@router.post("/api/applications/bulk-update")
async def bulk_update_application_status(
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk update multiple application statuses"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can update application status")
    
    application_ids = update_data.get("application_ids", [])
    new_status = update_data.get("status")
    
    if not application_ids:
        raise HTTPException(status_code=400, detail="No application IDs provided")
    
    # Validate status
    valid_statuses = ["submitted", "shortlisted", "rejected", "withdrawn"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    updated_count = 0
    errors = []
    
    for app_id in application_ids:
        try:
            application_uuid = uuid.UUID(app_id)
            
            # Find the application and verify ownership
            application = db.query(Application).join(Job).filter(
                Application.id == application_uuid,
                Job.created_by == current_user.id
            ).first()
            
            if application:
                application.status = new_status
                updated_count += 1
            else:
                errors.append(f"Application {app_id} not found or access denied")
                
        except ValueError:
            errors.append(f"Invalid application ID format: {app_id}")
        except Exception as e:
            errors.append(f"Error updating application {app_id}: {str(e)}")
    
    try:
        db.commit()
        return {
            "message": f"Successfully updated {updated_count} applications",
            "updated_count": updated_count,
            "errors": errors
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error committing bulk update")

# Get recruiter statistics/dashboard summary
@router.get("/api/recruiter/stats")
async def get_recruiter_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recruiter dashboard statistics"""
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can access stats")
    
    # Get jobs count
    total_jobs = db.query(Job).filter(Job.created_by == current_user.id).count()
    
    # Get applications count
    total_applications = db.query(Application).join(Job).filter(
        Job.created_by == current_user.id
    ).count()
    
    # Get applications by status
    applications_by_status = db.query(
        Application.status, 
        func.count(Application.id).label('count')
    ).join(Job).filter(
        Job.created_by == current_user.id
    ).group_by(Application.status).all()
    
    status_counts = {status: count for status, count in applications_by_status}
    
    # Get active jobs (not expired)
    active_jobs = db.query(Job).filter(
        Job.created_by == current_user.id,
        Job.deadline >= datetime.now()
    ).count()
    
    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "expired_jobs": total_jobs - active_jobs,
        "total_applications": total_applications,
        "applications_by_status": {
            "submitted": status_counts.get("submitted", 0),
            "shortlisted": status_counts.get("shortlisted", 0),
            "rejected": status_counts.get("rejected", 0),
            "withdrawn": status_counts.get("withdrawn", 0)
        }
    }