from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import auth, listings, search, vin, broker, billing, assist, alerts
from app.routers.health import get_health_payload, router as health_router
from app.routers.admin import router as admin_router
from app.routers.admin_plans import router as admin_plans_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(admin_router)
app.include_router(admin_plans_router)
app.include_router(billing.router)
app.include_router(assist.router)
app.include_router(alerts.router)
