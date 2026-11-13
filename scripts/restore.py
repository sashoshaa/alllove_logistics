"""Восстановление согласованной пары «база + файлы» из дневной копии."""

import asyncio
import sys

from app.database import async_session
from app.services.backup import list_backups, restore_backup


async def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else None
    copies = list_backups()
    if not copies:
        print("Копий нет. Сначала: python scripts/backup.py")
        return
    if not name:
        name = copies[-1]["name"]
        print(f"Имя не указано, берём последнюю копию: {name}")
    async with async_session() as db:
        result = await restore_backup(db, name)
        print("Восстановлено:", result)


if __name__ == "__main__":
    asyncio.run(main())
