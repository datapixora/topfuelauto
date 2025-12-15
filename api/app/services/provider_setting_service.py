from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.provider_setting import ProviderSetting

DEFAULTS = [
    {"key": "marketcheck", "enabled": True, "priority": 10, "mode": "both"},
]


def ensure_defaults(db: Session) -> None:
    existing = db.query(ProviderSetting).count()
    if existing:
        return
    for cfg in DEFAULTS:
        db.add(
            ProviderSetting(
                key=cfg["key"],
                enabled=cfg.get("enabled", True),
                priority=cfg.get("priority", 100),
                mode=cfg.get("mode", "both"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
    db.commit()


def list_settings(db: Session) -> List[ProviderSetting]:
    ensure_defaults(db)
    return db.query(ProviderSetting).order_by(ProviderSetting.priority.asc(), ProviderSetting.key.asc()).all()


def update_setting(db: Session, key: str, *, enabled=None, priority=None, mode=None) -> ProviderSetting:
    ensure_defaults(db)
    setting = db.query(ProviderSetting).filter(ProviderSetting.key == key).first()
    if not setting:
        setting = ProviderSetting(
            key=key,
            enabled=True if enabled is None else enabled,
            priority=priority if priority is not None else 100,
            mode=mode or "both",
            created_at=datetime.utcnow(),
        )
        db.add(setting)
    else:
        if enabled is not None:
            setting.enabled = bool(enabled)
        if priority is not None:
            setting.priority = int(priority)
        if mode is not None:
            setting.mode = mode
    setting.updated_at = datetime.utcnow()
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def get_enabled_providers(db: Session, purpose: str) -> List[str]:
    """
    purpose: "search" | "assist"
    Returns provider keys ordered by priority asc; falls back to ['marketcheck'] if empty.
    """
    ensure_defaults(db)
    rows = (
        db.query(ProviderSetting)
        .filter(
            ProviderSetting.enabled.is_(True),
            ProviderSetting.mode.in_(["both", purpose]),
        )
        .order_by(ProviderSetting.priority.asc(), ProviderSetting.key.asc())
        .all()
    )
    keys = [row.key for row in rows]
    if not keys:
        return ["marketcheck"]
    return keys
