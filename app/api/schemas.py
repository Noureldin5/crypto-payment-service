"""Request/response models (what the API accepts and returns)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.models import Payment


class CreatePaymentRequest(BaseModel):
    client_id: str = Field(..., examples=["1"])
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=8, examples=["0.5"])
    currency: str = Field("BTC", pattern="^BTC$")
    description: str | None = Field(None, max_length=255, examples=["Order #1042"])


class PaymentResponse(BaseModel):
    id: str
    client_id: str
    amount: Decimal
    currency: str
    status: str
    failure_reason: str | None
    tx_id: str | None
    confirmations: int
    caller_service: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, p: Payment) -> "PaymentResponse":
        return cls(
            id=p.id, client_id=p.client_id, amount=p.amount, currency=p.currency,
            status=p.status.value,
            failure_reason=p.failure_reason.value if p.failure_reason else None,
            tx_id=p.tx_id, confirmations=p.confirmations, caller_service=p.caller_service,
            description=p.description, created_at=p.created_at, updated_at=p.updated_at,
        )
