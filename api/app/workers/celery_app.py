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
}

celery_app.conf.timezone = "UTC"
