from app.models import Base
from app.database import engine

def create_table():
    print("starting to create tables")
    Base.metadata.create_all(bind = engine)
    print("tables created successfully")
    

create_table()