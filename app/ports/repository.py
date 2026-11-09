"""Port (interface) for storing payments."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import Payment


class PaymentRepository(ABC):
    @abstractmethod
    def save(self, payment: Payment) -> None: ...

    @abstractmethod
    def get(self, payment_id: str) -> Payment | None: ...

    @abstractmethod
    def get_by_idempotency_key(self, caller_service: str, key: str) -> Payment | None: ...

    @abstractmethod
    def list_recent(self, limit: int = 50) -> list[Payment]: ...
