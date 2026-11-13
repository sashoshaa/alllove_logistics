from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin
from app.services.audit import log_audit
from app.services.domain import is_catalog_used, is_location_used, is_supplier_used

router = APIRouter(tags=["directories"])


def _active_filter(model, current_user: models.User, include_inactive: bool):
    query = select(model)
    if current_user.role != "admin" or not include_inactive:
        query = query.where(model.is_active.is_(True))
    return query.order_by(model.id)


@router.get("/suppliers", response_model=list[schemas.SupplierOut])
async def list_suppliers(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(_active_filter(models.Supplier, current_user, include_inactive))
    return result.scalars().all()


@router.post("/suppliers", response_model=schemas.SupplierOut, status_code=201)
async def create_supplier(
    data: schemas.SupplierCreate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.Supplier).where(models.Supplier.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Поставщик с таким названием уже есть")
    item = models.Supplier(**data.model_dump())
    db.add(item)
    await db.flush()
    await log_audit(db, admin, "create_supplier", "supplier", item.id, data.model_dump())
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/suppliers/{supplier_id}", response_model=schemas.SupplierOut)
async def update_supplier(
    supplier_id: int,
    data: schemas.SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Поставщик не найден")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await log_audit(db, admin, "update_supplier", "supplier", item.id, data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Поставщик не найден")
    if await is_supplier_used(db, supplier_id):
        raise HTTPException(
            status_code=400,
            detail="Поставщик уже используется в поставках. Сделайте запись неактивной.",
        )
    await db.delete(item)
    await log_audit(db, admin, "delete_supplier", "supplier", supplier_id)
    await db.commit()
    return {"ok": True}


@router.get("/locations", response_model=list[schemas.LocationOut])
async def list_locations(
    type: Optional[str] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = _active_filter(models.StorageLocation, current_user, include_inactive)
    if type:
        query = query.where(models.StorageLocation.type == type)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/locations", response_model=schemas.LocationOut, status_code=201)
async def create_location(
    data: schemas.LocationCreate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    item = models.StorageLocation(**data.model_dump())
    db.add(item)
    await db.flush()
    await log_audit(db, admin, "create_location", "location", item.id, data.model_dump())
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/locations/{location_id}", response_model=schemas.LocationOut)
async def update_location(
    location_id: int,
    data: schemas.LocationUpdate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(
        select(models.StorageLocation).where(models.StorageLocation.id == location_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Место назначения не найдено")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await log_audit(db, admin, "update_location", "location", item.id, data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/locations/{location_id}")
async def delete_location(
    location_id: int,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(
        select(models.StorageLocation).where(models.StorageLocation.id == location_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Место назначения не найдено")
    if await is_location_used(db, location_id):
        raise HTTPException(
            status_code=400,
            detail="Место уже используется в поставках. Сделайте запись неактивной.",
        )
    await db.delete(item)
    await log_audit(db, admin, "delete_location", "location", location_id)
    await db.commit()
    return {"ok": True}


@router.get("/catalog", response_model=list[schemas.CatalogItemOut])
async def list_catalog(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(_active_filter(models.CatalogItem, current_user, include_inactive))
    return result.scalars().all()


@router.post("/catalog", response_model=schemas.CatalogItemOut, status_code=201)
async def create_catalog_item(
    data: schemas.CatalogItemCreate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.CatalogItem).where(models.CatalogItem.sku == data.sku))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Артикул уже существует")
    item = models.CatalogItem(**data.model_dump())
    db.add(item)
    await db.flush()
    await log_audit(db, admin, "create_catalog_item", "catalog_item", item.id, data.model_dump())
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/catalog/{item_id}", response_model=schemas.CatalogItemOut)
async def update_catalog_item(
    item_id: int,
    data: schemas.CatalogItemUpdate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.CatalogItem).where(models.CatalogItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Позиция номенклатуры не найдена")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await log_audit(db, admin, "update_catalog_item", "catalog_item", item.id, data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/catalog/{item_id}")
async def delete_catalog_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.CatalogItem).where(models.CatalogItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Позиция номенклатуры не найдена")
    if await is_catalog_used(db, item_id):
        raise HTTPException(
            status_code=400,
            detail="Позиция уже используется в поставках. Сделайте запись неактивной.",
        )
    await db.delete(item)
    await log_audit(db, admin, "delete_catalog_item", "catalog_item", item_id)
    await db.commit()
    return {"ok": True}
