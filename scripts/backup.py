"""Ежедневная копия базы и файлов документов (ФТ-12)."""

import asyncio

from app.database import async_session
from app.services.backup import create_backup, list_backups


async def main() -> None:
    async with async_session() as db:
        result = await create_backup(db)
        print("Создана копия:", result)
        print("Хранятся:", list_backups())


if __name__ == "__main__":
    asyncio.run(main())
