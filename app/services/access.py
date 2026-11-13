from fastapi import HTTPException
from app import models
from app.constants import (
    ROLE_ADMIN,
    ROLE_CLIENT,
    ROLE_VALIDATOR,
    STATUS_CREATED,
    STATUS_CANCELLED,
)


def can_access_supply(user: models.User, supply: models.Supply) -> bool:
    if user.role == ROLE_ADMIN:
        return True
    if user.role == ROLE_CLIENT:
        return True
    if user.role == ROLE_VALIDATOR:
        return supply.status not in {STATUS_CREATED, STATUS_CANCELLED}
    return False


def ensure_supply_access(user: models.User, supply: models.Supply) -> None:
    if not can_access_supply(user, supply):
        raise HTTPException(status_code=403, detail="Нет доступа к этой поставке")


def can_edit_supply(user: models.User, supply: models.Supply) -> bool:
    from app.constants import EDITABLE_STATUSES

    if user.role != ROLE_CLIENT:
        return False
    return supply.status in EDITABLE_STATUSES
