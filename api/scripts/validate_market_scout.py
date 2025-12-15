import logging
import os
import sys
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import joinedload

from app.core.database import SessionLocal
from app.models.user import User
from app.services import assist_service
from app.services import user_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_or_create_user(db) -> User:
    user = db.query(User).filter(User.email == "test@example.com").first()
    if user:
        return user
    return user_service.create_user(
        db, email="test@example.com", password="password"
    )


def run_market_scout(db, user: User, title: str, intake_payload: Dict[str, Any]):
    logger.info(f"--- Running market.scout for title: {title} ---")
    case = assist_service.create_draft_case(
        db, user_id=user.id, title=title, intake_payload=intake_payload, mode="one_shot"
    )
    case = assist_service.submit_case(db, case, user)
    case = assist_service.run_case_inline(db, case, user)
    logger.info(f"--- Finished market.scout for title: {title} ---")
    return case


def main():
    db = SessionLocal()
    user = get_or_create_user(db)

    case1 = run_market_scout(
        db,
        user,
        "toyota supra",
        {"search": {"q": "toyota supra", "year_min": 2020}},
    )
    case1 = db.query(assist_service.AssistCase).options(joinedload(assist_service.AssistCase.steps)).filter(assist_service.AssistCase.id == case1.id).one()

    # Run 2: "nissan gtr"
    case2 = run_market_scout(
        db,
        user,
        "nissan gtr",
        {"search": {"q": "nissan gtr", "year_min": 2018}},
    )
    case2 = db.query(assist_service.AssistCase).options(joinedload(assist_service.AssistCase.steps)).filter(assist_service.AssistCase.id == case2.id).one()

    # Validation
    # Find market.scout step (should be steps[1] but let's be robust)
    market_step_1 = next((s for s in case1.steps if s.step_key == "market.scout"), None)
    market_step_2 = next((s for s in case2.steps if s.step_key == "market.scout"), None)

    if not market_step_1 or not market_step_2:
        logger.error("Validation failed: market.scout step not found")
        db.close()
        return

    sig1 = market_step_1.output_json.get("signature") if market_step_1.output_json else None
    sig2 = market_step_2.output_json.get("signature") if market_step_2.output_json else None

    logger.info(f"Signature 1 (toyota supra): {sig1}")
    logger.info(f"Signature 2 (nissan gtr): {sig2}")

    if not sig1 or not sig2:
        logger.warning("Validation incomplete: One or both signatures are missing")
    elif sig1 == sig2:
        logger.warning("Validation note: Signatures are the same (expected if both searches returned no results)")
    else:
        logger.info("Validation successful: Signatures are different.")

    # Further checks can be done by inspecting the logs for the marketcheck provider calls
    # and comparing the results.

    db.close()


if __name__ == "__main__":
    main()