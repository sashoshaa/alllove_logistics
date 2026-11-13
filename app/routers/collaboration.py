import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.constants import (
    HISTORY_PROPOSAL,
    PROPOSAL_ACCEPTED,
    PROPOSAL_PENDING,
    PROPOSAL_REJECTED,
    ROLE_CLIENT,
    ROLE_VALIDATOR,
)
from app.database import get_db
from app.security import get_current_user, require_roles
from app.services.access import ensure_supply_access
from app.services.audit import log_audit, log_history
from app.services.domain import get_active_location, get_active_supplier, get_supply_or_404
from app.services.notifications import notify_proposal_created, notify_proposal_decided

router = APIRouter(tags=["collaboration"])


@router.get("/supplies/{supply_id}/comments", response_model=list[schemas.CommentOut])
async def list_comments(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    result = await db.execute(
        select(models.SupplyComment)
        .where(models.SupplyComment.supply_id == supply_id)
        .order_by(models.SupplyComment.created_at.asc())
    )
    rows = result.scalars().all()
    author_ids = {row.author_id for row in rows}
    users = {}
    if author_ids:
        users_result = await db.execute(select(models.User).where(models.User.id.in_(author_ids)))
        users = {user.id: user for user in users_result.scalars().all()}
    return [
        schemas.CommentOut(
            id=row.id,
            supply_id=row.supply_id,
            author_id=row.author_id,
            author_name=users.get(row.author_id).full_name if users.get(row.author_id) else None,
            text=row.text,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/supplies/{supply_id}/comments", response_model=schemas.CommentOut, status_code=201)
async def add_comment(
    supply_id: int,
    data: schemas.CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT, ROLE_VALIDATOR)),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    text = data.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Комментарий не может быть пустым")
    comment = models.SupplyComment(
        supply_id=supply.id,
        author_id=current_user.id,
        text=text,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    await db.flush()
    await log_audit(db, current_user, "add_comment", "supply", supply.id)
    await db.commit()
    await db.refresh(comment)
    return schemas.CommentOut(
        id=comment.id,
        supply_id=comment.supply_id,
        author_id=comment.author_id,
        author_name=current_user.full_name,
        text=comment.text,
        created_at=comment.created_at,
    )


@router.get("/supplies/{supply_id}/proposals", response_model=list[schemas.ProposalOut])
async def list_proposals(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    result = await db.execute(
        select(models.ChangeProposal)
        .where(models.ChangeProposal.supply_id == supply_id)
        .order_by(models.ChangeProposal.created_at.desc())
    )
    rows = result.scalars().all()
    author_ids = {row.author_id for row in rows}
    users: dict[int, models.User] = {}
    if author_ids:
        users_result = await db.execute(select(models.User).where(models.User.id.in_(author_ids)))
        users = {user.id: user for user in users_result.scalars().all()}
    return [
        _serialize_proposal(row, users[row.author_id].full_name if row.author_id in users else None)
        for row in rows
    ]


@router.post("/supplies/{supply_id}/proposals", response_model=schemas.ProposalOut, status_code=201)
async def create_proposal(
    supply_id: int,
    data: schemas.ProposalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT)),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    payload = data.model_dump(exclude_none=True)
    payload.pop("comment", None)
    if not payload:
        raise HTTPException(status_code=400, detail="Нужно указать хотя бы одно предлагаемое изменение")
    if "supplier_id" in payload:
        await get_active_supplier(db, payload["supplier_id"])
    if "location_id" in payload:
        await get_active_location(db, payload["location_id"])
    for key, value in list(payload.items()):
        if hasattr(value, "isoformat"):
            payload[key] = value.isoformat()
    proposal = models.ChangeProposal(
        supply_id=supply.id,
        author_id=current_user.id,
        payload=json.dumps(payload, ensure_ascii=False),
        status=PROPOSAL_PENDING,
        base_version=supply.version,
        comment=data.comment,
        created_at=datetime.utcnow(),
    )
    db.add(proposal)
    await db.flush()
    await notify_proposal_created(db, supply, current_user)
    await log_audit(db, current_user, "create_proposal", "proposal", proposal.id, payload)
    await db.commit()
    await db.refresh(proposal)
    return _serialize_proposal(proposal, current_user.full_name)


@router.post("/proposals/{proposal_id}/accept", response_model=schemas.ProposalOut)
async def accept_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT)),
):
    proposal, supply = await _load_proposal(db, proposal_id)
    if current_user.id != supply.responsible_id:
        raise HTTPException(status_code=403, detail="Принять предложение может только ответственный сотрудник")
    if proposal.status != PROPOSAL_PENDING:
        raise HTTPException(status_code=400, detail="Предложение уже обработано")
    if proposal.base_version != supply.version:
        raise HTTPException(
            status_code=409,
            detail="Поставка изменилась после создания предложения. Проверьте данные и создайте новое предложение.",
        )

    payload = json.loads(proposal.payload)
    if "planned_date" in payload:
        await log_history(
            db, supply.id, current_user.id, HISTORY_PROPOSAL, "planned_date", supply.planned_date, payload["planned_date"]
        )
        supply.planned_date = datetime.fromisoformat(payload["planned_date"]).date()
    if "supplier_id" in payload:
        await get_active_supplier(db, payload["supplier_id"])
        await log_history(
            db, supply.id, current_user.id, HISTORY_PROPOSAL, "supplier_id", supply.supplier_id, payload["supplier_id"]
        )
        supply.supplier_id = payload["supplier_id"]
    if "location_id" in payload:
        await get_active_location(db, payload["location_id"])
        await log_history(
            db, supply.id, current_user.id, HISTORY_PROPOSAL, "location_id", supply.location_id, payload["location_id"]
        )
        supply.location_id = payload["location_id"]

    supply.updated_at = datetime.utcnow()
    supply.version += 1
    proposal.status = PROPOSAL_ACCEPTED
    proposal.decided_by_id = current_user.id
    proposal.decided_at = datetime.utcnow()
    await notify_proposal_decided(db, supply, proposal.author_id, True)
    await log_audit(db, current_user, "accept_proposal", "proposal", proposal.id)
    await db.commit()
    await db.refresh(proposal)
    return _serialize_proposal(proposal)


