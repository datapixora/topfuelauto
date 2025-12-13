from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "topfuelauto",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.beat_schedule = {
    "placeholder-task": {
        "task": "app.workers.tasks.placeholder",
        "schedule": 3600,
        "args": (),
    }
}

celery_app.conf.timezone = "UTC"