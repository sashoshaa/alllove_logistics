from tests.conftest import auth_header, create_supply


async def test_6_2_1_create_and_edit_directories(app_client):
    admin = await auth_header(app_client, "admin@example.com")
    supplier = await app_client.post(
        "/suppliers",
        json={"name": "Новый поставщик", "contact": "n@example.com", "address": "Казань"},
        headers=admin,
    )
    assert supplier.status_code == 201
    renamed = await app_client.patch(
        f"/suppliers/{supplier.json()['id']}",
        json={"name": "Поставщик обновлённый"},
        headers=admin,
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Поставщик обновлённый"

    location = await app_client.post(
        "/locations",
        json={"name": "Склад 2", "type": "warehouse", "address": "Адрес 2"},
        headers=admin,
    )
    assert location.status_code == 201
    catalog = await app_client.post(
        "/catalog",
        json={"sku": "SKU-100", "name": "Юбка", "category": "Низ", "size": "M", "color": "синий"},
        headers=admin,
    )
    assert catalog.status_code == 201

    client = await auth_header(app_client, "client1@example.com")
    visible = await app_client.get("/suppliers", headers=client)
    names = [row["name"] for row in visible.json()]
    assert "Поставщик обновлённый" in names


async def test_6_2_2_inactive_and_permissions(app_client):
    admin = await auth_header(app_client, "admin@example.com")
    client = await auth_header(app_client, "client1@example.com")
    await create_supply(app_client, client)

    delete_used = await app_client.delete("/suppliers/1", headers=admin)
    assert delete_used.status_code == 400

    deactivate = await app_client.patch("/suppliers/1", json={"is_active": False}, headers=admin)
    assert deactivate.status_code == 200

    create_with_inactive = await app_client.post(
        "/supplies",
        json={
            "supplier_id": 1,
            "location_id": 1,
            "planned_date": "2026-12-20",
            "responsible_id": 2,
            "items": [{"catalog_item_id": 1, "quantity": 1}],
        },
        headers=client,
    )
    assert create_with_inactive.status_code == 400

    forbidden = await app_client.post(
        "/suppliers",
        json={"name": "Клиентский поставщик"},
        headers=client,
    )
    assert forbidden.status_code == 403

    listed = await app_client.get("/suppliers", headers=client)
    assert all(row["id"] != 1 or row["is_active"] for row in listed.json())
    assert 1 not in [row["id"] for row in listed.json()]
