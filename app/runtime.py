from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.config import BASE_DIR, settings

log = logging.getLogger("alllove.runtime")


def in_tests() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("ALLLOVE_TESTING") == "1")


def alembic_config() -> Config:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "alembic"))
    return config


def apply_migrations(stamp_existing: bool = False) -> None:
    config = alembic_config()
    if stamp_existing:
        command.stamp(config, "head")
        return
    command.upgrade(config, "head")


def _schema_state(sync_conn) -> tuple[bool, str | None]:
    inspector = inspect(sync_conn)
    has_users = inspector.has_table("users")
    if not inspector.has_table("alembic_version"):
        return has_users, None
    row = sync_conn.execute(text("select version_num from alembic_version")).first()
    return has_users, row[0] if row and row[0] else None


async def prepare_schema() -> None:
    from app.database import engine

    heads = set(ScriptDirectory.from_config(alembic_config()).get_heads())
    async with engine.connect() as connection:
        has_users, version = await connection.run_sync(_schema_state)

    if version and version in heads:
        return

    await engine.dispose()
    stamp = has_users and not version
    log.info("Применяю схему базы (%s)", "stamp" if stamp else "upgrade")
    await asyncio.to_thread(apply_migrations, stamp)


def cert_paths() -> tuple[Path, Path]:
    folder = Path(settings.SSL_DIR)
    return folder / "alllove.crt", folder / "alllove.key"
