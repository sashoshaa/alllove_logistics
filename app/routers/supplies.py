from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.constants import (
    HISTORY_MANUAL,
    HISTORY_REPEAT,
    ROLE_CLIENT,
    ROLE_VALIDATOR,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_CREATED,
    STATUS_IN_TRANSIT,
    STATUS_ON_CHECK,
    TERMINAL_STATUSES,
)
from app.database import get_db
from app.security import get_current_user, require_roles
from app.services.access import can_edit_supply, ensure_supply_access
from app.services.audit import log_audit, log_history
from app.services.domain import (
    apply_status_change,
    generate_supply_number,
    get_active_client,
    get_active_location,
    get_active_supplier,
    get_supply_or_404,
    load_catalog_items,
    maybe_mark_overdue,
    serialize_supply,
    supply_list_options,
)

router = APIRouter(prefix="/supplies", tags=["supplies"])


def _sort_column(sort: str):
    mapping = {
        "planned_date": models.Supply.planned_date,
        "status": models.Supply.status,
        "number": models.Supply.number,
        "id": models.Supply.id,
    }
    return mapping.get(sort, models.Supply.id)


@router.get("/summary", response_model=schemas.SupplySummary)
async def supply_summary(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(select(models.Supply.status, models.Supply.planned_date))
    rows = result.all()
    today = date.today()
    in_transit = on_check = overdue = completed = 0
    for status_value, planned in rows:
        if status_value == STATUS_IN_TRANSIT:
            in_transit += 1
        if status_value == STATUS_ON_CHECK:
            on_check += 1
        if status_value == STATUS_COMPLETED:
            completed += 1
        if status_value not in TERMINAL_STATUSES and planned < today:
            overdue += 1
    return schemas.SupplySummary(
        in_transit=in_transit,
        on_check=on_check,
        overdue=overdue,
        completed=completed,
        total=len(rows),
    )


@router.get("", response_model=list[schemas.SupplyOut])
async def list_supplies(
    response: Response,
    search: Optional[str] = None,
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    location_id: Optional[int] = None,
    responsible_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort: str = Query(default="id"),
    order: str = Query(default="desc"),
    queue: bool = False,
    archive: bool = False,
    limit: Optional[int] = Query(default=None, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = select(models.Supply)
    if current_user.role == ROLE_VALIDATOR or queue:
        if current_user.role == ROLE_VALIDATOR:
            query = query.where(models.Supply.status == STATUS_ON_CHECK)
    if archive:
        query = query.where(models.Supply.status.in_(TERMINAL_STATUSES))
    elif status:
        query = query.where(models.Supply.status == status)
    elif current_user.role == ROLE_CLIENT:
        query = query.where(models.Supply.status.notin_(TERMINAL_STATUSES))
    if supplier_id:
        query = query.where(models.Supply.supplier_id == supplier_id)
    if location_id:
        query = query.where(models.Supply.location_id == location_id)
    if responsible_id:
        query = query.where(models.Supply.responsible_id == responsible_id)
    if date_from:
        query = query.where(models.Supply.planned_date >= date_from)
    if date_to:
        query = query.where(models.Supply.planned_date <= date_to)
    if search:
        pattern = f"%{search}%"
        query = (
            query.outerjoin(models.SupplyItem)
            .outerjoin(models.CatalogItem)
            .where(
                or_(
                    models.Supply.number.ilike(pattern),
                    models.CatalogItem.sku.ilike(pattern),
                    models.CatalogItem.name.ilike(pattern),
                )
            )
            .distinct()
        )

    column = _sort_column(sort)
    id_query = query.with_only_columns(models.Supply.id).order_by(
        column.asc() if order == "asc" else column.desc()
    )
    if search:
        id_query = id_query.distinct()
    total = (await db.execute(select(func.count()).select_from(id_query.order_by(None).subquery()))).scalar() or 0
    response.headers["X-Total-Count"] = str(total)
    if limit is not None:
        id_query = id_query.offset(offset).limit(limit)
    ids = list((await db.execute(id_query)).scalars().all())
    if not ids:
        return []
    loaded = await db.execute(
        select(models.Supply).options(*supply_list_options()).where(models.Supply.id.in_(ids))
    )
    by_id = {row.id: row for row in loaded.scalars().unique()}
    supplies = [by_id[item_id] for item_id in ids if item_id in by_id]
    await maybe_mark_overdue(db, supplies)
    await db.commit()
    return [serialize_supply(supply) for supply in supplies]


@router.post("", response_model=schemas.SupplyOut, status_code=201)
async def create_supply(
    data: schemas.SupplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT)),
):
    await get_active_supplier(db, data.supplier_id)
    await get_active_location(db, data.location_id)
    await get_active_client(db, data.responsible_id)
    catalog = await load_catalog_items(db, [item.catalog_item_id for item in data.items])

    number = await generate_supply_number(db)
    supply = models.Supply(
        number=number,
        supplier_id=data.supplier_id,
        location_id=data.location_id,
        planned_date=data.planned_date,
        status=STATUS_CREATED,
        responsible_id=data.responsible_id,
        created_by_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(supply)
    await db.flush()
    for item in data.items:
        db.add(
            models.SupplyItem(
                supply_id=supply.id,
                catalog_item_id=item.catalog_item_id,
                planned_qty=item.quantity,
            )
        )
        catalog[item.catalog_item_id]
    await log_history(db, supply.id, current_user.id, HISTORY_MANUAL, "created", None, number)
    await log_audit(db, current_user, "create_supply", "supply", supply.id, {"number": number})
    await db.commit()
    supply = await get_supply_or_404(db, supply.id)
    return serialize_supply(supply)


@router.get("/{supply_id}", response_model=schemas.SupplyOut)
async def get_supply(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    await maybe_mark_overdue(db, [supply])
    await db.commit()
    supply = await get_supply_or_404(db, supply_id)
    return serialize_supply(supply)


@router.patch("/{supply_id}", response_model=schemas.SupplyOut)
async def update_supply(
    supply_id: int,
    data: schemas.SupplyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT)),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    if not can_edit_supply(current_user, supply):
        raise HTTPException(status_code=400, detail="Поставка уже передана на проверку или завершена")

    payload = data.model_dump(exclude_unset=True)
    if "supplier_id" in payload:
        await get_active_supplier(db, payload["supplier_id"])
        await log_history(
            db, supply.id, current_user.id, HISTORY_MANUAL, "supplier_id", supply.supplier_id, payload["supplier_id"]
        )
        supply.supplier_id = payload["supplier_id"]
    if "location_id" in payload:
        await get_active_location(db, payload["location_id"])
        await log_history(
            db, supply.id, current_user.id, HISTORY_MANUAL, "location_id", supply.location_id, payload["location_id"]
        )
        supply.location_id = payload["location_id"]
    if "planned_date" in payload:
        await log_history(
            db, supply.id, current_user.id, HISTORY_MANUAL, "planned_date", supply.planned_date, payload["planned_date"]
        )
        supply.planned_date = payload["planned_date"]
    if "responsible_id" in payload:
        await get_active_client(db, payload["responsible_id"])
        await log_history(
            db,
            supply.id,
            current_user.id,
            HISTORY_MANUAL,
            "responsible_id",
            supply.responsible_id,
            payload["responsible_id"],
        )
        supply.responsible_id = payload["responsible_id"]
    if "items" in payload and payload["items"] is not None:
        await load_catalog_items(db, [item["catalog_item_id"] for item in payload["items"]])
        supply.items.clear()
        await db.flush()
        for item in payload["items"]:
            db.add(
                models.SupplyItem(
                    supply_id=supply.id,
                    catalog_item_id=item["catalog_item_id"],
                    planned_qty=item["quantity"],
                )
            )
        await log_history(db, supply.id, current_user.id, HISTORY_MANUAL, "items", "previous", "updated")

    supply.updated_at = datetime.utcnow()
    supply.version += 1
    await log_audit(db, current_user, "update_supply", "supply", supply.id, payload)
    await db.commit()
    supply = await get_supply_or_404(db, supply.id)
    return serialize_supply(supply)


@router.post("/{supply_id}/status", response_model=schemas.SupplyOut)
async def change_status(
    supply_id: int,
    data: schemas.StatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    await apply_status_change(db, supply, current_user, data.status)
    if data.comment:
        db.add(
            models.SupplyComment(
                supply_id=supply.id,
                author_id=current_user.id,
                text=data.comment,
                created_at=datetime.utcnow(),
            )
        )
    await log_audit(db, current_user, "change_status", "supply", supply.id, {"status": data.status})
    await db.commit()
    supply = await get_supply_or_404(db, supply.id)
    return serialize_supply(supply)


@router.post("/{supply_id}/repeat", response_model=schemas.SupplyOut, status_code=201)
async def repeat_supply(
    supply_id: int,
    data: schemas.SupplyRepeat,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT)),
):
    source = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, source)
    await get_active_client(db, data.responsible_id)
    number = await generate_supply_number(db)
    copy = models.Supply(
        number=number,
        supplier_id=source.supplier_id,
        location_id=source.location_id,
        planned_date=data.planned_date,
        status=STATUS_CREATED,
        responsible_id=data.responsible_id,
        created_by_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(copy)
    await db.flush()
    for item in source.items:
        db.add(
            models.SupplyItem(
                supply_id=copy.id,
                catalog_item_id=item.catalog_item_id,
                planned_qty=item.planned_qty,
            )
        )
    await log_history(db, copy.id, current_user.id, HISTORY_REPEAT, "copied_from", None, source.number)
    await log_audit(
        db,
        current_user,
        "repeat_supply",
        "supply",
        copy.id,
        {"source": source.number, "number": number},
    )
    await db.commit()
    copy = await get_supply_or_404(db, copy.id)
    return serialize_supply(copy)


@router.get("/{supply_id}/history", response_model=list[schemas.HistoryOut])
async def supply_history(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    result = await db.execute(
        select(models.SupplyHistory)
        .where(models.SupplyHistory.supply_id == supply_id)
        .order_by(models.SupplyHistory.created_at.asc(), models.SupplyHistory.id.asc())
    )
    rows = result.scalars().all()
    actor_ids = {row.actor_id for row in rows}
    users = {}
    if actor_ids:
        users_result = await db.execute(select(models.User).where(models.User.id.in_(actor_ids)))
        users = {user.id: user for user in users_result.scalars().all()}
    return [
        schemas.HistoryOut(
            id=row.id,
            supply_id=row.supply_id,
            actor_id=row.actor_id,
            actor_name=users.get(row.actor_id).full_name if users.get(row.actor_id) else None,
            source=row.source,
            field=row.field,
            old_value=row.old_value,
            new_value=row.new_value,
            created_at=row.created_at,
        )
        for row in rows
    ]
