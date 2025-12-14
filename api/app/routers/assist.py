from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services import assist_service, plan_service, prompt_service
from app.models.assist_case import AssistCase

router = APIRouter(prefix="/api/v1/assist", tags=["assist"])


@router.post("/cases")
def create_case(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    title = payload.get("title")
    mode = payload.get("mode", "one_shot")
    intake = payload.get("intake_payload") or {}
    case = assist_service.create_draft_case(db, current_user.id, title, intake, mode)
    return {"case": _case_out(case)}


@router.post("/cases/{case_id}/submit")
def submit_case(case_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    case = db.get(AssistCase, case_id)
    if not case or case.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        prompt_service.ensure_default_templates(db)
        assist_service.submit_case(db, case, current_user)
        assist_service.run_case_inline(db, case, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"case": _case_out(case)}


@router.get("/cases")
def list_cases(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    cases = assist_service.list_user_cases(db, current_user.id)
    return {"cases": [_case_out(c) for c in cases]}


@router.get("/cases/{case_id}")
def case_detail(case_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    res = assist_service.get_case_detail(db, current_user.id, case_id)
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    case, steps, artifacts = res
    return {
        "case": _case_out(case),
        "steps": [_step_out(s) for s in steps],
        "artifacts": [_artifact_out(a) for a in artifacts],
    }


@router.post("/cases/{case_id}/cancel")
def cancel_case(case_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ok = assist_service.cancel_case(db, current_user.id, case_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"canceled": True}


@router.post("/cases/{case_id}/rerun")
def rerun_case(case_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    case = db.get(AssistCase, case_id)
    if not case or case.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    assist_service.run_case_inline(db, case, current_user)
    return {"case": _case_out(case)}


@router.get("/cards")
def case_cards(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    cards = assist_service.case_cards(db, current_user.id)
    return {"cards": cards}


def _case_out(c: AssistCase):
    return {
        "id": c.id,
        "title": c.title,
        "status": c.status,
        "mode": c.mode,
        "last_run_at": c.last_run_at.isoformat() if c.last_run_at else None,
        "next_run_at": c.next_run_at.isoformat() if c.next_run_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _step_out(s):
    return {
        "id": s.id,
        "step_key": s.step_key,
        "status": s.status,
        "output_json": s.output_json,
        "error": s.error,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
    }


def _artifact_out(a):
    return {
        "id": a.id,
        "type": a.type,
        "content_text": a.content_text,
        "content_json": a.content_json,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
