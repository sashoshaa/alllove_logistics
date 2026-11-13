from datetime import date, timedelta

from tests.conftest import auth_header, create_supply


async def test_6_3_history_and_audit(app_client):
    admin = await auth_header(app_client, "admin@example.com")
    client = await auth_header(app_client, "client1@example.com")
    supply = await create_supply(app_client, client)
    new_date = (date.today() + timedelta(days=4)).isoformat()
    updated = await app_client.patch(
        f"/supplies/{supply['id']}",
        json={"planned_date": new_date},
        headers=client,
    )
    assert updated.status_code == 200
    history = await app_client.get(f"/supplies/{supply['id']}/history", headers=admin)
    assert history.status_code == 200
    rows = history.json()
    assert any(row["field"] == "planned_date" for row in rows)
    planned = next(row for row in rows if row["field"] == "planned_date")
    assert planned["new_value"] == new_date
    assert planned["actor_id"] == 2
    assert planned["source"] == "manual"

    mutate = await app_client.post(f"/admin/audit/{rows[0]['id']}", headers=admin)
    assert mutate.status_code == 405
    delete = await app_client.delete("/admin/audit/1", headers=admin)
    assert delete.status_code == 405
    journal = await app_client.get("/admin/audit", headers=admin)
    assert journal.status_code == 200
    assert len(journal.json()) >= 1


async def test_6_7_proposals(app_client):
    cl1 = await auth_header(app_client, "client1@example.com")
    cl2 = await auth_header(app_client, "client2@example.com")
    supply = await create_supply(app_client, cl1)
    new_date = (date.today() + timedelta(days=9)).isoformat()
    proposal = await app_client.post(
        f"/supplies/{supply['id']}/proposals",
        json={"planned_date": new_date, "comment": "перенос срока"},
        headers=cl2,
    )
    assert proposal.status_code == 201
    notes = await app_client.get("/notifications", headers=cl1)
    assert any(row["type"] == "proposal_created" for row in notes.json())

    accepted = await app_client.post(f"/proposals/{proposal.json()['id']}/accept", headers=cl1)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    card = await app_client.get(f"/supplies/{supply['id']}", headers=cl1)
    assert card.json()["planned_date"] == new_date

    again = await app_client.post(f"/proposals/{proposal.json()['id']}/accept", headers=cl1)
    assert again.status_code == 400

    second = await app_client.post(
        f"/supplies/{supply['id']}/proposals",
        json={"planned_date": (date.today() + timedelta(days=20)).isoformat()},
        headers=cl2,
    )
    rejected = await app_client.post(f"/proposals/{second.json()['id']}/reject", headers=cl1)
    assert rejected.status_code == 200
    after_reject = await app_client.get(f"/supplies/{supply['id']}", headers=cl1)
    assert after_reject.json()["planned_date"] == new_date

    third = await app_client.post(
        f"/supplies/{supply['id']}/proposals",
        json={"planned_date": (date.today() + timedelta(days=21)).isoformat()},
        headers=cl2,
    )
    steal = await app_client.post(f"/proposals/{third.json()['id']}/accept", headers=cl2)
    assert steal.status_code == 403


async def test_6_8_reports(app_client):
    client = await auth_header(app_client, "client1@example.com")
    validator = await auth_header(app_client, "validator@example.com")
    supply = await create_supply(app_client, client)
    await app_client.post(f"/supplies/{supply['id']}/status", json={"status": "in_transit"}, headers=client)
    await app_client.post(f"/supplies/{supply['id']}/status", json={"status": "on_check"}, headers=client)
    current = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    items = sorted(current.json()["items"], key=lambda row: row["catalog_item_id"])
    await app_client.post(
        f"/supplies/{supply['id']}/check",
        json={
            "items": [
                {"item_id": items[0]["id"], "actual_qty": 8},
                {"item_id": items[1]["id"], "actual_qty": 5},
            ]
        },
        headers=validator,
    )
    registry = await app_client.get("/reports/registry", headers=client)
    assert registry.status_code == 200
    assert any(row["number"] == supply["number"] for row in registry.json())
    csv_body = await app_client.get("/reports/registry.csv", headers=client)
    assert csv_body.status_code == 200
    assert supply["number"] in csv_body.text

    diffs = await app_client.get("/reports/discrepancies", headers=client)
    assert diffs.status_code == 200
    assert any(row["number"] == supply["number"] for row in diffs.json())
    empty = await app_client.get(
        "/reports/discrepancies",
        params={"date_from": "1990-01-01", "date_to": "1990-01-02"},
        headers=client,
    )
    assert empty.json() == []


