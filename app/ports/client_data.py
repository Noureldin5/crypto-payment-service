"""Port (interface) for the external client-data service ("ABC")."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ClientData:
    client_id: str
    full_name: str
    email: str
    status: str  # "ACTIVE" or "BLOCKED"

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"


class ClientDataProvider(ABC):
    @abstractmethod
    def get_client(self, client_id: str) -> ClientData | None:
        """Return client data, or None if ABC does not know this client."""
