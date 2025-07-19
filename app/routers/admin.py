# Add these admin routes to your main.py file
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.models import User, Job, Application, Base
from app.database import get_db
from app.auth import get_current_user
import uuid

router = APIRouter()
