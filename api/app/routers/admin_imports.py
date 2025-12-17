"""Admin routes for CSV import management."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.schemas.admin_import import (
    ImportUploadResponse,
    ImportStartRequest,
    ImportProgressResponse,
    ImportSummary
)
from app.services import import_service
from app.workers.import_processor import process_import

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/imports", tags=["admin", "imports"])


@router.post("/upload", response_model=ImportUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    source_key: str = Form(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Upload a CSV file for import.

    Returns:
        - import_id
        - detected headers
        - sample preview (first 20 rows)
        - suggested column mapping
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    # Read file data
    try:
        file_data = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read file")

    # Validate file size (max 50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    if len(file_data) > max_size:
        raise HTTPException(status_code=400, detail=f"File too large (max {max_size / 1024 / 1024}MB)")

    # Create import record
    try:
        admin_import = import_service.create_import(
            db=db,
            filename=file.filename,
            file_data=file_data,
            content_type=file.content_type or "text/csv",
            source_key=source_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create import: {e}")
        raise HTTPException(status_code=500, detail="Failed to process CSV file")

    # Return response
    return ImportUploadResponse(
        import_id=admin_import.id,
        filename=admin_import.filename,
        file_size=admin_import.file_size,
        sha256=admin_import.sha256,
        total_rows=admin_import.total_rows,
        detected_headers=admin_import.detected_headers,
        sample_preview=admin_import.sample_preview,
        suggested_mapping=admin_import.column_map,
        status=admin_import.status,
    )


@router.get("/{import_id}", response_model=ImportProgressResponse)
def get_import_status(
    import_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Get import status and progress.
    """
    admin_import = import_service.get_import(db, import_id)
    if not admin_import:
        raise HTTPException(status_code=404, detail="Import not found")

    return ImportProgressResponse.from_orm(admin_import)


@router.get("", response_model=List[ImportSummary])
def list_imports(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    List recent imports.
    """
    imports = import_service.list_imports(db, limit=limit, offset=offset)
    return [ImportSummary.from_orm(imp) for imp in imports]


@router.post("/{import_id}/start", response_model=ImportProgressResponse)
def start_import(
    import_id: int,
    request: ImportStartRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Start processing an import with the provided column mapping.

    Enqueues a Celery background task to process the CSV file.
    """
    # Validate mapping
    try:
        import_service.validate_column_mapping(request.column_map)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Update import with mapping
    try:
        admin_import = import_service.update_import_mapping(db, import_id, request.column_map)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Update source_key if provided
    if request.source_key:
        admin_import.source_key = request.source_key
        db.commit()
        db.refresh(admin_import)

    # Enqueue processing task
    try:
        task = process_import.delay(import_id)
        logger.info(f"Enqueued import task for import {import_id}: task_id={task.id}")
    except Exception as e:
        logger.error(f"Failed to enqueue import task: {e}")
        raise HTTPException(status_code=500, detail="Failed to start import processing")

    return ImportProgressResponse.from_orm(admin_import)
