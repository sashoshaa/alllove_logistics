"""НФТ-03 / 6.16: 5000 поставок, 20 одновременных пользователей, p95 списка и карточки."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ALLLOVE_TESTING", "1")
os.environ.setdefault("ALLLOVE_BACKUP_SCHEDULE_ENABLED", "false")

from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models
from app.database import Base
from app.main import app
from app.security import hash_password
from app.services.perf import percentile

RESULT_PATH = ROOT / "docs" / "load_protocol.md"


async def seed(db: AsyncSession, supplies: int, users: int) -> tuple[str, int]:
    password = hash_password("load123")
    people = [
        models.User(
            email="admin@load.local",
            full_name="Администратор нагрузки",
            hashed_password=password,
            role="admin",
            is_active=True,
        ),
        models.User(
            email="validator@load.local",
            full_name="Валидатор нагрузки",
            hashed_password=password,
            role="validator",
            is_active=True,
        ),
    ]
    client_count = max(1, users - 2)
    for index in range(client_count):
        people.append(
            models.User(
                email=f"client{index + 1:02d}@load.local",
                full_name=f"Сотрудник {index + 1}",
                hashed_password=password,
                role="client",
                is_active=True,
            )
        )
    db.add_all(people)
    db.add(models.Supplier(name="Load Supplier", contact="load@example.com", is_active=True))
    db.add(models.StorageLocation(name="Склад нагрузки", type="warehouse", is_active=True))
    db.add(models.CatalogItem(sku="LOAD-001", name="Платье нагрузка", category="Платья", size="M", color="чёрный", is_active=True))
    await db.commit()

    supplier_id = (await db.execute(select(models.Supplier.id))).scalar_one()
    location_id = (await db.execute(select(models.StorageLocation.id))).scalar_one()
    catalog_id = (await db.execute(select(models.CatalogItem.id))).scalar_one()
    client_ids = list(
        (await db.execute(select(models.User.id).where(models.User.role == "client"))).scalars()
    )
    today = date.today()
    now = datetime.utcnow()
    supply_rows = []
    item_rows = []
    for index in range(supplies):
        supply_rows.append(
            {
                "number": f"LOAD-{index + 1:05d}",
                "supplier_id": supplier_id,
                "location_id": location_id,
                "planned_date": today + timedelta(days=index % 30),
                "status": "created",
                "responsible_id": client_ids[index % len(client_ids)],
                "created_by_id": client_ids[0],
                "version": 1,
                "created_at": now,
                "updated_at": now,
            }
        )
    await db.execute(insert(models.Supply), supply_rows)
    await db.flush()
    ids = list((await db.execute(select(models.Supply.id).order_by(models.Supply.id))).scalars())
    for supply_id in ids:
        item_rows.append(
            {
                "supply_id": supply_id,
                "catalog_item_id": catalog_id,
                "planned_qty": 3,
            }
        )
    await db.execute(insert(models.SupplyItem), item_rows)
    await db.commit()
    return "client01@load.local", ids[0]


async def measure(client: AsyncClient, headers: dict, supply_id: int, repeats: int) -> tuple[list[float], list[float]]:
    lists: list[float] = []
    cards: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        listed = await client.get(
            "/supplies",
            headers=headers,
            params={"sort": "id", "order": "desc", "limit": 50, "offset": 0},
        )
        lists.append((time.perf_counter() - started) * 1000)
        listed.raise_for_status()
        started = time.perf_counter()
        card = await client.get(f"/supplies/{supply_id}", headers=headers)
        cards.append((time.perf_counter() - started) * 1000)
        card.raise_for_status()
    return lists, cards


def write_protocol(payload: dict) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        "\n".join(
            [
                "# Протокол нагрузочной проверки AllLove Logistics",
                "",
                f"Дата: {payload['when']}",
                f"Стенд: {payload['db']}",
                f"Поставок: {payload['supplies']}",
                f"Одновременных сессий: {payload['users']}",
                "",
                "| Операция | p50, мс | p95, мс | max, мс | Норматив |",
                "|---|---:|---:|---:|---|",
                f"| Список | {payload['list_p50']:.0f} | {payload['list_p95']:.0f} | {payload['list_max']:.0f} | список ≤ 3000 мс; p95 сервера ≤ 2000 мс |",
                f"| Карточка | {payload['card_p50']:.0f} | {payload['card_p95']:.0f} | {payload['card_max']:.0f} | карточка ≤ 3000 мс; p95 сервера ≤ 2000 мс |",
                "",
                f"Ошибок: {payload['errors']}.",
                f"Вывод: {payload['verdict']}.",
                "",
            ]
        ),
        encoding="utf-8",
    )


async def run(supplies: int, users: int, repeats: int, db_url: str) -> dict:
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        if db_url.startswith("sqlite"):
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA synchronous=OFF"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as db:
        email, supply_id = await seed(db, supplies, users)

    from app.database import get_db

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    list_times: list[float] = []
    card_times: list[float] = []
    errors = 0
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post("/auth/login", data={"username": email, "password": "load123"})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        sessions = [
            measure(client, headers, supply_id, repeats) for _ in range(users)
        ]
        results = await asyncio.gather(*sessions, return_exceptions=True)
        for item in results:
            if isinstance(item, Exception):
                errors += 1
                continue
            lists, cards = item
            list_times.extend(lists)
            card_times.extend(cards)
    app.dependency_overrides.clear()
    await engine.dispose()

    payload = {
        "when": datetime.now().isoformat(timespec="seconds"),
        "db": db_url,
        "supplies": supplies,
        "users": users,
        "list_p50": percentile(list_times, 50),
        "list_p95": percentile(list_times, 95),
        "list_max": max(list_times) if list_times else 0,
        "card_p50": percentile(card_times, 50),
        "card_p95": percentile(card_times, 95),
        "card_max": max(card_times) if card_times else 0,
        "errors": errors,
    }
    ok = payload["list_p95"] <= 2000 and payload["card_p95"] <= 2000 and errors == 0
    payload["verdict"] = "норматив выдержан" if ok else "норматив не выдержан, требуется разбор стенда"
    write_protocol(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplies", type=int, default=5000)
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--db",
        default=f"sqlite+aiosqlite:///{ROOT / 'storage' / 'load.db'}",
    )
    args = parser.parse_args()
    Path(ROOT / "storage").mkdir(parents=True, exist_ok=True)
    payload = asyncio.run(run(args.supplies, args.users, args.repeats, args.db))
    print(
        f"список p95={payload['list_p95']:.0f} мс, карточка p95={payload['card_p95']:.0f} мс, "
        f"ошибок {payload['errors']}, {payload['verdict']}"
    )
    print("Протокол:", RESULT_PATH)


if __name__ == "__main__":
    main()
