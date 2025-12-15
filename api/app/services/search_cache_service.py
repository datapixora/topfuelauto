import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.search_cache_entry import SearchCacheEntry


def compute_signature(providers: List[str], query_normalized: str, filters: Dict[str, Any], page: int, limit: int) -> str:
    payload = {
        "providers": providers or [],
        "q": query_normalized or "",
        "filters": filters or {},
        "page": page,
        "limit": limit,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def get_cached(db: Session, signature: str, ttl_minutes: int = 15) -> Optional[SearchCacheEntry]:
    cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
    entry = (
        db.query(SearchCacheEntry)
        .filter(SearchCacheEntry.signature == signature, SearchCacheEntry.created_at >= cutoff)
        .first()
    )
    return entry


def set_cached(
    db: Session,
    *,
    signature: str,
    providers: List[str],
    query_normalized: str,
    filters: Dict[str, Any],
    page: int,
    limit: int,
    total: int,
    results: List[Dict[str, Any]],
):
    entry = (
        db.query(SearchCacheEntry)
        .filter(SearchCacheEntry.signature == signature)
        .first()
    )
    now = datetime.utcnow()
    if not entry:
        entry = SearchCacheEntry(signature=signature)
    entry.providers_json = providers
    entry.query_normalized = query_normalized
    entry.filters_json = filters
    entry.page = page
    entry.limit = limit
    entry.total = total
    entry.results_json = results
    entry.created_at = now
    db.add(entry)
    db.commit()
    return entry
