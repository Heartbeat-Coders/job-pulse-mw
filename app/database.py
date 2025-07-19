# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

# Load settings from config
settings = get_settings()

# Create SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL,
                       echo = False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
