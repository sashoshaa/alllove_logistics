from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.constants import ROLE_ADMIN, ROLE_CLIENT
from app.database import get_db
from app.security import get_current_user, hash_password, require_admin
from app.services.audit import log_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=schemas.UserOut, status_code=201)
async def create_user(
    data: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.User).where(models.User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    user = models.User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await log_audit(db, admin, "create_user", "user", user.id, {"email": user.email, "role": user.role})
    await db.commit()
    await db.refresh(user)
    return user


@router.get("", response_model=list[schemas.UserOut])
async def list_users(
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = select(models.User).order_by(models.User.id)
    if current_user.role != ROLE_ADMIN:
        query = query.where(models.User.role == ROLE_CLIENT, models.User.is_active.is_(True))
    elif role:
        query = query.where(models.User.role == role)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{user_id}", response_model=schemas.UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.patch("/{user_id}", response_model=schemas.UserOut)
async def update_user(
    user_id: int,
    data: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    payload = data.model_dump(exclude_unset=True)
    if "password" in payload:
        user.hashed_password = hash_password(payload.pop("password"))
    for key, value in payload.items():
        setattr(user, key, value)
    await log_audit(db, admin, "update_user", "user", user.id, payload)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    admin: models.User = Depends(require_admin),
):
    raise HTTPException(
        status_code=405,
        detail="Удаление учётной записи запрещено. Заблокируйте доступ.",
    )
