from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "topfuelauto",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.beat_schedule = {
    "assist-watch-enqueue": {
        "task": "app.workers.assist.enqueue_due_watch_cases",
        "schedule": 120,
        "args": (),
    },
    "alerts-enqueue": {
        "task": "app.workers.alerts.enqueue_due_alerts",
        "schedule": 150,
        "args": (),
    },
    "data-engine-enqueue": {
        "task": "app.workers.data_engine.enqueue_due_sources",
        "schedule": 180,  # Check every 3 minutes
        "args": (),
    },
}

celery_app.conf.timezone = "UTC"

# Import all task modules to register them with Celery
# This must be done AFTER celery_app is created to avoid circular imports
from app.workers import data_engine  # noqa: F401, E402
from app.workers import assist  # noqa: F401, E402
from app.workers import alerts  # noqa: F401, E402
