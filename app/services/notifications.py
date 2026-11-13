from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.constants import (
    NOTIFICATION_CHECK_ASSIGNED,
    NOTIFICATION_OVERDUE,
    NOTIFICATION_PROPOSAL_CREATED,
    NOTIFICATION_PROPOSAL_DECIDED,
    NOTIFICATION_STATUS_CHANGED,
    ROLE_VALIDATOR,
    STATUS_LABELS,
)


async def notify(
    db: AsyncSession,
    user_id: int,
    ntype: str,
    title: str,
    message: str,
    supply_id: Optional[int] = None,
) -> models.Notification:
    item = models.Notification(
        user_id=user_id,
        type=ntype,
        title=title,
        message=message,
        supply_id=supply_id,
        created_at=datetime.utcnow(),
    )
    db.add(item)
    return item


async def notify_status_changed(
    db: AsyncSession,
    supply: models.Supply,
    old_status: str,
    new_status: str,
) -> None:
    await notify(
        db,
        supply.responsible_id,
        NOTIFICATION_STATUS_CHANGED,
        "Изменён статус поставки",
        f"Поставка {supply.number}: {STATUS_LABELS.get(old_status, old_status)} → {STATUS_LABELS.get(new_status, new_status)}",
        supply.id,
    )


async def notify_validators_check(db: AsyncSession, supply: models.Supply) -> None:
    result = await db.execute(
        select(models.User).where(
            models.User.role == ROLE_VALIDATOR,
            models.User.is_active.is_(True),
        )
    )
    for user in result.scalars().all():
        await notify(
            db,
            user.id,
            NOTIFICATION_CHECK_ASSIGNED,
            "Поставка направлена на проверку",
            f"Поставка {supply.number} ожидает сверки.",
            supply.id,
        )
    await notify(
        db,
        supply.responsible_id,
        NOTIFICATION_CHECK_ASSIGNED,
        "Поставка направлена на проверку",
        f"Поставка {supply.number} передана валидатору.",
        supply.id,
    )


async def notify_proposal_created(
    db: AsyncSession, supply: models.Supply, author: models.User
) -> None:
    await notify(
        db,
        supply.responsible_id,
        NOTIFICATION_PROPOSAL_CREATED,
        "Новое предложение изменения",
        f"{author.full_name} предложил изменение поставки {supply.number}.",
        supply.id,
    )


async def notify_proposal_decided(
    db: AsyncSession, supply: models.Supply, author_id: int, accepted: bool
) -> None:
    decision = "принято" if accepted else "отклонено"
    await notify(
        db,
        author_id,
        NOTIFICATION_PROPOSAL_DECIDED,
        "Решение по предложению",
        f"Предложение по поставке {supply.number} {decision}.",
        supply.id,
    )


async def notify_overdue_once(db: AsyncSession, supply: models.Supply) -> None:
    existing = await db.execute(
        select(models.Notification).where(
            models.Notification.user_id == supply.responsible_id,
            models.Notification.type == NOTIFICATION_OVERDUE,
            models.Notification.supply_id == supply.id,
        )
    )
    if existing.scalar_one_or_none():
        return
    await notify(
        db,
        supply.responsible_id,
        NOTIFICATION_OVERDUE,
        "Поставка просрочена",
        f"Плановая дата поставки {supply.number} уже прошла.",
        supply.id,
    )
