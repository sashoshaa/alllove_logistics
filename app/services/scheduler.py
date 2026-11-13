from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.database import async_session
from app.services.backup import create_backup, list_backups

log = logging.getLogger("alllove.backup")


def seconds_until_hour(hour: int, now: datetime | None = None) -> float:
    current = now or datetime.now()
    target = current.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return max(1.0, (target - current).total_seconds())


async def maybe_daily_backup() -> dict | None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    existing = {item["name"] for item in list_backups()}
    if today in existing:
        return None
    async with async_session() as db:
        result = await create_backup(db)
        log.info("Создана дневная копия %s", result.get("name"))
        return result


async def backup_loop() -> None:
    await asyncio.sleep(2)
    try:
        await maybe_daily_backup()
    except Exception:
        log.exception("Не удалось создать копию при запуске")
    while True:
        await asyncio.sleep(seconds_until_hour(settings.BACKUP_HOUR))
        try:
            await maybe_daily_backup()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Не удалось создать дневную копию")