async def test_6_9_overdue(app_client):
    client = await auth_header(app_client, "client1@example.com")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    supply = await create_supply(app_client, client, planned_date=yesterday)
    await app_client.post(f"/supplies/{supply['id']}/status", json={"status": "in_transit"}, headers=client)
    listed = await app_client.get("/supplies", headers=client)
    row = next(item for item in listed.json() if item["id"] == supply["id"])
    assert row["is_overdue"] is True
    assert row["overdue_days"] == 1
    assert row["status"] == "in_transit"
    summary = await app_client.get("/supplies/summary", headers=client)
    assert summary.json()["overdue"] >= 1
    notes = await app_client.get("/notifications", headers=client)
    overdue_notes = [row for row in notes.json() if row["type"] == "overdue"]
    assert overdue_notes
    await app_client.get("/supplies", headers=client)
    notes_again = await app_client.get("/notifications", headers=client)
    assert len([row for row in notes_again.json() if row["type"] == "overdue" and row["supply_id"] == supply["id"]]) == 1

    today_supply = await create_supply(app_client, client, planned_date=date.today().isoformat())
    today_card = await app_client.get(f"/supplies/{today_supply['id']}", headers=client)
    assert today_card.json()["is_overdue"] is False

    await app_client.post(f"/supplies/{supply['id']}/status", json={"status": "cancelled"}, headers=client)
    cancelled = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    assert cancelled.json()["is_overdue"] is False


async def test_6_10_notifications_read(app_client):
    client = await auth_header(app_client, "client1@example.com")
    supply = await create_supply(app_client, client)
    await app_client.post(f"/supplies/{supply['id']}/status", json={"status": "in_transit"}, headers=client)
    notes = await app_client.get("/notifications", headers=client)
    assert notes.status_code == 200
    target = next(row for row in notes.json() if row["supply_id"] == supply["id"])
    marked = await app_client.patch(f"/notifications/{target['id']}/read", headers=client)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    again = await app_client.get("/notifications", headers=client)
    saved = next(row for row in again.json() if row["id"] == target["id"])
    assert saved["is_read"] is True


async def test_6_12_comments(app_client):
    client = await auth_header(app_client, "client1@example.com")
    validator = await auth_header(app_client, "validator@example.com")
    supply = await create_supply(app_client, client)
    first = await app_client.post(
        f"/supplies/{supply['id']}/comments",
        json={"text": "уточнение по сроку"},
        headers=client,
    )
    assert first.status_code == 201
    empty = await app_client.post(
        f"/supplies/{supply['id']}/comments",
        json={"text": "   "},
        headers=client,
    )
    assert empty.status_code == 400
    denied = await app_client.post(
        f"/supplies/{supply['id']}/comments",
        json={"text": "валидатор рано"},
        headers=validator,
    )
    assert denied.status_code == 403
    await app_client.post(f"/supplies/{supply['id']}/status", json={"status": "in_transit"}, headers=client)
    second = await app_client.post(
        f"/supplies/{supply['id']}/comments",
        json={"text": "комментарий валидатора"},
        headers=validator,
    )
    assert second.status_code == 201
    comments = await app_client.get(f"/supplies/{supply['id']}/comments", headers=client)
    assert len(comments.json()) == 2
    card = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    assert card.json()["status"] == "in_transit"


async def test_6_15_backup(app_client):
    admin = await auth_header(app_client, "admin@example.com")
    client = await auth_header(app_client, "client1@example.com")
    supply = await create_supply(app_client, client)
    created = await app_client.post("/admin/backups", headers=admin)
    assert created.status_code == 200
    listed = await app_client.get("/admin/backups", headers=admin)
    assert listed.status_code == 200
    assert listed.json()
    assert created.json()["tables"]["users"] >= 5
    assert created.json()["tables"]["supplies"] >= 1
    restored = await app_client.post(f"/admin/backups/{created.json()['name']}/restore", headers=admin)
    assert restored.status_code == 200
    admin = await auth_header(app_client, "admin@example.com")
    after = await app_client.get(f"/supplies/{supply['id']}", headers=admin)
    assert after.status_code == 200
    assert after.json()["number"] == supply["number"]


async def test_6_16_list_performance_and_conflict(app_client):
    client = await auth_header(app_client, "client1@example.com")
    cl2 = await auth_header(app_client, "client2@example.com")
    supply = await create_supply(app_client, client)
    listed = await app_client.get("/supplies", headers=client)
    assert listed.status_code == 200
    card = await app_client.get(f"/supplies/{supply['id']}", headers=client)
    assert card.status_code == 200
    proposal = await app_client.post(
        f"/supplies/{supply['id']}/proposals",
        json={"planned_date": (date.today() + timedelta(days=8)).isoformat()},
        headers=cl2,
    )
    await app_client.patch(
        f"/supplies/{supply['id']}",
        json={"planned_date": (date.today() + timedelta(days=3)).isoformat()},
        headers=client,
    )
    conflict = await app_client.post(f"/proposals/{proposal.json()['id']}/accept", headers=client)
    assert conflict.status_code == 409