@router.post("/proposals/{proposal_id}/reject", response_model=schemas.ProposalOut)
async def reject_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT)),
):
    proposal, supply = await _load_proposal(db, proposal_id)
    if current_user.id != supply.responsible_id:
        raise HTTPException(status_code=403, detail="Отклонить предложение может только ответственный сотрудник")
    if proposal.status != PROPOSAL_PENDING:
        raise HTTPException(status_code=400, detail="Предложение уже обработано")
    proposal.status = PROPOSAL_REJECTED
    proposal.decided_by_id = current_user.id
    proposal.decided_at = datetime.utcnow()
    await log_history(db, supply.id, current_user.id, HISTORY_PROPOSAL, "proposal", "pending", "rejected")
    await notify_proposal_decided(db, supply, proposal.author_id, False)
    await log_audit(db, current_user, "reject_proposal", "proposal", proposal.id)
    await db.commit()
    await db.refresh(proposal)
    return _serialize_proposal(proposal)


@router.get("/notifications", response_model=list[schemas.NotificationOut])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Notification)
        .where(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/notifications/{notification_id}/read", response_model=schemas.NotificationOut)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Notification).where(models.Notification.id == notification_id)
    )
    item = result.scalar_one_or_none()
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    item.is_read = True
    await db.commit()
    await db.refresh(item)
    return item


async def _load_proposal(db: AsyncSession, proposal_id: int):
    result = await db.execute(
        select(models.ChangeProposal).where(models.ChangeProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Предложение не найдено")
    supply = await get_supply_or_404(db, proposal.supply_id)
    return proposal, supply


def _serialize_proposal(row: models.ChangeProposal, author_name: str | None = None) -> schemas.ProposalOut:
    return schemas.ProposalOut(
        id=row.id,
        supply_id=row.supply_id,
        author_id=row.author_id,
        author_name=author_name,
        payload=json.loads(row.payload),
        status=row.status,
        base_version=row.base_version,
        decided_by_id=row.decided_by_id,
        decided_at=row.decided_at,
        comment=row.comment,
        created_at=row.created_at,
    )
