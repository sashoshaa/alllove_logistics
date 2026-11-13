from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import httpx


class ApiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"Ошибка {response.status_code}"
    detail = payload.get("detail", payload)
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                parts.append(str(item.get("msg", item)))
            else:
                parts.append(str(item))
        return "; ".join(parts) or f"Ошибка {response.status_code}"
    return str(detail)


class ApiClient:
    def __init__(self, base_url: str, client: Optional[httpx.Client] = None):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.role: Optional[str] = None
        self.full_name: Optional[str] = None
        self._client = client or httpx.Client(timeout=20.0)

    def _headers(self, extra: Optional[dict[str, str]] = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(
            method,
            f"{self.base_url}{path}",
            headers=self._headers(kwargs.pop("headers", None)),
            **kwargs,
        )
        if not response.is_success:
            raise ApiError(error_message(response), response.status_code)
        if response.status_code == 204 or not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.content

    def login(self, email: str, password: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/auth/login",
            data={"username": email.strip(), "password": password},
        )
        role = data.get("role")
        if role != "validator":
            raise ApiError(
                "Это приложение только для валидатора. "
                "Сотрудник шоурума и администратор работают в веб-интерфейсе."
            )
        self.token = data["access_token"]
        self.role = role
        self.full_name = data.get("full_name")
        return data

    def logout(self) -> None:
        self.token = None
        self.role = None
        self.full_name = None

    def queue(self) -> list[dict[str, Any]]:
        return self._request("GET", "/supplies")

    def supply(self, supply_id: int) -> dict[str, Any]:
        return self._request("GET", f"/supplies/{supply_id}")

    def check(
        self,
        supply_id: int,
        items: list[dict[str, Any]],
        comment: str = "",
        return_for_clarification: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "items": items,
            "return_for_clarification": return_for_clarification,
        }
        if comment.strip():
            payload["comment"] = comment.strip()
        return self._request("POST", f"/supplies/{supply_id}/check", json=payload)

    def notifications(self) -> list[dict[str, Any]]:
        return self._request("GET", "/notifications")

    def mark_read(self, notification_id: int) -> dict[str, Any]:
        return self._request("PATCH", f"/notifications/{notification_id}/read")

    def download_document(self, document_id: int, destination: Path) -> Path:
        content = self._request("GET", f"/documents/{document_id}/download")
        destination.write_bytes(content if isinstance(content, bytes) else bytes(content))
        return destination
