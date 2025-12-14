from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.assist_case import AssistCase
from app.models.assist_step import AssistStep
from app.models.assist_artifact import AssistArtifact
from app.models.plan import Plan
from app.services import plan_service, prompt_service

PIPELINE_STEPS = [
    "intake.normalize",
    "market.scout",
    "risk.flags",
    "score.rank",
    "report.write",
]


def _today() -> datetime.date:
    return datetime.utcnow().date()


def _reset_runs(case: AssistCase):
    if case.last_run_at and case.last_run_at.date() != _today():
        case.runs_today = 0


def plan_limits(plan: Optional[Plan]) -> dict:
    return {
        "one_shot": plan.assist_one_shot_per_day if plan else None,
        "watch_enabled": bool(plan.assist_watch_enabled) if plan else False,
        "watch_max_cases": plan.assist_watch_max_cases if plan else None,
        "watch_runs_per_day": plan.assist_watch_runs_per_day if plan else None,
        "budget_per_day": plan.assist_ai_budget_cents_per_day if plan else None,
        "reruns_per_day": plan.assist_reruns_per_day if plan else None,
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


def run_case_inline(db: Session, case: AssistCase, user) -> AssistCase:
    plan = plan_service.get_active_plan(db, user)
    limits = plan_limits(plan)

    _reset_runs(case)
    if limits["watch_runs_per_day"] is not None and case.runs_today >= limits["watch_runs_per_day"]:
        case.status = "queued"
        db.add(case)
        db.commit()
        return case

    case.status = "running"
    case.last_run_at = datetime.utcnow()
    case.runs_today = (case.runs_today or 0) + 1
    db.add(case)
    db.commit()

    # mock steps
    db.query(AssistStep).filter(AssistStep.case_id == case.id).delete()
    for step_key in PIPELINE_STEPS:
        step = AssistStep(
            case_id=case.id,
            step_key=step_key,
            status="running",
            input_json=case.intake_payload or {},
            started_at=datetime.utcnow(),
        )
        db.add(step)
        db.commit()
        step.status = "succeeded"
        step.output_json = {"mock": True, "step": step_key}
        step.finished_at = datetime.utcnow()
        db.add(step)
        db.commit()

    # artifact
    db.query(AssistArtifact).filter(AssistArtifact.case_id == case.id).delete()
    artifact = AssistArtifact(
        case_id=case.id,
        type="report_md",
        content_text="## Assist Report\n\nThis is a placeholder report. Steps executed successfully.",
        content_json={"summary": "mock"},
    )
    db.add(artifact)

    case.status = "completed" if case.mode == "one_shot" else "queued"
    if case.mode == "watch" and limits["watch_enabled"]:
        _compute_next_run(case, limits)
    else:
        case.next_run_at = None
    case.updated_at = datetime.utcnow()
    db.add(case)
    db.commit()
    db.refresh(case)
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
