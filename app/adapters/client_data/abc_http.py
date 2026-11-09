"""Adapter: calls the external ABC client-data service over HTTP."""
from __future__ import annotations

import httpx

from app.domain.exceptions import ClientServiceUnavailable
from app.ports.client_data import ClientData, ClientDataProvider


class AbcHttpClientDataProvider(ClientDataProvider):
    def __init__(self, base_url: str, api_key: str, timeout: float = 5.0,
                 transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(
            base_url=base_url, headers={"X-API-Key": api_key}, timeout=timeout,
            transport=transport,
        )

    def get_client(self, client_id: str) -> ClientData | None:
        try:
            resp = self._http.get(f"/clients/{client_id}")
        except httpx.HTTPError as exc:
            raise ClientServiceUnavailable(str(exc)) from exc
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise ClientServiceUnavailable(f"ABC returned HTTP {resp.status_code}")
        d = resp.json()
        return ClientData(
            client_id=str(d["id"]), full_name=d["full_name"], email=d["email"], status=d["status"]
        )


class InMemoryClientDataProvider(ClientDataProvider):
    """Fake ABC for tests."""

    def __init__(self, clients: dict[str, ClientData] | None = None):
        self.clients = dict(clients or {})

    def get_client(self, client_id: str) -> ClientData | None:
        return self.clients.get(client_id)
