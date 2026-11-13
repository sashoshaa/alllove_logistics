from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.database import get_db
from app.security import (
    verify_password,
    create_access_token,
    get_current_user,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(models.User).where(models.User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Учётная запись заблокирована")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    await log_audit(db, user, "login", "user", user.id)
    await db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name,
    }


@router.get("/me", response_model=schemas.UserOut)
async def me(current_user: models.User = Depends(get_current_user)):
    return current_user
