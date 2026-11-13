from datetime import date, timedelta

from tests.conftest import auth_header, create_supply, tiny_pdf


async def _move_to_check(client, headers, supply_id):
    first = await client.post(
        f"/supplies/{supply_id}/status",
        json={"status": "in_transit"},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    second = await client.post(
        f"/supplies/{supply_id}/status",
        json={"status": "on_check"},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    return second.json()


async def test_6_6_1_matching_check(app_client):
    client = await auth_header(app_client, "client1@example.com")
    validator = await auth_header(app_client, "validator@example.com")
    supply = await create_supply(app_client, client)
    await _move_to_check(app_client, client, supply["id"])
    current = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    items = current.json()["items"]
    checked = await app_client.post(
        f"/supplies/{supply['id']}/check",
        json={
            "items": [
                {"item_id": items[0]["id"], "actual_qty": items[0]["planned_qty"]},
                {"item_id": items[1]["id"], "actual_qty": items[1]["planned_qty"]},
            ]
        },
        headers=validator,
    )
    assert checked.status_code == 200, checked.text
    body = checked.json()
    assert body["status"] == "checked"
    assert {item["actual_qty"] for item in body["items"]} == {10, 5}
    assert all(item["planned_qty"] in {10, 5} for item in body["items"])


async def test_6_6_2_discrepancies(app_client):
    client = await auth_header(app_client, "client1@example.com")
    validator = await auth_header(app_client, "validator@example.com")
    supply = await create_supply(app_client, client)
    await _move_to_check(app_client, client, supply["id"])
    current = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    items = sorted(current.json()["items"], key=lambda row: row["catalog_item_id"])
    checked = await app_client.post(
        f"/supplies/{supply['id']}/check",
        json={
            "items": [
                {"item_id": items[0]["id"], "actual_qty": 8},
                {"item_id": items[1]["id"], "actual_qty": 6},
            ],
            "comment": "недостача и излишек",
        },
        headers=validator,
    )
    assert checked.status_code == 200, checked.text
    assert checked.json()["status"] == "has_discrepancies"
    diffs = {item["catalog_item_id"]: item["difference"] for item in checked.json()["items"]}
    assert diffs[1] == -2
    assert diffs[2] == 1
    notes = await app_client.get("/notifications", headers=client)
    assert any("провер" in row["title"].lower() or "статус" in row["title"].lower() or "расхожд" in row["message"].lower() for row in notes.json())

    forbidden = await app_client.post(
        f"/supplies/{supply['id']}/check",
        json={"items": [{"item_id": items[0]["id"], "actual_qty": 8}, {"item_id": items[1]["id"], "actual_qty": 6}]},
        headers=client,
    )
    assert forbidden.status_code == 403


async def test_6_14_status_rules(app_client):
    client = await auth_header(app_client, "client1@example.com")
    validator = await auth_header(app_client, "validator@example.com")
    supply = await create_supply(app_client, client)
    skip = await app_client.post(
        f"/supplies/{supply['id']}/status",
        json={"status": "completed"},
        headers=client,
    )
    assert skip.status_code == 400
    still = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    assert still.json()["status"] == "created"

    await _move_to_check(app_client, client, supply["id"])
    unauthorized = await app_client.post(
        f"/supplies/{supply['id']}/status",
        json={"status": "checked"},
        headers=client,
    )
    assert unauthorized.status_code == 400

    current = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    items = current.json()["items"]
    ok = await app_client.post(
        f"/supplies/{supply['id']}/check",
        json={
            "items": [
                {"item_id": items[0]["id"], "actual_qty": items[0]["planned_qty"]},
                {"item_id": items[1]["id"], "actual_qty": items[1]["planned_qty"]},
            ]
        },
        headers=validator,
    )
    assert ok.json()["status"] == "checked"
    done = await app_client.post(
        f"/supplies/{supply['id']}/status",
        json={"status": "completed"},
        headers=client,
    )
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    history = await app_client.get(f"/supplies/{supply['id']}/history", headers=client)
    fields = [row["field"] for row in history.json()]
    assert "status" in fields


async def test_6_13_documents(app_client):
    client = await auth_header(app_client, "client1@example.com")
    supply = await create_supply(app_client, client)
    pdf = await app_client.post(
        f"/supplies/{supply['id']}/documents",
        files={"file": ("a.pdf", tiny_pdf(), "application/pdf")},
        headers=client,
    )
    jpg = await app_client.post(
        f"/supplies/{supply['id']}/documents",
        files={"file": ("a.jpg", b"\xff\xd8\xff tiny", "image/jpeg")},
        headers=client,
    )
    png = await app_client.post(
        f"/supplies/{supply['id']}/documents",
        files={"file": ("a.png", b"\x89PNG tiny", "image/png")},
        headers=client,
    )
    assert pdf.status_code == 201
    assert jpg.status_code == 201
    assert png.status_code == 201
    downloaded = await app_client.get(f"/documents/{pdf.json()['id']}/download", headers=client)
    assert downloaded.status_code == 200

    txt = await app_client.post(
        f"/supplies/{supply['id']}/documents",
        files={"file": ("a.txt", b"hello", "text/plain")},
        headers=client,
    )
    assert txt.status_code == 400

    huge = await app_client.post(
        f"/supplies/{supply['id']}/documents",
        files={"file": ("big.pdf", b"x" * (20 * 1024 * 1024 + 1), "application/pdf")},
        headers=client,
    )
    assert huge.status_code == 400

    created_doc_id = pdf.json()["id"]
    validator = await auth_header(app_client, "validator@example.com")
    denied = await app_client.get(f"/documents/{created_doc_id}/download", headers=validator)
    assert denied.status_code == 403
