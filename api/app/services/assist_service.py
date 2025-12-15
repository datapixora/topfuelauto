import hashlib
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.assist_artifact import AssistArtifact
from app.models.assist_case import AssistCase
from app.models.assist_step import AssistStep
from app.models.plan import Plan
from app.models.search_event import SearchEvent
from app.providers import get_active_providers
from app.services import plan_service, prompt_service, search_service, usage_service, provider_setting_service

PIPELINE_STEPS = [
    "intake.normalize",
    "market.scout",
    "risk.flags",
    "score.rank",
    "report.write",
]

DEFAULT_FREE_SEARCHES_PER_DAY = 5
SCOUT_MAX_ITEMS = 20


def _today() -> datetime.date:
    return datetime.utcnow().date()


def _reset_runs(case: AssistCase):
    if case.last_run_at and case.last_run_at.date() != _today():
        case.runs_today = 0
        case.updated_at = datetime.utcnow()


def plan_limits(plan: Optional[Plan]) -> dict:
    return {
        "one_shot": plan.assist_one_shot_per_day if plan else None,
        "watch_enabled": bool(plan.assist_watch_enabled) if plan else False,
        "watch_max_cases": plan.assist_watch_max_cases if plan else None,
        "watch_runs_per_day": plan.assist_watch_runs_per_day if plan else None,
        "budget_per_day": plan.assist_ai_budget_cents_per_day if plan else None,
        "reruns_per_day": plan.assist_reruns_per_day if plan else None,
    }


def _resolve_search_limit(plan: Optional[Plan]) -> Tuple[int | None, str]:
    plan_limit = None
    quota_message = "Daily search limit reached. Upgrade to continue."
    if plan and plan.searches_per_day is not None:
        plan_limit = plan.searches_per_day
    elif plan and plan.key == "free":
        plan_limit = DEFAULT_FREE_SEARCHES_PER_DAY
    elif not plan:
        plan_limit = DEFAULT_FREE_SEARCHES_PER_DAY
    if plan and plan.quota_reached_message:
        quota_message = plan.quota_reached_message
    return plan_limit, quota_message


def _safe_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit() or ch == "-")
        if digits and digits.strip("-").isdigit():
            try:
                return int(digits)
            except ValueError:
                return None
    return None


def _extract_search_query(intake_payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any], int]:
    payload = intake_payload or {}
    search_block = payload.get("search") or payload.get("query") or {}
    if isinstance(search_block, str):
        search_block = {"q": search_block}

    q = (
        search_block.get("q")
        or search_block.get("query")
        or payload.get("q")
        or payload.get("query")
        or payload.get("notes")
        or ""
    )
    filters = {
        "make": search_block.get("make") or payload.get("make"),
        "model": search_block.get("model") or payload.get("model"),
        "year_min": search_block.get("year_min") or payload.get("year_min"),
        "year_max": search_block.get("year_max") or payload.get("year_max"),
        "price_min": search_block.get("price_min") or payload.get("price_min"),
        "price_max": search_block.get("price_max") or payload.get("price_max"),
        "location": search_block.get("location") or payload.get("location"),
        "sort": search_block.get("sort") or payload.get("sort"),
    }
    page_size = search_block.get("page_size") or payload.get("page_size") or SCOUT_MAX_ITEMS
    try:
        page_size_int = int(page_size)
    except Exception:  # noqa: BLE001
        page_size_int = SCOUT_MAX_ITEMS
    page_size_int = max(1, min(page_size_int, SCOUT_MAX_ITEMS))
    return q.strip() or "car search", filters, page_size_int


