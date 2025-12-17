"""Admin routes for SearchField management."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.search_field import SearchField
from app.schemas.search_field import (
    SearchFieldCreate,
    SearchFieldUpdate,
    SearchFieldResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/search/fields", tags=["admin", "search-fields"])


@router.get("", response_model=List[SearchFieldResponse])
def list_search_fields(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    List all search fields.
    """
    fields = db.query(SearchField).order_by(SearchField.id).all()
    return fields


@router.get("/{field_id}", response_model=SearchFieldResponse)
def get_search_field(
    field_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Get a single search field by ID.
    """
    field = db.query(SearchField).filter(SearchField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Search field not found")
    return field


@router.post("", response_model=SearchFieldResponse, status_code=201)
def create_search_field(
    field_data: SearchFieldCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Create a new search field.

    Validates:
    - key must be unique and slug-like
    - data_type must be valid
    - storage must be 'core' or 'extra'
    """
    # Check if key already exists
    existing = db.query(SearchField).filter(SearchField.key == field_data.key).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Search field with key '{field_data.key}' already exists")

    # Create new field
    try:
        new_field = SearchField(**field_data.dict())
        db.add(new_field)
        db.commit()
        db.refresh(new_field)
        logger.info(f"Admin {admin.email} created search field: {new_field.key}")
        return new_field
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create search field: {e}")
        raise HTTPException(status_code=400, detail="Failed to create search field (integrity error)")


@router.patch("/{field_id}", response_model=SearchFieldResponse)
def update_search_field(
    field_id: int,
    field_data: SearchFieldUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Update a search field.

    Note: Cannot update key, data_type, or storage (immutable).
    """
    field = db.query(SearchField).filter(SearchField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Search field not found")

    # Update only provided fields
    update_data = field_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(field, key, value)

    db.commit()
    db.refresh(field)
    logger.info(f"Admin {admin.email} updated search field: {field.key}")
    return field


@router.delete("/{field_id}", status_code=204)
def delete_search_field(
    field_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Delete a search field.

    WARNING: This does not delete data from listings.extra JSONB.
    Consider soft-delete (set enabled=false) instead.
    """
    field = db.query(SearchField).filter(SearchField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Search field not found")

    field_key = field.key
    db.delete(field)
    db.commit()
    logger.warning(f"Admin {admin.email} deleted search field: {field_key}")
    return None
