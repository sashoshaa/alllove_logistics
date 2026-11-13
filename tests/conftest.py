import io
from datetime import date, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.security import hash_password
from app import models
from app import database as database_module
from app.config import settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def app_client(tmp_path, monkeypatch):
    settings.UPLOAD_DIR = str(tmp_path / "documents")
    settings.BACKUP_DIR = str(tmp_path / "backups")
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.BACKUP_DIR).mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database_module.engine = engine
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_maker() as db:
        users = [
            models.User(
                email="admin@example.com",
                full_name="Администратор",
                hashed_password=hash_password("test123"),
                role="admin",
                is_active=True,
            ),
            models.User(
                email="client1@example.com",
                full_name="Клиент Один",
                hashed_password=hash_password("test123"),
                role="client",
                is_active=True,
            ),
            models.User(
                email="client2@example.com",
                full_name="Клиент Два",
                hashed_password=hash_password("test123"),
                role="client",
                is_active=True,
            ),
            models.User(
                email="validator@example.com",
                full_name="Валидатор",
                hashed_password=hash_password("test123"),
                role="validator",
                is_active=True,
            ),
            models.User(
                email="blocked@example.com",
                full_name="Заблокированный",
                hashed_password=hash_password("test123"),
                role="client",
                is_active=False,
            ),
        ]
        db.add_all(users)
        db.add(models.Supplier(name="Test Supplier", contact="supplier@example.com", address="Москва", is_active=True))
        db.add(models.StorageLocation(name="Склад 1", address="Складской проезд 1", type="warehouse", is_active=True))
        db.add(models.StorageLocation(name="Шоурум AllLove", address="Тверская 1", type="showroom", is_active=True))
        db.add(models.CatalogItem(sku="SKU-001", name="Платье чёрное", category="Платья", size="M", color="чёрный", is_active=True))
        db.add(models.CatalogItem(sku="SKU-002", name="Блуза белая", category="Блузы", size="S", color="белый", is_active=True))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


async def auth_header(client: AsyncClient, email: str, password: str = "test123") -> dict:
    response = await client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def create_supply(client: AsyncClient, headers: dict, **overrides) -> dict:
    payload = {
        "supplier_id": 1,
        "location_id": 1,
        "planned_date": (date.today() + timedelta(days=1)).isoformat(),
        "responsible_id": 2,
        "items": [
            {"catalog_item_id": 1, "quantity": 10},
            {"catalog_item_id": 2, "quantity": 5},
        ],
    }
    payload.update(overrides)
    response = await client.post("/supplies", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def tiny_pdf() -> io.BytesIO:
    return io.BytesIO(b"%PDF-1.4 tiny")
