"""Начальные учётки, справочники и наглядные демо-поставки с документами."""

from __future__ import annotations

import asyncio
import json
import struct
import sys
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from sqlalchemy import select

from app.config import settings
from app.constants import (
    HISTORY_CHECK,
    HISTORY_MANUAL,
    KIND_SHORTAGE,
    KIND_SURPLUS,
    NOTIFICATION_CHECK_ASSIGNED,
    NOTIFICATION_OVERDUE,
    NOTIFICATION_PROPOSAL_CREATED,
    NOTIFICATION_STATUS_CHANGED,
    PROPOSAL_PENDING,
    STATUS_CANCELLED,
    STATUS_CHECKED,
    STATUS_COMPLETED,
    STATUS_CREATED,
    STATUS_HAS_DISCREPANCIES,
    STATUS_IN_TRANSIT,
    STATUS_ON_CHECK,
)
from app.database import async_session
from app.models import (
    AuditEvent,
    CatalogItem,
    ChangeProposal,
    Discrepancy,
    Notification,
    StorageLocation,
    Supplier,
    Supply,
    SupplyCheck,
    SupplyComment,
    SupplyDocument,
    SupplyHistory,
    SupplyItem,
    User,
)
from app.security import hash_password
from docs_pdf import invoice_pdf, line_items_from_catalog, packing_list_pdf, torg12_pdf

USERS = [
    ("admin@alllove.ru", "Администратор", "admin", "admin123", "+7 831 000-10-00"),
    ("client1@alllove.ru", "Иванов Иван Иванович", "client", "client123", "+7 831 000-11-01"),
    ("client2@alllove.ru", "Петрова Анна Сергеевна", "client", "client123", "+7 831 000-11-02"),
    ("client3@alllove.ru", "Орлова Мария Дмитриевна", "client", "client123", "+7 831 000-11-03"),
    ("validator@alllove.ru", "Смирнов Алексей Викторович", "validator", "validator123", "+7 831 000-12-01"),
]

SUPPLIERS = [
    ("Ателье Нева", "+7 812 555-01-01", "Санкт-Петербург, наб. реки Фонтанки, 18"),
    ("Fashion House", "+7 495 555-02-02", "Москва, Павелецкая наб., 2"),
    ("Maison Luce", "+39 02 555 0303", "Милан, Via della Spiga, 9"),
    ("Шёлк Казани", "+7 843 555-04-04", "Казань, ул. Баумана, 44"),
    ("Nord Knit", "+7 812 555-05-05", "Выборг, швейный цех 3"),
]

LOCATIONS = [
    ("Склад AllLove", "warehouse", "Нижний Новгород, ул. Складская, 7"),
    ("Шоурум AllLove", "showroom", "Нижний Новгород, Большая Покровская, 12"),
    ("Шоурум у Кремля", "showroom", "Нижний Новгород, пл. Минина, 3"),
    ("Резервный склад", "warehouse", "Кстово, логистический парк, бокс 14"),
]

CATALOG = [
    ("AL-DR-001", "Платье «Ивушка»", "Платья", "M", "чёрный"),
    ("AL-DR-002", "Платье «Вечер на Волге»", "Платья", "S", "бордо"),
    ("AL-BL-010", "Блуза шёлковая", "Блузы", "S", "молочный"),
    ("AL-BL-011", "Блуза с бантом", "Блузы", "M", "пыльная роза"),
    ("AL-CT-020", "Пальто бежевое", "Верх", "L", "бежевый"),
    ("AL-CT-021", "Тренч «Осень»", "Верх", "M", "кэмел"),
    ("AL-JK-030", "Жакет приталенный", "Костюмы", "S", "графит"),
    ("AL-SK-031", "Юбка-карандаш", "Костюмы", "S", "графит"),
    ("AL-KN-040", "Джемпер кашемир", "Трикотаж", "M", "слоновая кость"),
    ("AL-KN-041", "Кардиган oversize", "Трикотаж", "L", "шоколад"),
    ("AL-AC-050", "Платок «AllLove»", "Аксессуары", "one", "золото"),
    ("AL-AC-051", "Ремень кожаный", "Аксессуары", "M", "коньяк"),
]


