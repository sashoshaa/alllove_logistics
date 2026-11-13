from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.constants import (
    HISTORY_CHECK,
    KIND_MATCH,
    KIND_SHORTAGE,
    KIND_SURPLUS,
    ROLE_VALIDATOR,
    STATUS_HAS_DISCREPANCIES,
    STATUS_IN_TRANSIT,
    STATUS_ON_CHECK,
    STATUS_CHECKED,
)
from app.database import get_db
from app.security import require_roles
from app.services.access import ensure_supply_access
from app.services.audit import log_audit, log_history
from app.services.domain import apply_status_change, get_supply_or_404, serialize_supply
from app.services.notifications import notify

router = APIRouter(tags=["checks"])


@router.post("/supplies/{supply_id}/check", response_model=schemas.SupplyOut)
async def check_supply(
    supply_id: int,
    data: schemas.SupplyCheckIn,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_VALIDATOR)),
):
    supply = await get_supply_or_404(db, supply_id)
    ensure_supply_access(current_user, supply)
    if supply.status != STATUS_ON_CHECK:
        raise HTTPException(status_code=400, detail="Проверять можно только поставки в статусе «На проверке»")

    if data.return_for_clarification:
        await apply_status_change(db, supply, current_user, STATUS_IN_TRANSIT)
        if data.comment:
            db.add(
                models.SupplyComment(
                    supply_id=supply.id,
                    author_id=current_user.id,
                    text=data.comment,
                    created_at=datetime.utcnow(),
                )
            )
        await log_audit(db, current_user, "return_supply", "supply", supply.id)
        await db.commit()
        supply = await get_supply_or_404(db, supply.id)
        return serialize_supply(supply)

    items_by_id = {item.id: item for item in supply.items}
    if set(items_by_id) != {row.item_id for row in data.items}:
        raise HTTPException(
            status_code=400,
            detail="Нужно заполнить фактическое количество по всем позициям",
        )

    check = models.SupplyCheck(
        supply_id=supply.id,
        validator_id=current_user.id,
        result=KIND_MATCH,
        comment=data.comment,
        created_at=datetime.utcnow(),
    )
    db.add(check)
    await db.flush()

    has_diff = False
    for row in data.items:
        item = items_by_id[row.item_id]
        item.actual_qty = row.actual_qty
        diff = row.actual_qty - item.planned_qty
        if diff != 0:
            has_diff = True
            kind = KIND_SURPLUS if diff > 0 else KIND_SHORTAGE
            db.add(
                models.Discrepancy(
                    supply_id=supply.id,
                    item_id=item.id,
                    check_id=check.id,
                    planned_qty=item.planned_qty,
                    actual_qty=row.actual_qty,
                    difference=diff,
                    kind=kind,
                    comment=data.comment,
                )
            )

    new_status = STATUS_HAS_DISCREPANCIES if has_diff else STATUS_CHECKED
    check.result = "discrepancy" if has_diff else "match"
    supply.actual_date = date.today()
    await apply_status_change(db, supply, current_user, new_status, source=HISTORY_CHECK)
    await log_history(
        db,
        supply.id,
        current_user.id,
        HISTORY_CHECK,
        "check_result",
        None,
        check.result,
    )
    if data.comment:
        db.add(
            models.SupplyComment(
                supply_id=supply.id,
                author_id=current_user.id,
                text=data.comment,
                created_at=datetime.utcnow(),
            )
        )
    await notify(
        db,
        supply.responsible_id,
        "status_changed",
        "Результат проверки",
        f"Поставка {supply.number}: {'есть расхождения' if has_diff else 'проверена без расхождений'}.",
        supply.id,
    )
    await log_audit(db, current_user, "check_supply", "supply", supply.id, {"result": check.result})
    await db.commit()
    supply = await get_supply_or_404(db, supply.id)
    return serialize_supply(supply)