def _normalize_market_items(raw_items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in raw_items[:limit]:
        listing_id = item.get("listing_id") or item.get("id")
        normalized.append(
            {
                "listing_id": listing_id,
                "url": item.get("url"),
                "title": item.get("title"),
                "price": _safe_int(item.get("price")),
                "year": item.get("year"),
                "mileage": _safe_int(item.get("mileage") or item.get("miles") or item.get("odometer")),
                "location": item.get("location"),
            }
        )
    return normalized


def _compute_signature(items: List[Dict[str, Any]]) -> str:
    payload = [
        {
            "listing_id": item.get("listing_id"),
            "price": item.get("price"),
            "mileage": item.get("mileage"),
            "year": item.get("year"),
        }
        for item in sorted(items, key=lambda x: x.get("listing_id") or "")
    ]
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def _get_previous_search_results(db: Session, case_id: int) -> Dict[str, Any] | None:
    step = (
        db.query(AssistStep)
        .filter(AssistStep.case_id == case_id, AssistStep.step_key == "market.scout", AssistStep.status == "succeeded")
        .order_by(AssistStep.id.desc())
        .first()
    )
    if not step or not step.output_json:
        return None
    return {"output": step.output_json, "finished_at": step.finished_at}


def _detect_delta(
    current_items: List[Dict[str, Any]],
    current_signature: str,
    previous_output: Dict[str, Any] | None,
) -> Tuple[bool, Dict[str, Any]]:
    if not previous_output:
        return True, {"reason": "first_run"}

    prev_payload = previous_output.get("output") if isinstance(previous_output, dict) else previous_output
    prev_signature = prev_payload.get("signature") if isinstance(prev_payload, dict) else None
    prev_items = prev_payload.get("items") if isinstance(prev_payload, dict) else []
    prev_finished_at = previous_output.get("finished_at") if isinstance(previous_output, dict) else None

    if prev_signature and prev_signature == current_signature:
        return False, {"reason": "signature_match", "previous_finished_at": prev_finished_at}

    prev_map = {i.get("listing_id"): i for i in prev_items or [] if i.get("listing_id")}
    curr_map = {i.get("listing_id"): i for i in current_items if i.get("listing_id")}

    new_ids = [lid for lid in curr_map.keys() if lid not in prev_map]
    removed_ids = [lid for lid in prev_map.keys() if lid not in curr_map]
    price_changes = []
    for lid in curr_map.keys() & prev_map.keys():
        prev_price = prev_map[lid].get("price")
        curr_price = curr_map[lid].get("price")
        if prev_price is not None and curr_price is not None and prev_price != curr_price:
            price_changes.append({"listing_id": lid, "from": prev_price, "to": curr_price})

    if new_ids or removed_ids or price_changes:
        return True, {
            "reason": "delta",
            "new_ids": new_ids,
            "removed_ids": removed_ids,
            "price_changes": price_changes,
            "previous_finished_at": prev_finished_at,
        }

    return False, {"reason": "no_meaningful_change", "previous_finished_at": prev_finished_at}


def _add_artifact(
    db: Session,
    case_id: int,
    artifact_type: str,
    content_text: str | None,
    content_json: Dict[str, Any] | None = None,
):
    db.add(
        AssistArtifact(
            case_id=case_id,
            type=artifact_type,
            content_text=content_text,
            content_json=content_json,
        )
    )
    db.commit()


def _fetch_real_search_results(
    db: Session,
    user,
    intake_payload: Dict[str, Any],
    plan: Optional[Plan],
    case_id: Optional[int] = None,
    case_title: Optional[str] = None,
) -> Dict[str, Any]:
    logger = logging.getLogger(__name__)
    q, filters, page_size = _extract_search_query(intake_payload)
    plan_limit, quota_message = _resolve_search_limit(plan)
    user_id = getattr(user, "id", None) if user else None
    reset_at = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    query_normalized = " ".join(q.strip().lower().split())
    logger.info(
        "market.scout start case=%s title=%s q_norm=%s",
        case_id,
        case_title,
        query_normalized,
    )

    if user_id and plan_limit is not None:
        usage = usage_service.get_or_create_today_usage(db, user_id)
        if usage.search_count >= plan_limit:
            payload = {
                "detail": quota_message,
                "code": "quota_exceeded",
                "limit": plan_limit,
                "used": usage.search_count,
                "remaining": max(plan_limit - usage.search_count, 0),
                "reset_at": reset_at.isoformat(),
            }
            try:
                search_service.log_search_event(
                    db,
                    user_id=user_id,
                    session_id=None,
                    query_raw=q,
                    query_normalized=query_normalized,
                    filters=filters,
                    providers=[],
                    result_count=0,
                    latency_ms=None,
                    cache_hit=False,
                    rate_limited=False,
                    status="error",
                    error_code="quota_exceeded",
                )
            except Exception:
                pass
            return {
                "status": "quota_exceeded",
                "payload": payload,
                "reset_at": reset_at,
                "plan_limit": plan_limit,
                "q": q,
                "filters": filters,
            }

    settings = get_settings()
    enabled_keys = provider_setting_service.get_enabled_providers(db, "assist")
    providers_requested = list(enabled_keys)
    providers = get_active_providers(settings, allowed_keys=enabled_keys)
    if not providers:
        providers = get_active_providers(settings, allowed_keys=["marketcheck"])

    items: List[Dict[str, Any]] = []
    total = 0
    sources: List[Dict[str, Any]] = []
    status = "ok"
    error_code = None
    start_ts = time.time()
    providers_executed: List[str] = []
    per_provider_counts: Dict[str, int] = {}
    per_provider_errors: Dict[str, str] = {}

    for provider in providers:
        provider_start = time.time()
        provider_name = getattr(provider, "name", "unknown")
        providers_executed.append(provider_name)
        logger.info(
            "market.scout provider start case=%s provider=%s q=%s filters=%s signature=%s",
            case_id,
            provider_name,
            q,
            filters,
            "pending",
        )
        try:
            provider_items, provider_total, meta = provider.search_listings(
                query=q,
                filters=filters,
                page=1,
                page_size=page_size,
            )
            items.extend(provider_items[:page_size])
            total += provider_total
            sources.append(meta)
            per_provider_counts[provider_name] = len(provider_items)
            elapsed_ms = int((time.time() - provider_start) * 1000)
            logger.info(
                "market.scout provider done case=%s provider=%s count=%s elapsed_ms=%s",
                case_id,
                provider_name,
                len(provider_items),
                elapsed_ms,
            )
        except Exception as exc:  # noqa: BLE001
            meta = {"name": provider_name, "error": "request_failed"}
            sources.append(meta)
            per_provider_counts[provider_name] = 0
            per_provider_errors[provider_name] = str(exc)
            logger.warning(
                "market.scout provider failed case=%s provider=%s err=%s",
                case_id,
                provider_name,
                exc,
            )

    latency_ms = int((time.time() - start_ts) * 1000)

    if not items and per_provider_errors and len(per_provider_errors) == len(providers_executed):
        status = "error"
        error_code = "provider_error"

    usage = None
    remaining = None
    quota_info = None
    if user_id:
        if total > 0:
            usage = usage_service.increment_search_usage(db, user_id)
        else:
            usage = usage_service.get_or_create_today_usage(db, user_id)
        if plan_limit is not None:
            remaining = max(plan_limit - usage.search_count, 0)
        quota_info = {
            "limit": plan_limit,
            "used": usage.search_count if usage else None,
            "remaining": remaining,
            "reset_at": reset_at if plan_limit is not None else None,
        }
    debug_info = {
        "providers_requested": providers_requested,
        "providers_enabled_for_assist": enabled_keys,
        "providers_executed": providers_executed,
        "per_provider_counts": per_provider_counts,
        "per_provider_errors": per_provider_errors,
        "query_normalized": query_normalized,
        "filters": filters,
        "case_id": case_id,
        "case_title": case_title,
    }

    try:
        search_service.log_search_event(
            db,
            user_id=user_id,
            session_id=None,
            query_raw=q,
            query_normalized=query_normalized,
            filters=filters,
            providers=[p.name for p in providers],
            result_count=total,
            latency_ms=latency_ms,
            cache_hit=False,
            rate_limited=False,
            status=status,
            error_code=error_code,
        )
    except Exception:
        pass

    return {
        "status": status,
        "error_code": error_code,
        "items": items,
        "total": total,
        "sources": sources,
        "quota": quota_info,
        "plan_limit": plan_limit,
        "q": q,
        "filters": filters,
        "page_size": page_size,
        "debug": debug_info,
        "query_normalized": query_normalized,
        "case_id": case_id,
        "case_title": case_title,
        "cache_used": False,
        "cache_key": None,
    }


def create_draft_case(db: Session, user_id: int, title: str | None, intake_payload: dict, mode: str) -> AssistCase:
    case = AssistCase(
        user_id=user_id,
        title=title,
        intake_payload=intake_payload,
        mode=mode,
        status="draft",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def _count_today_cases(db: Session, user_id: int, mode: str) -> int:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(AssistCase.id))
        .filter(AssistCase.user_id == user_id, AssistCase.mode == mode, AssistCase.created_at >= today_start)
        .scalar()
        or 0
    )


