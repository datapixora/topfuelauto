"""Tiny smoke helper to validate PlanOut serialization with nullable fields."""

from datetime import datetime

from app.schemas.plan import PlanOut


def main():
    plan = PlanOut(
        id=1,
        key="free",
        name="Free",
        price_monthly=None,
        description=None,
        features=None,
        quotas=None,
        searches_per_day=None,
        quota_reached_message=None,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    print("PlanOut smoke OK:", plan.dict())


if __name__ == "__main__":
    main()
