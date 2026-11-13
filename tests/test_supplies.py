from datetime import date, timedelta

from tests.conftest import auth_header, create_supply, tiny_pdf


async def test_6_4_1_create_supply(app_client):
    client = await auth_header(app_client, "client1@example.com")
    planned = (date.today() + timedelta(days=1)).isoformat()
    body = await create_supply(app_client, client, planned_date=planned)
    assert body["number"].startswith("SUP-")
    assert body["status"] == "created"
    assert body["responsible_id"] == 2
    assert body["created_by_id"] == 2
    assert len(body["items"]) == 2
    listed = await app_client.get("/supplies", headers=client)
    assert any(row["id"] == body["id"] for row in listed.json())


async def test_6_4_2_invalid_create(app_client):
    client = await auth_header(app_client, "client1@example.com")
    listed_before = await app_client.get("/supplies", headers=client)
    count = len(listed_before.json())

    missing_responsible = await app_client.post(
        "/supplies",
        json={
            "supplier_id": 1,
            "location_id": 1,
            "planned_date": (date.today() + timedelta(days=1)).isoformat(),
            "items": [{"catalog_item_id": 1, "quantity": 1}],
        },
        headers=client,
    )
    assert missing_responsible.status_code == 422

    negative = await app_client.post(
        "/supplies",
        json={
            "supplier_id": 1,
            "location_id": 1,
            "planned_date": (date.today() + timedelta(days=1)).isoformat(),
            "responsible_id": 2,
            "items": [{"catalog_item_id": 1, "quantity": -3}],
        },
        headers=client,
    )
    assert negative.status_code == 422

    listed_after = await app_client.get("/supplies", headers=client)
    assert len(listed_after.json()) == count


async def test_6_5_1_search_and_filters(app_client):
    client = await auth_header(app_client, "client1@example.com")
    first = await create_supply(app_client, client)
    await create_supply(
        app_client,
        client,
        planned_date=(date.today() + timedelta(days=5)).isoformat(),
        location_id=2,
    )
    by_number = await app_client.get(f"/supplies?search={first['number']}", headers=client)
    assert [row["number"] for row in by_number.json()] == [first["number"]]

    by_sku = await app_client.get("/supplies?search=SKU-001", headers=client)
    assert len(by_sku.json()) >= 1

    sorted_rows = await app_client.get("/supplies?sort=planned_date&order=asc", headers=client)
    dates = [row["planned_date"] for row in sorted_rows.json()]
    assert dates == sorted(dates)

    by_location = await app_client.get("/supplies?location_id=2", headers=client)
    assert {row["location_id"] for row in by_location.json()} == {2}
    by_supplier = await app_client.get("/supplies?supplier_id=1", headers=client)
    assert all(row["supplier_id"] == 1 for row in by_supplier.json())
    by_responsible = await app_client.get("/supplies?responsible_id=2", headers=client)
    assert all(row["responsible_id"] == 2 for row in by_responsible.json())
    page = await app_client.get("/supplies?limit=1&offset=0&sort=id&order=asc", headers=client)
    assert page.status_code == 200
    assert len(page.json()) == 1
    assert page.headers.get("x-total-count")


async def test_6_5_2_card_and_forbidden_action(app_client):
    client = await auth_header(app_client, "client1@example.com")
    validator = await auth_header(app_client, "validator@example.com")
    supply = await create_supply(app_client, client)
    card = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    assert card.status_code == 200
    body = card.json()
    assert body["status"] == "created"
    assert body["items"]
    assert "planned_date" in body

    forbidden = await app_client.patch(
        f"/supplies/{supply['id']}",
        json={"planned_date": (date.today() + timedelta(days=10)).isoformat()},
        headers=validator,
    )
    assert forbidden.status_code == 403
    unchanged = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    assert unchanged.json()["planned_date"] == supply["planned_date"]


async def test_6_11_repeat_supply(app_client):
    client = await auth_header(app_client, "client1@example.com")
    source = await create_supply(app_client, client)
    files = {"file": ("invoice.pdf", tiny_pdf(), "application/pdf")}
    uploaded = await app_client.post(
        f"/supplies/{source['id']}/documents",
        files=files,
        headers=client,
    )
    assert uploaded.status_code == 201

    missing = await app_client.post(f"/supplies/{source['id']}/repeat", json={}, headers=client)
    assert missing.status_code == 422

    new_date = (date.today() + timedelta(days=12)).isoformat()
    repeated = await app_client.post(
        f"/supplies/{source['id']}/repeat",
        json={"planned_date": new_date, "responsible_id": 3},
        headers=client,
    )
    assert repeated.status_code == 201
    body = repeated.json()
    assert body["number"] != source["number"]
    assert body["status"] == "created"
    assert body["supplier_id"] == source["supplier_id"]
    assert body["location_id"] == source["location_id"]
    assert body["responsible_id"] == 3
    assert body["planned_date"] == new_date
    assert len(body["items"]) == 2
    assert body["documents"] == []

    original = await app_client.get(f"/supplies/{source['id']}", headers=client)
    assert original.json()["number"] == source["number"]
    assert original.json()["responsible_id"] == source["responsible_id"]
    docs = await app_client.get(f"/supplies/{source['id']}/documents", headers=client)
    assert len(docs.json()) == 1
