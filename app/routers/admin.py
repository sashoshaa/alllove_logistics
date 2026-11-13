from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.database import get_db
from app.security import require_admin
from app.services.backup import create_backup, list_backups, restore_backup

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit", response_model=list[schemas.AuditOut])
async def list_audit(
    object_type: Optional[str] = None,
    object_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    query = select(models.AuditEvent).order_by(models.AuditEvent.created_at.desc(), models.AuditEvent.id.desc())
    if object_type:
        query = query.where(models.AuditEvent.object_type == object_type)
    if object_id is not None:
        query = query.where(models.AuditEvent.object_id == object_id)
    result = await db.execute(query)
    rows = result.scalars().all()
    actor_ids = {row.actor_id for row in rows if row.actor_id}
    users = {}
    if actor_ids:
        users_result = await db.execute(select(models.User).where(models.User.id.in_(actor_ids)))
        users = {user.id: user for user in users_result.scalars().all()}
    return [
        schemas.AuditOut(
            id=row.id,
            actor_id=row.actor_id,
            actor_name=users.get(row.actor_id).full_name if row.actor_id and users.get(row.actor_id) else None,
            action=row.action,
            object_type=row.object_type,
            object_id=row.object_id,
            details=row.details,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/audit/{event_id}")
async def mutate_audit(event_id: int, admin: models.User = Depends(require_admin)):
    raise HTTPException(status_code=405, detail="Записи журнала нельзя изменять")


@router.delete("/audit/{event_id}")
async def delete_audit(event_id: int, admin: models.User = Depends(require_admin)):
    raise HTTPException(status_code=405, detail="Записи журнала нельзя удалять")


@router.get("/backups")
async def backups(admin: models.User = Depends(require_admin)):
    return list_backups()


@router.post("/backups")
async def run_backup(
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    return await create_backup(db)


@router.post("/backups/{name}/restore")
async def restore(
    name: str,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    try:
        return await restore_backup(db, name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
