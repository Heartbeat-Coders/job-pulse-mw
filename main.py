# app/main.py
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from app.backend import guest_user


from app.routers.auth import router as auth_router
from app.routers.main import router as main_router

app = FastAPI(title="Heartbeat Coders E-Recruitment")

# Add the Authentication Middleware
app.add_middleware(AuthenticationMiddleware, backend=guest_user)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

def datetimeformat(value, format="%Y-%m-%d"):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value.strftime(format)

templates.env.filters['datetimeformat'] = datetimeformat
# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(main_router, tags=["main"])
