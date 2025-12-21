"""Service for managing site-wide settings."""

from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.models.site_settings import SiteSetting


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a setting value by key."""
    setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: Optional[str], description: Optional[str] = None) -> SiteSetting:
    """Set a setting value, creating or updating as needed."""
    setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    
    if setting:
        setting.value = value
        setting.updated_at = datetime.utcnow()
        if description is not None:
            setting.description = description
    else:
        setting = SiteSetting(
            key=key,
            value=value,
            description=description,
        )
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return setting


def delete_setting(db: Session, key: str) -> bool:
    """Delete a setting by key."""
    setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    if setting:
        db.delete(setting)
        db.commit()
        return True
    return False


def list_settings(db: Session) -> list[SiteSetting]:
    """List all settings."""
    return db.query(SiteSetting).order_by(SiteSetting.key).all()
