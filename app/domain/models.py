"""Domain layer: the Payment entity and its state machine.

This module has NO dependencies on FastAPI, SQLAlchemy or Bitcoin.
It is pure business logic, which makes it easy to test and reuse (SRP).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from app.domain.exceptions import InvalidStateTransition


class PaymentStatus(str, Enum):
    CREATED = "CREATED"                  # request accepted, nothing checked yet
    WALLET_FOUND = "WALLET_FOUND"        # client has a wallet
    CLIENT_VERIFIED = "CLIENT_VERIFIED"  # ABC service confirmed client data
    FUNDS_CONFIRMED = "FUNDS_CONFIRMED"  # wallet balance >= amount
    PROCESSING = "PROCESSING"            # transaction broadcast, waiting for confirmations
    SUCCESS = "SUCCESS"                  # transaction confirmed on the blockchain
    FAILED = "FAILED"                    # any step failed (see failure_reason)


class FailureReason(str, Enum):
    WALLET_NOT_FOUND = "WALLET_NOT_FOUND"
    CLIENT_NOT_FOUND = "CLIENT_NOT_FOUND"
    CLIENT_BLOCKED = "CLIENT_BLOCKED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    WALLET_ERROR = "WALLET_ERROR"
    CLIENT_SERVICE_UNAVAILABLE = "CLIENT_SERVICE_UNAVAILABLE"
    TRANSACTION_REJECTED = "TRANSACTION_REJECTED"


# Allowed transitions = the state diagram, written as code.
ALLOWED_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.CREATED: {PaymentStatus.WALLET_FOUND, PaymentStatus.FAILED},
    PaymentStatus.WALLET_FOUND: {PaymentStatus.CLIENT_VERIFIED, PaymentStatus.FAILED},
    PaymentStatus.CLIENT_VERIFIED: {PaymentStatus.FUNDS_CONFIRMED, PaymentStatus.FAILED},
    PaymentStatus.FUNDS_CONFIRMED: {PaymentStatus.PROCESSING, PaymentStatus.FAILED},
    PaymentStatus.PROCESSING: {PaymentStatus.SUCCESS, PaymentStatus.FAILED},
    PaymentStatus.SUCCESS: set(),   # final
    PaymentStatus.FAILED: set(),    # final
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Payment:
    client_id: str
    amount: Decimal
    currency: str
    caller_service: str
    description: str | None = None
    idempotency_key: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: PaymentStatus = PaymentStatus.CREATED
    failure_reason: FailureReason | None = None
    wallet_id: str | None = None
    tx_id: str | None = None
    confirmations: int = 0
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @property
    def is_final(self) -> bool:
        return self.status in (PaymentStatus.SUCCESS, PaymentStatus.FAILED)

    def transition_to(self, new_status: PaymentStatus) -> None:
        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidStateTransition(self.status, new_status)
        self.status = new_status
        self.updated_at = _now()

    def fail(self, reason: FailureReason) -> None:
        self.transition_to(PaymentStatus.FAILED)
        self.failure_reason = reason
