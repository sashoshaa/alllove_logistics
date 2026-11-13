import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app import models


async def log_audit(
    db: AsyncSession,
    actor: Optional[models.User],
    action: str,
    object_type: str,
    object_id: Optional[int] = None,
    details: Optional[Any] = None,
) -> models.AuditEvent:
    event = models.AuditEvent(
        actor_id=actor.id if actor else None,
        action=action,
        object_type=object_type,
        object_id=object_id,
        details=json.dumps(details, ensure_ascii=False, default=str) if details is not None else None,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    return event


async def log_history(
    db: AsyncSession,
    supply_id: int,
    actor_id: int,
    source: str,
    field: str,
    old_value: Any,
    new_value: Any,
) -> models.SupplyHistory:
    row = models.SupplyHistory(
        supply_id=supply_id,
        actor_id=actor_id,
        source=source,
        field=field,
        old_value=None if old_value is None else str(old_value),
        new_value=None if new_value is None else str(new_value),
        created_at=datetime.utcnow(),
    )
    db.add(row)
    return row
