from tests.conftest import auth_header


async def test_6_1_1_login_and_me(app_client):
    for email, role in [
        ("admin@example.com", "admin"),
        ("client1@example.com", "client"),
        ("validator@example.com", "validator"),
    ]:
        response = await app_client.post("/auth/login", data={"username": email, "password": "test123"})
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["role"] == role
        assert "hashed_password" not in body
        headers = {"Authorization": f"Bearer {body['access_token']}"}
        me = await app_client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == email
        assert "hashed_password" not in me.json()


async def test_6_1_2_blocked_and_forbidden(app_client):
    blocked = await app_client.post(
        "/auth/login", data={"username": "blocked@example.com", "password": "test123"}
    )
    assert blocked.status_code == 403

    no_token = await app_client.get("/users")
    assert no_token.status_code == 401

    bad_token = await app_client.get("/users", headers={"Authorization": "Bearer invalid"})
    assert bad_token.status_code == 401

    client_headers = await auth_header(app_client, "client1@example.com")
    forbidden = await app_client.post(
        "/users",
        json={
            "email": "x@example.com",
            "full_name": "Новый",
            "password": "secret1",
            "role": "client",
        },
        headers=client_headers,
    )
    assert forbidden.status_code == 403


async def test_6_17_2_jwt_and_validation_errors(app_client):
    client_headers = await auth_header(app_client, "client1@example.com")
    invalid = await app_client.post(
        "/supplies",
        json={
            "supplier_id": "bad",
            "location_id": 1,
            "planned_date": "2026-12-01",
            "responsible_id": 2,
            "items": [{"catalog_item_id": 1, "quantity": 1}],
        },
        headers=client_headers,
    )
    assert invalid.status_code == 422

    missing = await app_client.get("/auth/me")
    assert missing.status_code == 401
