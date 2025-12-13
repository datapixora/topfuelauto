from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.plan import Plan

PLANS = [
    {
        "key": "free",
        "name": "Free",
        "description": "Starter plan",
        "price_monthly": None,
        "features": {"vin_history": False},
        "quotas": {"searches_per_day": 25},
    },
    {
        "key": "pro",
        "name": "Pro",
        "description": "For frequent buyers",
        "price_monthly": 39,
        "features": {"vin_history": True, "priority_support": True},
        "quotas": {"searches_per_day": 250},
    },
    {
        "key": "ultimate",
        "name": "Ultimate",
        "description": "High volume",
        "price_monthly": 99,
        "features": {"vin_history": True, "priority_support": True, "bulk": True},
        "quotas": {"searches_per_day": 1000},
    },
]


def main():
    db: Session = SessionLocal()
    try:
        for p in PLANS:
            existing = db.query(Plan).filter(Plan.key == p["key"]).first()
            if existing:
                existing.name = p["name"]
                existing.description = p["description"]
                existing.price_monthly = p["price_monthly"]
                existing.features = p["features"]
                existing.quotas = p["quotas"]
                db.add(existing)
            else:
                db.add(Plan(**p))
        db.commit()
        print("Plans seeded/updated")
    finally:
        db.close()


if __name__ == "__main__":
    main()
