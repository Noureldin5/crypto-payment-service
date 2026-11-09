"""HTTP layer: only translates HTTP <-> service calls. No business logic here."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.api.schemas import CreatePaymentRequest, PaymentResponse
from app.container import get_payment_service, get_settings
from app.domain.exceptions import PaymentNotFound
from app.domain.models import PaymentStatus
from app.services.payment_service import PaymentService

router = APIRouter()


def authenticate_caller(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Which service is calling us? Returns its name, or 401."""
    caller = get_settings().callers.get(x_api_key)
    if caller is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return caller


@router.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@router.post("/payments", response_model=PaymentResponse, tags=["payments"],
             status_code=status.HTTP_201_CREATED)
def create_payment(
    body: CreatePaymentRequest,
    response: Response,
    caller: str = Depends(authenticate_caller),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    service: PaymentService = Depends(get_payment_service),
):
    payment = service.create_payment(
        client_id=body.client_id, amount=body.amount, currency=body.currency,
        caller_service=caller, description=body.description, idempotency_key=idempotency_key,
    )
    # 201 = paid or in progress, 402 = payment declined (business failure)
    if payment.status == PaymentStatus.FAILED:
        response.status_code = status.HTTP_402_PAYMENT_REQUIRED
    return PaymentResponse.from_domain(payment)


@router.get("/payments/{payment_id}", response_model=PaymentResponse, tags=["payments"])
def get_payment(
    payment_id: str,
    _: str = Depends(authenticate_caller),
    service: PaymentService = Depends(get_payment_service),
):
    try:
        return PaymentResponse.from_domain(service.get_payment(payment_id))
    except PaymentNotFound:
        raise HTTPException(status_code=404, detail="Payment not found")


@router.get("/payments", response_model=list[PaymentResponse], tags=["payments"])
def list_payments(
    limit: int = 50,
    _: str = Depends(authenticate_caller),
    service: PaymentService = Depends(get_payment_service),
):
    return [PaymentResponse.from_domain(p) for p in service.list_payments(min(limit, 200))]