def _png(width: int = 320, height: int = 200, rgb: tuple[int, int, int] = (122, 46, 42)) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    rows = []
    for y in range(height):
        row = bytearray(b"\x00")
        for x in range(width):
            shade = 18 if (x // 16 + y // 16) % 2 == 0 else 0
            row.extend((max(0, rgb[0] - shade), max(0, rgb[1] - shade), max(0, rgb[2] - shade)))
        rows.append(bytes(row))
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _make_doc(kind: str, supply: Supply, row: dict, catalog: dict) -> tuple[str, str, bytes]:
    items = line_items_from_catalog(row["items"], catalog)
    issued = row.get("actual") or row["planned"]
    if kind == "nakladnaya":
        return (
            f"nakladnaya-{supply.number}.pdf",
            "application/pdf",
            torg12_pdf(
                number=supply.number,
                issued=issued,
                supplier_name=row["supplier"].name,
                supplier_address=row["supplier"].address or "",
                supplier_phone=row["supplier"].contact or "",
                location_name=row["location"].name,
                location_address=row["location"].address or "",
                items=items,
                received_by=row["responsible"].full_name,
            ),
        )
    if kind == "pack":
        return (
            f"upakovka-{supply.number}.pdf",
            "application/pdf",
            packing_list_pdf(
                number=supply.number,
                issued=issued,
                supplier_name=row["supplier"].name,
                location_name=row["location"].name,
                items=items,
            ),
        )
    if kind == "invoice":
        return (
            f"schet-{supply.number}.pdf",
            "application/pdf",
            invoice_pdf(
                number=supply.number,
                issued=issued,
                supplier_name=row["supplier"].name,
                supplier_address=row["supplier"].address or "",
                supplier_phone=row["supplier"].contact or "",
                items=items,
            ),
        )
    return (
        f"foto-korobki-{supply.number}.png",
        "image/png",
        _png(),
    )


def _save_doc(supply_id: int, name: str, content: bytes) -> Path:
    folder = Path(settings.UPLOAD_DIR) / str(supply_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(content)
    return path


async def _get(db, model, **kwargs):
    query = select(model)
    for key, value in kwargs.items():
        query = query.where(getattr(model, key) == value)
    return (await db.execute(query)).scalar_one()


async def seed() -> None:
    today = date.today()
    now = datetime.utcnow()
    async with async_session() as db:
        for email, name, role, password, phone in USERS:
            exists = await db.execute(select(User).where(User.email == email))
            if exists.scalar_one_or_none():
                continue
            db.add(
                User(
                    email=email,
                    full_name=name,
                    phone=phone,
                    hashed_password=hash_password(password),
                    role=role,
                    is_active=True,
                )
            )
        await db.flush()

        for name, contact, address in SUPPLIERS:
            exists = await db.execute(select(Supplier).where(Supplier.name == name))
            if exists.scalar_one_or_none():
                continue
            db.add(Supplier(name=name, contact=contact, address=address, is_active=True))

        for name, kind, address in LOCATIONS:
            exists = await db.execute(select(StorageLocation).where(StorageLocation.name == name))
            if exists.scalar_one_or_none():
                continue
            db.add(StorageLocation(name=name, type=kind, address=address, is_active=True))

        for sku, name, category, size, color in CATALOG:
            exists = await db.execute(select(CatalogItem).where(CatalogItem.sku == sku))
            if exists.scalar_one_or_none():
                continue
            db.add(
                CatalogItem(sku=sku, name=name, category=category, size=size, color=color, is_active=True)
            )
        await db.flush()

        ivan = await _get(db, User, email="client1@alllove.ru")
        anna = await _get(db, User, email="client2@alllove.ru")
        maria = await _get(db, User, email="client3@alllove.ru")
        validator = await _get(db, User, email="validator@alllove.ru")
        admin = await _get(db, User, email="admin@alllove.ru")

        neva = await _get(db, Supplier, name="Ателье Нева")
        fashion = await _get(db, Supplier, name="Fashion House")
        luce = await _get(db, Supplier, name="Maison Luce")
        silk = await _get(db, Supplier, name="Шёлк Казани")
        knit = await _get(db, Supplier, name="Nord Knit")

        warehouse = await _get(db, StorageLocation, name="Склад AllLove")
        showroom = await _get(db, StorageLocation, name="Шоурум AllLove")
        kremlin = await _get(db, StorageLocation, name="Шоурум у Кремля")

        sku = {}
        for code, *_rest in CATALOG:
            sku[code] = await _get(db, CatalogItem, sku=code)

        scenarios = [
            {
                "number": "DEMO-001",
                "status": STATUS_CREATED,
                "supplier": neva,
                "location": showroom,
                "planned": today + timedelta(days=10),
                "responsible": ivan,
                "creator": ivan,
                "items": [("AL-DR-002", 6), ("AL-BL-010", 8), ("AL-AC-050", 12)],
                "docs": ["nakladnaya", "photo"],
                "comments": [(ivan, "Ждём подтверждение цвета бордо от ателье.")],
            },
            {
                "number": "DEMO-002",
                "status": STATUS_IN_TRANSIT,
                "supplier": luce,
                "location": kremlin,
                "planned": today + timedelta(days=4),
                "responsible": anna,
                "creator": anna,
                "items": [("AL-CT-020", 4), ("AL-CT-021", 3), ("AL-KN-040", 10)],
                "docs": ["nakladnaya", "pack", "photo"],
                "comments": [(anna, "Машина выехала из Милана, трек ML-88421.")],
            },
            {
                "number": "DEMO-003",
                "status": STATUS_ON_CHECK,
                "supplier": fashion,
                "location": warehouse,
                "planned": today - timedelta(days=1),
                "responsible": ivan,
                "creator": ivan,
                "items": [("AL-JK-030", 5), ("AL-SK-031", 5), ("AL-BL-011", 7)],
                "docs": ["nakladnaya", "pack"],
                "comments": [(validator, "Коробки на рампе, начинаю сверку.")],
                "overdue": True,
            },
            {
                "number": "DEMO-004",
                "status": STATUS_ON_CHECK,
                "supplier": silk,
                "location": showroom,
                "planned": today + timedelta(days=1),
                "responsible": maria,
                "creator": maria,
                "items": [("AL-DR-001", 9), ("AL-AC-050", 9)],
                "docs": ["nakladnaya", "photo"],
                "comments": [(maria, "Просьба сверить платки отдельно — они в отдельном коробе.")],
            },
            {
                "number": "DEMO-005",
                "status": STATUS_HAS_DISCREPANCIES,
                "supplier": knit,
                "location": warehouse,
                "planned": today - timedelta(days=2),
                "actual": today - timedelta(days=1),
                "responsible": anna,
                "creator": ivan,
                "items": [("AL-KN-040", 20), ("AL-KN-041", 8)],
                "facts": {"AL-KN-040": 17, "AL-KN-041": 9},
                "docs": ["nakladnaya", "pack"],
                "comments": [
                    (validator, "Недостача трёх джемперов, кардиганов на один больше."),
                    (anna, "Запросила у Nord Knit довоз завтра."),
                ],
                "overdue": True,
            },
            {
                "number": "DEMO-006",
                "status": STATUS_CHECKED,
                "supplier": neva,
                "location": showroom,
                "planned": today - timedelta(days=3),
                "actual": today - timedelta(days=3),
                "responsible": ivan,
                "creator": ivan,
                "items": [("AL-DR-001", 4), ("AL-BL-010", 4), ("AL-AC-051", 4)],
                "facts": {"AL-DR-001": 4, "AL-BL-010": 4, "AL-AC-051": 4},
                "docs": ["nakladnaya"],
                "comments": [(validator, "Совпало с накладной, можно выставлять в зал.")],
            },
            {
                "number": "DEMO-007",
                "status": STATUS_COMPLETED,
                "supplier": fashion,
                "location": kremlin,
                "planned": today - timedelta(days=12),
                "actual": today - timedelta(days=11),
                "responsible": anna,
                "creator": anna,
                "items": [("AL-DR-002", 3), ("AL-CT-021", 2), ("AL-AC-050", 6)],
                "facts": {"AL-DR-002": 3, "AL-CT-021": 2, "AL-AC-050": 6},
                "docs": ["nakladnaya", "pack"],
                "comments": [(anna, "Коллекция уже в витрине у Кремля.")],
            },
            {
                "number": "DEMO-008",
                "status": STATUS_CANCELLED,
                "supplier": luce,
                "location": showroom,
                "planned": today + timedelta(days=20),
                "responsible": maria,
                "creator": maria,
                "items": [("AL-CT-020", 2)],
                "docs": ["invoice"],
                "comments": [(maria, "Отменили: пальто ушло в другую партию Maison Luce.")],
            },
            {
                "number": "DEMO-009",
                "status": STATUS_IN_TRANSIT,
                "supplier": silk,
                "location": warehouse,
                "planned": today - timedelta(days=4),
                "responsible": maria,
                "creator": ivan,
                "items": [("AL-DR-001", 11), ("AL-BL-011", 11), ("AL-AC-050", 11)],
                "docs": ["nakladnaya", "photo"],
                "comments": [(ivan, "Задержка на сортировке в Казани.")],
                "overdue": True,
                "proposal": True,
            },
            {
                "number": "DEMO-010",
                "status": STATUS_CREATED,
                "supplier": fashion,
                "location": showroom,
                "planned": today + timedelta(days=18),
                "responsible": anna,
                "creator": maria,
                "items": [("AL-JK-030", 6), ("AL-SK-031", 6), ("AL-KN-041", 5)],
                "docs": ["invoice"],
                "comments": [(maria, "Черновик капсулы к новогодней витрине.")],
            },
        ]

        demo = await db.execute(select(Supply).where(Supply.number == "DEMO-001"))
        if demo.scalar_one_or_none():
            updated = 0
            for row in scenarios:
                supply = await _get(db, Supply, number=row["number"])
                docs = await db.execute(select(SupplyDocument).where(SupplyDocument.supply_id == supply.id))
                for doc in docs.scalars().all():
                    kind = None
                    if doc.original_name.startswith("nakladnaya-"):
                        kind = "nakladnaya"
                    elif doc.original_name.startswith("upakovka-"):
                        kind = "pack"
                    elif doc.original_name.startswith("schet-"):
                        kind = "invoice"
                    if not kind:
                        continue
                    name, ctype, data = _make_doc(kind, supply, row, sku)
                    Path(doc.filename).write_bytes(data)
                    doc.size = len(data)
                    doc.content_type = ctype
                    doc.original_name = name
                    updated += 1
            await db.commit()
            print(f"Документы демо-поставок обновлены по форме ТОРГ-12 ({updated} файлов)")
            return

        created: dict[str, Supply] = {}
        for row in scenarios:
            supply = Supply(
                number=row["number"],
                supplier_id=row["supplier"].id,
                location_id=row["location"].id,
                planned_date=row["planned"],
                actual_date=row.get("actual"),
                status=row["status"],
                responsible_id=row["responsible"].id,
                created_by_id=row["creator"].id,
                version=1,
                created_at=now - timedelta(days=8),
                updated_at=now,
            )
            db.add(supply)
            await db.flush()
            created[row["number"]] = supply

            item_map: dict[str, SupplyItem] = {}
            for code, qty in row["items"]:
                item = SupplyItem(
                    supply_id=supply.id,
                    catalog_item_id=sku[code].id,
                    planned_qty=qty,
                    actual_qty=(row.get("facts") or {}).get(code),
                )
                db.add(item)
                await db.flush()
                item_map[code] = item

            db.add(
                SupplyHistory(
                    supply_id=supply.id,
                    actor_id=row["creator"].id,
                    source=HISTORY_MANUAL,
                    field="created",
                    new_value=supply.number,
                    created_at=now - timedelta(days=8),
                )
            )
            if row["status"] != STATUS_CREATED:
                db.add(
                    SupplyHistory(
                        supply_id=supply.id,
                        actor_id=row["creator"].id,
                        source=HISTORY_MANUAL,
                        field="status",
                        old_value=STATUS_CREATED,
                        new_value=row["status"],
                        created_at=now - timedelta(days=3),
                    )
                )

            for kind in row["docs"]:
                name, ctype, data = _make_doc(kind, supply, row, sku)
                path = _save_doc(supply.id, name, data)
                db.add(
                    SupplyDocument(
                        supply_id=supply.id,
                        filename=str(path),
                        original_name=name,
                        content_type=ctype,
                        size=len(data),
                        uploaded_by_id=row["creator"].id,
                        created_at=now - timedelta(days=7),
                    )
                )

            for author, text in row.get("comments", []):
                db.add(
                    SupplyComment(
                        supply_id=supply.id,
                        author_id=author.id,
                        text=text,
                        created_at=now - timedelta(hours=6),
                    )
                )

            db.add(
                AuditEvent(
                    actor_id=row["creator"].id,
                    action="create_supply",
                    object_type="supply",
                    object_id=supply.id,
                    details=json.dumps({"number": supply.number}, ensure_ascii=False),
                    created_at=now - timedelta(days=8),
                )
            )

            if row["status"] in {STATUS_ON_CHECK, STATUS_HAS_DISCREPANCIES, STATUS_CHECKED, STATUS_COMPLETED}:
                db.add(
                    Notification(
                        user_id=row["responsible"].id,
                        type=NOTIFICATION_STATUS_CHANGED,
                        title="Изменён статус поставки",
                        message=f"Поставка {supply.number} сейчас: {row['status']}.",
                        supply_id=supply.id,
                        is_read=row["status"] == STATUS_COMPLETED,
                        created_at=now - timedelta(days=2),
                    )
                )
            if row["status"] == STATUS_ON_CHECK:
                db.add(
                    Notification(
                        user_id=validator.id,
                        type=NOTIFICATION_CHECK_ASSIGNED,
                        title="Поставка направлена на проверку",
                        message=f"Поставка {supply.number} ожидает сверки.",
                        supply_id=supply.id,
                        is_read=False,
                        created_at=now - timedelta(hours=5),
                    )
                )
            if row.get("overdue"):
                db.add(
                    Notification(
                        user_id=row["responsible"].id,
                        type=NOTIFICATION_OVERDUE,
                        title="Просрочена поставка",
                        message=f"Плановая дата {supply.number} уже прошла.",
                        supply_id=supply.id,
                        is_read=False,
                        created_at=now - timedelta(days=1),
                    )
                )

            facts = row.get("facts")
            if facts and row["status"] in {STATUS_HAS_DISCREPANCIES, STATUS_CHECKED, STATUS_COMPLETED}:
                has_diff = any(facts[code] != qty for code, qty in row["items"] if code in facts)
                check = SupplyCheck(
                    supply_id=supply.id,
                    validator_id=validator.id,
                    result="discrepancy" if has_diff else "match",
                    comment=row["comments"][0][1] if row.get("comments") else None,
                    created_at=now - timedelta(days=1),
                )
                db.add(check)
                await db.flush()
                db.add(
                    SupplyHistory(
                        supply_id=supply.id,
                        actor_id=validator.id,
                        source=HISTORY_CHECK,
                        field="check_result",
                        new_value=check.result,
                        created_at=now - timedelta(days=1),
                    )
                )
                for code, planned in row["items"]:
                    actual = facts.get(code)
                    if actual is None or actual == planned:
                        continue
                    diff = actual - planned
                    db.add(
                        Discrepancy(
                            supply_id=supply.id,
                            item_id=item_map[code].id,
                            check_id=check.id,
                            planned_qty=planned,
                            actual_qty=actual,
                            difference=diff,
                            kind=KIND_SURPLUS if diff > 0 else KIND_SHORTAGE,
                            comment="сверка демо-партии",
                        )
                    )

            if row.get("proposal"):
                db.add(
                    ChangeProposal(
                        supply_id=supply.id,
                        author_id=anna.id,
                        payload=json.dumps({"planned_date": (today + timedelta(days=3)).isoformat()}, ensure_ascii=False),
                        status=PROPOSAL_PENDING,
                        base_version=supply.version,
                        comment="Перенести срок: задержка на сортировке.",
                        created_at=now - timedelta(hours=3),
                    )
                )
                db.add(
                    Notification(
                        user_id=row["responsible"].id,
                        type=NOTIFICATION_PROPOSAL_CREATED,
                        title="Новое предложение изменения",
                        message=f"По поставке {supply.number} коллега предложила новую дату.",
                        supply_id=supply.id,
                        is_read=False,
                        created_at=now - timedelta(hours=3),
                    )
                )

        db.add(
            AuditEvent(
                actor_id=admin.id,
                action="seed_demo",
                object_type="system",
                object_id=None,
                details="Демо-витрина поставок AllLove",
                created_at=now,
            )
        )
        await db.commit()
        print("Начальные данные и 10 демо-поставок с документами готовы")


if __name__ == "__main__":
    asyncio.run(seed())
