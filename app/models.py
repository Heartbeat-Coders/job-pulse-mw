# app/models.py

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from pytz import timezone
from sqlalchemy.ext.declarative import declarative_base

# Base class for models
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=False)
    role = Column(String, default="applicant")  # applicant, recruiter, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now())

    applications = relationship("Application", back_populates="user")
    jobs = relationship("Job", back_populates="creator")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")))

    applications = relationship("Application", back_populates="job")
    creator = relationship("User", back_populates="jobs")
    

class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    status = Column(String, default="submitted")  # submitted, shortlisted, rejected, etc.
    score = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    cv_filename = Column(String)
    created_at = Column(DateTime, default=datetime.now(timezone("Africa/Blantyre")))

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
