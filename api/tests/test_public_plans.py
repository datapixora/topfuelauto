"""
Regression tests for GET /api/v1/public/plans.

These tests verify:
- Only active plans are returned
- Ordering is by sort_order asc, then created_at asc
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.routers.public_plans import list_public_plans


class TestPublicPlansEndpoint:
    def test_filters_inactive_and_orders(self, db: Session):
        now = datetime.utcnow()

        keys = [
            "test_public_plans_a",
            "test_public_plans_b",
            "test_public_plans_c",
            "test_public_plans_inactive",
        ]
        db.query(Plan).filter(Plan.key.in_(keys)).delete(synchronize_session=False)
        # Ensure any existing featured plan does not conflict with the test plan below.
        db.query(Plan).filter(Plan.is_featured.is_(True)).update({"is_featured": False})
        db.commit()

        plan_c = Plan(
            key="test_public_plans_c",
            slug="test-public-plans-c",
            name="C",
            price_monthly=10,
            description="C plan",
            features=["Feature C1"],
            is_active=True,
            is_featured=False,
            sort_order=1,
            created_at=now - timedelta(days=2),
        )
        plan_b = Plan(
            key="test_public_plans_b",
            slug="test-public-plans-b",
            name="B",
            price_monthly=20,
            description="B plan",
            features=["Feature B1"],
            is_active=True,
            is_featured=False,
            sort_order=1,
            created_at=now - timedelta(days=1),
        )
        plan_a = Plan(
            key="test_public_plans_a",
            slug="test-public-plans-a",
            name="A",
            price_monthly=30,
            description="A plan",
            features=["Feature A1"],
            is_active=True,
            is_featured=True,
            sort_order=2,
            created_at=now,
        )
        plan_inactive = Plan(
            key="test_public_plans_inactive",
            slug="test-public-plans-inactive",
            name="Inactive",
            price_monthly=999,
            description="Should not show",
            features=["Hidden"],
            is_active=False,
            is_featured=False,
            sort_order=0,
            created_at=now - timedelta(days=3),
        )

        db.add_all([plan_a, plan_b, plan_c, plan_inactive])
        db.commit()

        res = list_public_plans(db)
        plans = res["plans"]

        assert [p.slug for p in plans] == ["test-public-plans-c", "test-public-plans-b", "test-public-plans-a"]
        assert all(p.is_active for p in plans)

        # Cleanup (best-effort; tests are often run against a dedicated DB anyway).
        db.query(Plan).filter(Plan.key.in_(keys)).delete(synchronize_session=False)
        db.commit()


@pytest.fixture
def db():
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
