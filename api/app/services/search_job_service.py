from datetime import datetime
from typing import Any, List, Tuple

from sqlalchemy.orm import Session

from app.models.search_job import SearchJob
from app.models.search_result import SearchResult


def create_job(db: Session, *, user_id: int | None, query_normalized: str, filters: dict | None) -> SearchJob:
    job = SearchJob(
        user_id=user_id,
        query_normalized=query_normalized,
        filters_json=filters,
        status="queued",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def set_status(db: Session, job: SearchJob, status: str, error: str | None = None, result_count: int | None = None):
    job.status = status
    job.error = error
    job.result_count = result_count
    job.updated_at = datetime.utcnow()
    db.add(job)
    db.commit()


def store_results(db: Session, job_id: int, items: List[dict[str, Any]]) -> int:
    rows = []
    now = datetime.utcnow()
    for item in items:
        rows.append(
            SearchResult(
                job_id=job_id,
                title=item.get("title") or "Listing",
                year=item.get("year"),
                make=item.get("make"),
                model=item.get("model"),
                price=item.get("price"),
                location=item.get("location"),
                source_domain=item.get("source_domain") or "unknown",
                url=item.get("url"),
                fetched_at=item.get("fetched_at") or now,
                extra_json=None,
            )
        )
    if rows:
        db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


def get_job_with_results(db: Session, job_id: int) -> Tuple[SearchJob | None, List[SearchResult]]:
    job = db.get(SearchJob, job_id)
    if not job:
        return None, []
    results = db.query(SearchResult).filter(SearchResult.job_id == job_id).order_by(SearchResult.id.asc()).all()
    return job, results

