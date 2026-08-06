import sys
from pathlib import Path

# Ensure project root is on sys.path for backend.* imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.security.auth import verify_api_key
from backend.security.rate_limiter import RateLimiter

limiter = RateLimiter(max_requests=60, window_seconds=60)

app = FastAPI(
    title="Project MEW Autofill Backend API",
    version="1.0.0",
    dependencies=[Depends(verify_api_key)]
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    if not request.url.path.startswith("/test-forms"):
        limiter.check_rate_limit(request)
    response = await call_next(request)
    return response

from backend.routes.profile import router as profile_router
from backend.routes.autofill import router as autofill_router
from backend.routes.testing import router as testing_router
from backend.routes.auth import router as auth_router
from backend.routes.applications import router as applications_router

from fastapi.responses import Response

app.include_router(profile_router)
app.include_router(autofill_router)
app.include_router(testing_router)
app.include_router(auth_router)
app.include_router(applications_router)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)



