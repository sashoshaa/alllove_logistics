from datetime import date, datetime
from typing import Iterable, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import func, inspect as sa_inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.constants import (
    CLIENT_TRANSITIONS,
    HISTORY_MANUAL,
    ROLE_CLIENT,
    ROLE_VALIDATOR,
    STATUS_COMPLETED,
    STATUS_CREATED,
    STATUS_LABELS,
    STATUS_ON_CHECK,
    TERMINAL_STATUSES,
    VALIDATOR_TRANSITIONS,
)
from app.services.audit import log_history
from app.services.notifications import notify_overdue_once, notify_status_changed, notify_validators_check


def overdue_info(supply: models.Supply, today: Optional[date] = None) -> tuple[bool, int]:
    today = today or date.today()
    if supply.status in TERMINAL_STATUSES:
        return False, 0
    if supply.planned_date >= today:
        return False, 0
    return True, (today - supply.planned_date).days


def serialize_item(item: models.SupplyItem) -> schemas.SupplyItemOut:
    catalog = item.catalog_item
    difference = None
    if item.actual_qty is not None:
        difference = item.actual_qty - item.planned_qty
    return schemas.SupplyItemOut(
        id=item.id,
        catalog_item_id=item.catalog_item_id,
        planned_qty=item.planned_qty,
        actual_qty=item.actual_qty,
        sku=catalog.sku if catalog else None,
        name=catalog.name if catalog else None,
        category=catalog.category if catalog else None,
        size=catalog.size if catalog else None,
        color=catalog.color if catalog else None,
        difference=difference,
    )


def serialize_supply(supply: models.Supply, today: Optional[date] = None) -> schemas.SupplyOut:
    is_overdue, days = overdue_info(supply, today)
    return schemas.SupplyOut(
        id=supply.id,
        number=supply.number,
        supplier_id=supply.supplier_id,
        supplier_name=supply.supplier.name if supply.supplier else None,
        location_id=supply.location_id,
        location_name=supply.location.name if supply.location else None,
        location_type=supply.location.type if supply.location else None,
        planned_date=supply.planned_date,
        actual_date=supply.actual_date,
        status=supply.status,
        status_label=STATUS_LABELS.get(supply.status, supply.status),
        responsible_id=supply.responsible_id,
        responsible_name=supply.responsible.full_name if supply.responsible else None,
        created_by_id=supply.created_by_id,
        created_by_name=supply.created_by.full_name if supply.created_by else None,
        version=supply.version,
        created_at=supply.created_at,
        updated_at=supply.updated_at,
        is_overdue=is_overdue,
        overdue_days=days,
        items=[serialize_item(item) for item in supply.items],
        documents=[
            schemas.DocumentOut.model_validate(doc)
            for doc in ([] if "documents" in sa_inspect(supply).unloaded else supply.documents)
        ],
    )


def supply_list_options():
    return (
        selectinload(models.Supply.supplier),
        selectinload(models.Supply.location),
        selectinload(models.Supply.responsible),
        selectinload(models.Supply.created_by),
        selectinload(models.Supply.items).selectinload(models.SupplyItem.catalog_item),
    )


def supply_load_options():
    return (
        *supply_list_options(),
        selectinload(models.Supply.documents),
    )


async def get_supply_or_404(db: AsyncSession, supply_id: int) -> models.Supply:
    result = await db.execute(
        select(models.Supply).options(*supply_load_options()).where(models.Supply.id == supply_id)
    )
    supply = result.scalar_one_or_none()
    if not supply:
        raise HTTPException(status_code=404, detail="Поставка не найдена")
    return supply


async def generate_supply_number(db: AsyncSession) -> str:
    result = await db.execute(select(func.max(models.Supply.id)))
    last_id = result.scalar() or 0
    return f"SUP-{last_id + 1:04d}"


async def get_active_client(db: AsyncSession, user_id: int) -> models.User:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Ответственный сотрудник не найден или заблокирован")
    if user.role != ROLE_CLIENT:
        raise HTTPException(status_code=400, detail="Ответственным может быть только сотрудник роли «клиент»")
    return user


async def get_active_supplier(db: AsyncSession, supplier_id: int) -> models.Supplier:
    result = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=400, detail="Поставщик не найден")
    if not supplier.is_active:
        raise HTTPException(status_code=400, detail="Нельзя выбрать неактивного поставщика")
    return supplier


async def get_active_location(db: AsyncSession, location_id: int) -> models.StorageLocation:
    result = await db.execute(
        select(models.StorageLocation).where(models.StorageLocation.id == location_id)
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=400, detail="Место назначения не найдено")
    if not location.is_active:
        raise HTTPException(status_code=400, detail="Нельзя выбрать неактивное место назначения")
    return location


async def load_catalog_items(db: AsyncSession, item_ids: Sequence[int]) -> dict[int, models.CatalogItem]:
    result = await db.execute(
        select(models.CatalogItem).where(models.CatalogItem.id.in_(item_ids))
    )
    items = {item.id: item for item in result.scalars().all()}
    missing = [item_id for item_id in item_ids if item_id not in items]
    if missing:
        raise HTTPException(status_code=400, detail="Позиция номенклатуры не найдена")
    for item in items.values():
        if not item.is_active:
            raise HTTPException(status_code=400, detail=f"Позиция {item.sku} неактивна")
    return items


async def apply_status_change(
    db: AsyncSession,
    supply: models.Supply,
    actor: models.User,
    new_status: str,
    source: str = HISTORY_MANUAL,
) -> None:
    old_status = supply.status
    if new_status == old_status:
        return

    allowed = set()
    if actor.role == ROLE_CLIENT:
        allowed = CLIENT_TRANSITIONS.get(old_status, set())
    elif actor.role == ROLE_VALIDATOR:
        allowed = VALIDATOR_TRANSITIONS.get(old_status, set())
    elif actor.role == "admin":
        raise HTTPException(status_code=403, detail="Администратор не меняет статус поставки")

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Переход «{STATUS_LABELS.get(old_status)}» → «{STATUS_LABELS.get(new_status)}» запрещён",
        )

    if old_status == STATUS_CREATED and new_status == STATUS_COMPLETED:
        raise HTTPException(status_code=400, detail="Нельзя завершить поставку без проверки")

    supply.status = new_status
    supply.updated_at = datetime.utcnow()
    supply.version += 1
    await log_history(db, supply.id, actor.id, source, "status", old_status, new_status)
    await notify_status_changed(db, supply, old_status, new_status)
    if new_status == STATUS_ON_CHECK:
        await notify_validators_check(db, supply)


async def maybe_mark_overdue(db: AsyncSession, supplies: Iterable[models.Supply]) -> None:
    for supply in supplies:
        is_overdue, _ = overdue_info(supply)
        if is_overdue:
            await notify_overdue_once(db, supply)


async def is_supplier_used(db: AsyncSession, supplier_id: int) -> bool:
    result = await db.execute(
        select(func.count()).select_from(models.Supply).where(models.Supply.supplier_id == supplier_id)
    )
    return (result.scalar() or 0) > 0


async def is_location_used(db: AsyncSession, location_id: int) -> bool:
    result = await db.execute(
        select(func.count()).select_from(models.Supply).where(models.Supply.location_id == location_id)
    )
    return (result.scalar() or 0) > 0


async def is_catalog_used(db: AsyncSession, item_id: int) -> bool:
    result = await db.execute(
        select(func.count()).select_from(models.SupplyItem).where(models.SupplyItem.catalog_item_id == item_id)
    )
    return (result.scalar() or 0) > 0
