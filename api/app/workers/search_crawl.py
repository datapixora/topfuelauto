import logging

from app.workers.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.providers.web_crawl import WebCrawlOnDemandProvider
from app.services import search_job_service, provider_setting_service
from app.models.search_job import SearchJob

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.search_crawl.run_on_demand_crawl")
def run_on_demand_crawl(job_id: int):
    db = SessionLocal()
    try:
        job = db.get(SearchJob, job_id)
        if not job:
            return "missing"

        settings = get_settings()
        crawl_setting = provider_setting_service.get_setting(db, "web_crawl_on_demand")
        crawl_config = crawl_setting.settings_json if crawl_setting else {}
        provider = WebCrawlOnDemandProvider(settings, config=crawl_config)

        search_job_service.set_status(db, job, "running")

        if not provider.enabled:
            search_job_service.set_status(db, job, "failed", error="no_sources_configured", result_count=0)
            return "no_sources"

        items = provider.crawl_sources(job.query_normalized)
        saved = search_job_service.store_results(db, job.id, items)
        search_job_service.set_status(db, job, "succeeded", result_count=saved)
        return {"saved": saved}
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_on_demand_crawl failed job_id=%s error=%s", job_id, exc)
        try:
            job = db.get(SearchJob, job_id)
            if job:
                search_job_service.set_status(db, job, "failed", error=str(exc))
        finally:
            db.rollback()
        return "error"
    finally:
        db.close()

