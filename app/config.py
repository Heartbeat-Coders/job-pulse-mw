# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = f"postgresql://postgres.knbcfzfrkipcjidrxnmu:uQvfnLbvSz63UH9l@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
    #DATABASE_URL : str = "postgresql://postgres:root@localhost:5432/coders_db"
    OPENAI_API_KEY: str =''
    SECRET_KEY: str = "supersecretkey"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = Settings()
