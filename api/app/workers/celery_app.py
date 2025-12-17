from celery import Celery
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Log release info on worker startup
logger.info(f"=== Worker Starting ===")
logger.info(f"Git SHA: {settings.git_sha or 'unknown'}")
logger.info(f"Build Time: {settings.build_time or 'unknown'}")
logger.info(f"=======================")

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
from app.workers import import_processor  # noqa: F401, E402
