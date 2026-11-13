from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.config import settings
from app.constants import ALLOWED_DOC_EXTENSIONS, MAX_DOC_SIZE, ROLE_CLIENT
from app.database import get_db
from app.security import get_current_user, require_roles
from app.services.access import ensure_supply_access
from app.services.audit import log_audit
from app.services.domain import get_supply_or_404

router = APIRouter(tags=["documents"])


def _validate_file(file: UploadFile, size: int) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_DOC_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Допустимы только файлы PDF, JPG и PNG")
    if size > MAX_DOC_SIZE:
        raise HTTPException(status_code=400, detail="Размер файла не должен превышать 20 МБ")
    return suffix


@router.post("/supplies/{supply_id}/documents", response_model=schemas.DocumentOut, status_code=201)
async def upload_document(
    supply_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT)),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    content = await file.read()
    suffix = _validate_file(file, len(content))
    folder = Path(settings.UPLOAD_DIR) / str(supply.id)
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{suffix}"
    path = folder / stored_name
    path.write_bytes(content)

    doc = models.SupplyDocument(
        supply_id=supply.id,
        filename=str(path),
        original_name=file.filename or stored_name,
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        uploaded_by_id=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.add(doc)
    await db.flush()
    await log_audit(db, current_user, "upload_document", "document", doc.id, {"supply": supply.number})
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/supplies/{supply_id}/documents", response_model=list[schemas.DocumentOut])
async def list_documents(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    result = await db.execute(
        select(models.SupplyDocument)
        .where(models.SupplyDocument.supply_id == supply_id)
        .order_by(models.SupplyDocument.id)
    )
    return result.scalars().all()


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.SupplyDocument).where(models.SupplyDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    supply = await get_supply_or_404(db, doc.supply_id)
    ensure_supply_access(current_user, supply)
    path = Path(doc.filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Файл отсутствует в хранилище")
    return FileResponse(path, filename=doc.original_name, media_type=doc.content_type)
