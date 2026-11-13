import csv
from datetime import date
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.constants import ROLE_CLIENT, STATUS_LABELS
from app.database import get_db
from app.security import require_roles
from app.services.domain import overdue_info, supply_load_options

router = APIRouter(prefix="/reports", tags=["reports"])


async def _registry_rows(
    db: AsyncSession,
    date_from: Optional[date],
    date_to: Optional[date],
    status: Optional[str],
) -> list[schemas.RegistryRow]:
    query = select(models.Supply).options(*supply_load_options())
    if date_from:
        query = query.where(models.Supply.planned_date >= date_from)
    if date_to:
        query = query.where(models.Supply.planned_date <= date_to)
    if status:
        query = query.where(models.Supply.status == status)
    query = query.order_by(models.Supply.planned_date.asc(), models.Supply.number.asc())
    result = await db.execute(query)
    rows = []
    for supply in result.scalars().unique().all():
        is_overdue, _ = overdue_info(supply)
        items = "; ".join(
            f"{item.catalog_item.sku}×{item.planned_qty}" if item.catalog_item else str(item.catalog_item_id)
            for item in supply.items
        )
        rows.append(
            schemas.RegistryRow(
                number=supply.number,
                supplier=supply.supplier.name if supply.supplier else "",
                destination=supply.location.name if supply.location else "",
                planned_date=supply.planned_date,
                status=STATUS_LABELS.get(supply.status, supply.status),
                responsible=supply.responsible.full_name if supply.responsible else "",
                is_overdue=is_overdue,
                items=items,
            )
        )
    return rows


async def _discrepancy_rows(
    db: AsyncSession,
    date_from: Optional[date],
    date_to: Optional[date],
) -> list[schemas.DiscrepancyReportRow]:
    result = await db.execute(
        select(models.Discrepancy, models.Supply, models.CatalogItem)
        .join(models.Supply, models.Supply.id == models.Discrepancy.supply_id)
        .join(models.SupplyItem, models.SupplyItem.id == models.Discrepancy.item_id)
        .join(models.CatalogItem, models.CatalogItem.id == models.SupplyItem.catalog_item_id)
        .order_by(models.Supply.number.asc())
    )
    rows = []
    for discrepancy, supply, catalog in result.all():
        if date_from and supply.planned_date < date_from:
            continue
        if date_to and supply.planned_date > date_to:
            continue
        rows.append(
            schemas.DiscrepancyReportRow(
                number=supply.number,
                sku=catalog.sku,
                name=catalog.name,
                planned_qty=discrepancy.planned_qty,
                actual_qty=discrepancy.actual_qty,
                difference=discrepancy.difference,
                kind=discrepancy.kind,
                comment=discrepancy.comment,
            )
        )
    return rows


def _csv_response(filename: str, fieldnames: list[str], rows: list[dict]) -> StreamingResponse:
    buffer = StringIO()
    buffer.write("\ufeff")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/registry", response_model=list[schemas.RegistryRow])
async def registry(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT, "admin")),
):
    return await _registry_rows(db, date_from, date_to, status)


@router.get("/registry.csv")
async def registry_csv(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT, "admin")),
):
    rows = await _registry_rows(db, date_from, date_to, status)
    payload = []
    for row in rows:
        data = row.model_dump()
        data["planned_date"] = data["planned_date"].isoformat()
        payload.append(data)
    return _csv_response(
        "registry.csv",
        ["number", "supplier", "destination", "planned_date", "status", "responsible", "is_overdue", "items"],
        payload,
    )


@router.get("/discrepancies", response_model=list[schemas.DiscrepancyReportRow])
async def discrepancies(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT, "admin")),
):
    return await _discrepancy_rows(db, date_from, date_to)


@router.get("/discrepancies.csv")
async def discrepancies_csv(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_roles(ROLE_CLIENT, "admin")),
):
    rows = await _discrepancy_rows(db, date_from, date_to)
    return _csv_response(
        "discrepancies.csv",
        ["number", "sku", "name", "planned_qty", "actual_qty", "difference", "kind", "comment"],
        [row.model_dump() for row in rows],
    )
