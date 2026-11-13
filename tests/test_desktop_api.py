import json
from pathlib import Path

import httpx

from desktop.api import ApiClient, ApiError, error_message


def _client(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    return ApiClient("http://test", client=httpx.Client(transport=transport))


def test_login_accepts_validator_and_stores_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/login"
        body = request.content.decode()
        assert "validator%40alllove.ru" in body or "validator@alllove.ru" in body
        return httpx.Response(
            200,
            json={
                "access_token": "tok",
                "token_type": "bearer",
                "role": "validator",
                "full_name": "Валидатор",
            },
        )

    api = _client(handler)
    data = api.login("validator@alllove.ru", "validator123")
    assert data["role"] == "validator"
    assert api.token == "tok"
    assert api.full_name == "Валидатор"


def test_login_rejects_showroom_role():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "tok",
                "token_type": "bearer",
                "role": "client",
                "full_name": "Клиент",
            },
        )

    api = _client(handler)
    try:
        api.login("client1@alllove.ru", "client123")
        assert False, "expected ApiError"
    except ApiError as exc:
        assert "валидатора" in str(exc).lower()
        assert api.token is None


def test_check_payload_and_document_download(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/check"):
            body = json.loads(request.content.decode())
            assert body["items"] == [{"item_id": 1, "actual_qty": 4}]
            assert body["return_for_clarification"] is False
            assert body["comment"] == "ок"
            return httpx.Response(200, json={"status": "checked"})
        if request.url.path.endswith("/download"):
            return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})
        return httpx.Response(404, json={"detail": "нет"})

    api = _client(handler)
    api.token = "tok"
    result = api.check(9, [{"item_id": 1, "actual_qty": 4}], comment="ок")
    assert result["status"] == "checked"
    dest = tmp_path / "doc.pdf"
    api.download_document(3, dest)
    assert dest.read_bytes() == b"%PDF"


def test_error_message_from_detail_list():
    response = httpx.Response(422, json={"detail": [{"msg": "Нужно заполнить факт"}]})
    assert "Нужно заполнить факт" in error_message(response)
