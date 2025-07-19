from app.database import engine
from app.models import Base

Base.metadata.drop_all()
Base.metadata.create_all()