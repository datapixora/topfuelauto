from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.core.config import get_settings
from app.routers import auth, listings, search, vin, broker, billing, assist, alerts, legal
from app.routers.health import get_health_payload, router as health_router
from app.routers.admin import router as admin_router
from app.routers.admin_plans import router as admin_plans_router
from app.routers.admin_data import router as admin_data_router
from app.routers.admin_proxies import router as admin_proxies_router
from app.routers.admin_imports import router as admin_imports_router
from app.routers.meta import router as meta_router

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

# Log release info on startup
logger.info(f"=== API Starting ===")
logger.info(f"Git SHA: {settings.git_sha or 'unknown'}")
logger.info(f"Build Time: {settings.build_time or 'unknown'}")
logger.info(f"===================")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers to ensure CORS headers on all error responses
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with CORS headers."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("Origin", "*") if request.headers.get("Origin") in settings.cors_origins else settings.cors_origins[0] if settings.cors_origins else "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with CORS headers."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("Origin", "*") if request.headers.get("Origin") in settings.cors_origins else settings.cors_origins[0] if settings.cors_origins else "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with CORS headers and logging."""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}"},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("Origin", "*") if request.headers.get("Origin") in settings.cors_origins else settings.cors_origins[0] if settings.cors_origins else "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )


@app.get("/health")
async def health():
    """Legacy root-level health for load balancers; prefer /api/v1/health."""
    return get_health_payload()


@app.get("/")
async def root():
    return {"message": "TopFuel Auto API"}


app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(search.router)
app.include_router(vin.router)
app.include_router(broker.router)
app.include_router(health_router)
app.include_router(meta_router)
app.include_router(admin_router)
app.include_router(admin_plans_router)
app.include_router(admin_data_router)
app.include_router(admin_proxies_router)
app.include_router(admin_imports_router)
app.include_router(billing.router)
app.include_router(assist.router)
app.include_router(alerts.router)
app.include_router(legal.router)
