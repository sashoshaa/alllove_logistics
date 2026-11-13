from datetime import datetime

from sqlalchemy import create_engine, inspect, text

from app.runtime import apply_migrations, in_tests
from app.services.perf import percentile
from app.services.scheduler import seconds_until_hour
from scripts.make_certs import make_certs


def test_percentile_and_schedule_window():
    assert percentile([10, 20, 30, 40, 50], 50) == 30
    assert percentile([10, 20, 30, 40, 50], 95) == 48
    now = datetime(2026, 11, 13, 4, 0, 0)
    assert seconds_until_hour(3, now) == 23 * 3600
    assert in_tests() is True


def test_alembic_upgrade_creates_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "mig.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    from app import config as config_module

    monkeypatch.setattr(config_module.settings, "DATABASE_URL", url)
    apply_migrations()
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as connection:
        tables = inspect(connection).get_table_names()
        version = connection.execute(text("select version_num from alembic_version")).scalar_one()
    engine.dispose()
    assert "users" in tables
    assert "supplies" in tables
    assert "supply_history" in tables
    assert version == "0001_initial"


def test_make_certs(tmp_path):
    cert, key = make_certs(tmp_path)
    assert cert.exists() and key.exists()
    assert "BEGIN CERTIFICATE" in cert.read_text()
    assert "PRIVATE KEY" in key.read_text()
