# app/dependencies.py

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_302_FOUND
from fastapi.responses import RedirectResponse

from app.database import get_db
from app import models

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get current user from session for template-based authentication
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        # For HTML responses, redirect to login page
        if request.headers.get("accept", "").startswith("text/html"):
            return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
        # For API responses, raise HTTP exception
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        # Clear invalid session
        request.session.pop("user_id", None)
        if request.headers.get("accept", "").startswith("text/html"):
            return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        # Clear session for inactive user
        request.session.pop("user_id", None)
        if request.headers.get("accept", "").startswith("text/html"):
            return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    return user

def get_current_admin_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current user and verify admin role"""
    current_user = get_current_user(request, db)
    
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    if current_user.role != "admin":
        if request.headers.get("accept", "").startswith("text/html"):
            return RedirectResponse(url="/", status_code=HTTP_302_FOUND)
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Admin access required"
        )
    
    return current_user

def get_current_recruiter_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current user and verify recruiter/admin role"""
    current_user = get_current_user(request, db)
    
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    if current_user.role not in ["recruiter", "admin"]:
        if request.headers.get("accept", "").startswith("text/html"):
            return RedirectResponse(url="/", status_code=HTTP_302_FOUND)
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Recruiter access required"
        )
    
    return current_user

def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get current user from session, but don't require authentication
    Returns None if user is not authenticated
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        return None
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user or not user.is_active:
        # Clear invalid session
        request.session.pop("user_id", None)
        return None
    
    return user