def submit_case(db: Session, case: AssistCase, user) -> AssistCase:
    plan = plan_service.get_active_plan(db, user)
    limits = plan_limits(plan)

    if case.mode == "one_shot":
        max_daily = limits["one_shot"]
        if max_daily is not None:
            used = _count_today_cases(db, user.id, "one_shot")
            if used >= max_daily:
                raise ValueError("assist_one_shot_limit_reached")
    if case.mode == "watch":
        if not limits["watch_enabled"]:
            raise ValueError("assist_watch_not_allowed")
        max_cases = limits["watch_max_cases"]
        if max_cases is not None:
            active_watch = (
                db.query(func.count(AssistCase.id))
                .filter(AssistCase.user_id == user.id, AssistCase.mode == "watch", AssistCase.is_active.is_(True))
                .scalar()
                or 0
            )
            if active_watch >= max_cases:
                raise ValueError("assist_watch_max_cases")

    case.status = "queued"
    case.budget_cents_limit = limits["budget_per_day"]
    case.updated_at = datetime.utcnow()
    case.next_run_at = datetime.utcnow()
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def _compute_next_run(case: AssistCase, limits: dict):
    runs_per_day = limits.get("watch_runs_per_day") or 1
    hours = max(24 // max(runs_per_day, 1), 1)
    case.next_run_at = datetime.utcnow() + timedelta(hours=hours)


def _format_price(price: Optional[int]) -> str:
    if price is None:
        return "N/A"
    return f"${price:,.0f}"


def run_case_inline(db: Session, case: AssistCase, user) -> AssistCase:
    logger = logging.getLogger(__name__)
    try:
        if case.status == "running":
            return case

        plan = plan_service.get_active_plan(db, user)
        limits = plan_limits(plan)

        _reset_runs(case)
        if limits["watch_runs_per_day"] is not None and case.runs_today >= limits["watch_runs_per_day"]:
            case.status = "queued"
            db.add(case)
            db.commit()
            return case

        previous_market = _get_previous_search_results(db, case.id)
        prev_report = (
            db.query(AssistArtifact)
            .filter(AssistArtifact.case_id == case.id, AssistArtifact.type == "report_md")
            .order_by(AssistArtifact.id.desc())
            .first()
        )
        prev_report_payload = None
        if prev_report:
            prev_report_payload = {
                "content_text": prev_report.content_text,
                "content_json": prev_report.content_json,
            }

        # reset steps/artifacts for the new run
        db.query(AssistStep).filter(AssistStep.case_id == case.id).delete()
        db.query(AssistArtifact).filter(AssistArtifact.case_id == case.id).delete()
        db.commit()

        case.status = "running"
        case.last_run_at = datetime.utcnow()
        case.runs_today = (case.runs_today or 0) + 1
        db.add(case)
        db.commit()

        # intake.normalize (placeholder)
        intake_step = AssistStep(
            case_id=case.id,
            step_key="intake.normalize",
            status="running",
            input_json=case.intake_payload or {},
            started_at=datetime.utcnow(),
        )
        db.add(intake_step)
        db.commit()
        normalized_payload = case.intake_payload or {}
        case.normalized_payload = normalized_payload
        intake_step.status = "succeeded"
        intake_step.output_json = normalized_payload
        intake_step.finished_at = datetime.utcnow()
        db.add(intake_step)
        db.add(case)
        db.commit()

        market_step = AssistStep(
            case_id=case.id,
            step_key="market.scout",
            status="running",
            input_json=case.intake_payload or {},
            started_at=datetime.utcnow(),
        )
        db.add(market_step)
        db.commit()

        search_res = _fetch_real_search_results(
            db,
            user,
            case.intake_payload or {},
            plan,
            case_id=case.id,
            case_title=case.title,
        )
        if search_res.get("status") == "quota_exceeded":
            market_step.status = "blocked"
            market_step.output_json = {"reason": "quota_exceeded", **(search_res.get("payload") or {})}
            market_step.finished_at = datetime.utcnow()
            db.add(market_step)
            db.commit()

            reset_at = search_res.get("reset_at") or (
                datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            )
            detail = search_res.get("payload") or {}
            report_text = (
                f"Daily search quota reached ({detail.get('used')}/{detail.get('limit')}). "
                f"Resets at {reset_at.isoformat()}."
            )
            _add_artifact(db, case.id, "report_md", report_text, detail)
            case.status = "queued" if case.mode == "watch" else "failed"
            if case.mode == "watch":
                case.next_run_at = reset_at
            else:
                case.next_run_at = None
            case.updated_at = datetime.utcnow()
            db.add(case)
            db.commit()
            db.refresh(case)
            return case

        if search_res.get("status") == "error":
            market_step.status = "failed"
            market_step.error = search_res.get("error_code") or "provider_error"
            market_step.finished_at = datetime.utcnow()
            db.add(market_step)
            db.commit()
            case.status = "failed"
            if case.mode == "watch" and limits["watch_enabled"]:
                _compute_next_run(case, limits)
            else:
                case.next_run_at = None
            case.updated_at = datetime.utcnow()
            db.add(case)
            db.commit()
            db.refresh(case)
            return case

        raw_items = search_res.get("items") or []
        page_size = search_res.get("page_size") or SCOUT_MAX_ITEMS
        normalized_items = _normalize_market_items(raw_items, page_size)
        signature = _compute_signature(normalized_items)
        total = search_res.get("total") or 0
        market_output = {
            "items": normalized_items,
            "signature": signature,
            "total": total,
        }
        market_output["source_signature"] = signature
        market_output["cache_used"] = False
        market_output["case_id"] = case.id
        market_output["case_title"] = case.title
        market_output["query_normalized"] = search_res.get("query_normalized")
        market_output["filters"] = search_res.get("filters")
        if search_res.get("debug"):
            market_output["debug"] = search_res["debug"]
        if search_res.get("quota"):
            market_output["quota"] = search_res["quota"]
        market_step.status = "succeeded"
        market_step.output_json = market_output
        market_step.finished_at = datetime.utcnow()
        db.add(market_step)
        db.commit()

        case.normalized_payload = {"q": search_res.get("q"), **(search_res.get("filters") or {})}

        has_delta, delta_info = _detect_delta(normalized_items, signature, previous_market)

        if case.mode == "watch" and not has_delta:
            # Skip expensive steps; still surface summary and keep previous report if present
            delta_text = "No new listings or price changes since last run."
            if delta_info.get("reason") == "signature_match":
                delta_text = "No change detected (signature match)."
            _add_artifact(
                db,
                case.id,
                "delta_summary",
                delta_text,
                {"delta": delta_info, "signature": signature, "total": total},
            )
            if prev_report_payload:
                _add_artifact(
                    db,
                    case.id,
                    "report_md",
                    prev_report_payload.get("content_text"),
                    prev_report_payload.get("content_json"),
                )

            for step_key in ["risk.flags", "score.rank", "report.write"]:
                step = AssistStep(
                    case_id=case.id,
                    step_key=step_key,
                    status="succeeded",
                    input_json={"reason": "no_delta"},
                    output_json={"skipped": True, "delta": delta_info},
                    started_at=datetime.utcnow(),
                    finished_at=datetime.utcnow(),
                )
                db.add(step)
            db.commit()

            case.status = "queued"
            if case.mode == "watch" and limits["watch_enabled"]:
                _compute_next_run(case, limits)
            else:
                case.next_run_at = None
            case.updated_at = datetime.utcnow()
            db.add(case)
            db.commit()
            db.refresh(case)
            return case

        # risk.flags (simple heuristic)
        risk_step = AssistStep(
            case_id=case.id,
            step_key="risk.flags",
            status="running",
            input_json={"items": normalized_items},
            started_at=datetime.utcnow(),
        )
        db.add(risk_step)
        db.commit()
        risk_flags: List[Dict[str, Any]] = []
        for item in normalized_items:
            if item.get("price") is None:
                risk_flags.append({"listing_id": item.get("listing_id"), "flag": "missing_price", "severity": "medium"})
            if item.get("mileage") and item.get("year"):
                year_val = _safe_int(item.get("year"))
                if year_val:
                    age = datetime.utcnow().year - year_val
                    if age > 0:
                        avg_miles = item["mileage"] / age
                        if avg_miles > 20000:
                            risk_flags.append(
                                {"listing_id": item.get("listing_id"), "flag": "high_annual_mileage", "severity": "low"}
                            )
        risk_step.status = "succeeded"
        risk_step.output_json = {"flags": risk_flags}
        risk_step.finished_at = datetime.utcnow()
        db.add(risk_step)
        db.commit()

        # score.rank (basic price-based ranking)
        score_step = AssistStep(
            case_id=case.id,
            step_key="score.rank",
            status="running",
            input_json={"items": normalized_items},
            started_at=datetime.utcnow(),
        )
        db.add(score_step)
        db.commit()
        ranked = sorted(normalized_items, key=lambda x: (x.get("price") is None, x.get("price") or float("inf")))
        scores = []
        for idx, item in enumerate(ranked):
            base = max(100 - idx * 5, 40)
            scores.append({"listing_id": item.get("listing_id"), "score": base})
        score_step.status = "succeeded"
        score_step.output_json = {"scores": scores, "ranked_ids": [s["listing_id"] for s in scores]}
        score_step.finished_at = datetime.utcnow()
        db.add(score_step)
        db.commit()

        # report.write
        report_step = AssistStep(
            case_id=case.id,
            step_key="report.write",
            status="running",
            input_json={"items": normalized_items, "scores": scores, "flags": risk_flags},
            started_at=datetime.utcnow(),
        )
        db.add(report_step)
        db.commit()

        top_lines = []
        for item in ranked[:5]:
            title = item.get("title") or "Listing"
            price_txt = _format_price(item.get("price"))
            year_txt = str(item.get("year") or "N/A")
            location_txt = item.get("location") or "N/A"
            url = item.get("url") or ""
            suffix = f" - {url}" if url else ""
            top_lines.append(f"- {title} ({year_txt}) - {price_txt} - {location_txt}{suffix}")

        debug_lines = []
        debug_lines.append(f"- case_id: {case.id}")
        debug_lines.append(f"- title: {case.title}")
        debug_lines.append(f"- query: {search_res.get('query_normalized')}")
        debug_lines.append(f"- filters: {search_res.get('filters')}")
        debug_meta = search_res.get("debug") or {}
        debug_lines.append(f"- providers_enabled: {debug_meta.get('providers_enabled_for_assist')}")
        debug_lines.append(f"- providers_executed: {debug_meta.get('providers_executed')}")
        debug_lines.append(f"- per_provider_counts: {debug_meta.get('per_provider_counts')}")
        debug_lines.append(f"- signature: {signature}")
        debug_lines.append(f"- cache_used: {search_res.get('cache_used', False)}")
        debug_lines.append(f"- cache_key: {search_res.get('cache_key')}")
        first_url = normalized_items[0].get("url") if normalized_items else None
        first_title = normalized_items[0].get("title") if normalized_items else None
        debug_lines.append(f"- sample_first_result_title: {first_title}")
        debug_lines.append(f"- sample_first_result_url: {first_url}")

        report_md = "\n".join(
            [
                f"## Market Scout Results ({len(normalized_items)} items, total {total})",
                "",
                "Top picks:",
                *top_lines,
                "",
                "Delta detected" if has_delta else "No significant delta detected",
                "",
                "### Debug",
                *debug_lines,
            ]
        )

        report_step.status = "succeeded"
        report_step.output_json = {"report_md": report_md, "delta": delta_info, "signature": signature}
        report_step.finished_at = datetime.utcnow()
        db.add(report_step)
        db.commit()

        _add_artifact(
            db,
            case.id,
            "report_md",
            report_md,
            {
                "items": normalized_items,
                "scores": scores,
                "flags": risk_flags,
                "signature": signature,
                "delta": delta_info,
            },
        )

        case.status = "completed" if case.mode == "one_shot" else "queued"
        if case.mode == "watch" and limits["watch_enabled"]:
            _compute_next_run(case, limits)
        else:
            case.next_run_at = None
        logger.info(
            "market.scout end case=%s total=%s signature=%s cache_used=%s",
            case.id,
            total,
            signature,
            search_res.get("cache_used", False),
        )
        case.updated_at = datetime.utcnow()
        db.add(case)
        db.commit()
        db.refresh(case)
        return case
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "assist run_case_inline failed case=%s user=%s",
            case.id if case else None,
            getattr(user, "id", None),
        )
        try:
            case.status = "failed"
            case.next_run_at = None
            case.updated_at = datetime.utcnow()
            db.add(case)
            db.commit()
        except Exception:
            db.rollback()
        return case


