import json
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Date, DateTime, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.config import settings

TABLES = [
    ("users", models.User),
    ("suppliers", models.Supplier),
    ("storage_locations", models.StorageLocation),
    ("catalog_items", models.CatalogItem),
    ("supplies", models.Supply),
    ("supply_items", models.SupplyItem),
    ("supply_documents", models.SupplyDocument),
    ("supply_checks", models.SupplyCheck),
    ("discrepancies", models.Discrepancy),
    ("change_proposals", models.ChangeProposal),
    ("supply_comments", models.SupplyComment),
    ("notifications", models.Notification),
    ("audit_events", models.AuditEvent),
    ("supply_history", models.SupplyHistory),
]


def _row_to_dict(row: Any) -> dict:
    data = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        data[column.name] = value
    return data


async def create_backup(db: AsyncSession) -> dict:
    backup_root = Path(settings.BACKUP_DIR)
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y-%m-%d")
    target = backup_root / stamp
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    dump: dict[str, list] = {}
    for name, model in TABLES:
        result = await db.execute(select(model))
        dump[name] = [_row_to_dict(row) for row in result.scalars().all()]
    (target / "database.json").write_text(
        json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    docs_src = Path(settings.UPLOAD_DIR)
    docs_dst = target / "documents"
    if docs_src.exists():
        shutil.copytree(docs_src, docs_dst, dirs_exist_ok=True)
    else:
        docs_dst.mkdir(exist_ok=True)

    keep = settings.BACKUP_KEEP_DAYS
    existing = sorted([path for path in backup_root.iterdir() if path.is_dir()])
    while len(existing) > keep:
        shutil.rmtree(existing[0])
        existing.pop(0)

    return {
        "name": stamp,
        "path": str(target),
        "tables": {name: len(rows) for name, rows in dump.items()},
        "kept": [path.name for path in sorted(backup_root.iterdir()) if path.is_dir()],
    }


def _parse_value(column, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date) and isinstance(value, str):
        return date.fromisoformat(value[:10])
    return value


async def restore_backup(db: AsyncSession, name: str) -> dict:
    target = Path(settings.BACKUP_DIR) / name
    dump_file = target / "database.json"
    if not dump_file.exists():
        raise FileNotFoundError(f"Копия {name} не найдена")
    dump = json.loads(dump_file.read_text(encoding="utf-8"))

    for table_name, model in reversed(TABLES):
        await db.execute(delete(model))
    await db.flush()

    restored: dict[str, int] = {}
    for table_name, model in TABLES:
        rows = dump.get(table_name, [])
        for row in rows:
            payload = {
                column.name: _parse_value(column, row.get(column.name))
                for column in model.__table__.columns
            }
            db.add(model(**payload))
        restored[table_name] = len(rows)
    await db.commit()

    docs_src = target / "documents"
    docs_dst = Path(settings.UPLOAD_DIR)
    if docs_dst.exists():
        shutil.rmtree(docs_dst)
    if docs_src.exists():
        shutil.copytree(docs_src, docs_dst)
    else:
        docs_dst.mkdir(parents=True, exist_ok=True)

    return {"name": name, "tables": restored, "documents_restored": docs_src.exists()}


def list_backups() -> list[dict]:
    backup_root = Path(settings.BACKUP_DIR)
    if not backup_root.exists():
        return []
    items = []
    for path in sorted(backup_root.iterdir()):
        if path.is_dir():
            db_file = path / "database.json"
            items.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "has_database": db_file.exists(),
                    "has_documents": (path / "documents").exists(),
                }
            )
    return items