def list_user_cases(db: Session, user_id: int, status: Optional[str] = None) -> List[AssistCase]:
    q = db.query(AssistCase).filter(AssistCase.user_id == user_id)
    if status:
        q = q.filter(AssistCase.status == status)
    return q.order_by(AssistCase.created_at.desc()).all()


def get_case_detail(db: Session, user_id: int, case_id: int):
    case = db.query(AssistCase).filter(AssistCase.user_id == user_id, AssistCase.id == case_id).first()
    if not case:
        return None
    steps = db.query(AssistStep).filter(AssistStep.case_id == case.id).order_by(AssistStep.id.asc()).all()
    artifacts = db.query(AssistArtifact).filter(AssistArtifact.case_id == case.id).all()
    return case, steps, artifacts


def cancel_case(db: Session, user_id: int, case_id: int) -> bool:
    case = db.query(AssistCase).filter(AssistCase.user_id == user_id, AssistCase.id == case_id).first()
    if not case:
        return False
    case.status = "canceled"
    case.updated_at = datetime.utcnow()
    db.add(case)
    db.commit()
    return True


def case_cards(db: Session, user_id: int, limit: int = 5):
    cases = (
        db.query(AssistCase)
        .filter(AssistCase.user_id == user_id)
        .order_by(AssistCase.updated_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for c in cases:
        total_steps = len(PIPELINE_STEPS)
        done = db.query(AssistStep).filter(AssistStep.case_id == c.id, AssistStep.status == "succeeded").count()
        progress = int((done / total_steps) * 100) if total_steps else 0
        result.append(
            {
                "id": c.id,
                "title": c.title or "Untitled",
                "status": c.status,
                "mode": c.mode,
                "progress_percent": progress,
                "last_activity_at": c.updated_at.isoformat() if c.updated_at else None,
                "next_run_at": c.next_run_at.isoformat() if c.next_run_at else None,
            }
        )
    return result
