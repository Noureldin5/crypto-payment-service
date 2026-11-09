"""Application layer: orchestrates one payment, step by step.

Flow (exactly as the assignment describes it):
  1. Ask the WALLET: does this client exist / have a wallet?
  2. Ask the ABC SERVICE for the client's data (and check the client is active).
  3. Ask the WALLET again: is there enough money?
  4. Take the payment (transfer client -> merchant) and return the result.

The service only knows the three interfaces (ports). It doesn't know about
Bitcoin, HTTP or Postgres, so each of those can be swapped out.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from app.domain.exceptions import (
    ClientServiceUnavailable,
    InsufficientFundsError,
    PaymentNotFound,
    WalletError,
)
from app.domain.models import FailureReason, Payment, PaymentStatus
from app.ports.client_data import ClientDataProvider
from app.ports.repository import PaymentRepository
from app.ports.wallet import WalletProvider

log = logging.getLogger(__name__)


class PaymentService:
    def __init__(
        self,
        wallet: WalletProvider,
        client_data: ClientDataProvider,
        repository: PaymentRepository,
        required_confirmations: int = 1,
    ):
        self.wallet = wallet
        self.client_data = client_data
        self.repository = repository
        self.required_confirmations = required_confirmations

    # ---------- public API ----------

    def create_payment(
        self,
        client_id: str,
        amount: Decimal,
        currency: str,
        caller_service: str,
        description: str | None = None,
        idempotency_key: str | None = None,
    ) -> Payment:
        # Idempotency: the same request sent twice must not charge the client twice.
        if idempotency_key:
            existing = self.repository.get_by_idempotency_key(caller_service, idempotency_key)
            if existing:
                return existing

        payment = Payment(
            client_id=client_id,
            amount=amount,
            currency=currency,
            caller_service=caller_service,
            description=description,
            idempotency_key=idempotency_key,
        )
        self.repository.save(payment)
        self._process(payment)
        return payment

    def get_payment(self, payment_id: str) -> Payment:
        payment = self.repository.get(payment_id)
        if payment is None:
            raise PaymentNotFound(payment_id)
        if payment.status == PaymentStatus.PROCESSING:
            self.refresh_confirmations(payment)
        return payment

    def list_payments(self, limit: int = 50) -> list[Payment]:
        return self.repository.list_recent(limit)

    def refresh_confirmations(self, payment: Payment) -> Payment:
        """PROCESSING -> SUCCESS once the blockchain has confirmed the transaction."""
        try:
            info = self.wallet.get_transaction(payment.wallet_id, payment.tx_id)
        except WalletError:
            log.warning("Could not refresh tx %s, will retry later", payment.tx_id)
            return payment
        payment.confirmations = info.confirmations
        if info.confirmations < 0:  # transaction conflicted / dropped
            payment.fail(FailureReason.TRANSACTION_REJECTED)
        elif info.confirmations >= self.required_confirmations:
            payment.transition_to(PaymentStatus.SUCCESS)
        self.repository.save(payment)
        return payment

    # ---------- the 4 steps ----------

    def _process(self, payment: Payment) -> None:
        try:
            # Step 1: does the client have a wallet?
            wallet_id = self.wallet.find_wallet(payment.client_id)
            if wallet_id is None:
                return self._fail(payment, FailureReason.WALLET_NOT_FOUND)
            payment.wallet_id = wallet_id
            self._move(payment, PaymentStatus.WALLET_FOUND)

            # Step 2: get client data from ABC
            client = self.client_data.get_client(payment.client_id)
            if client is None:
                return self._fail(payment, FailureReason.CLIENT_NOT_FOUND)
            if not client.is_active:
                return self._fail(payment, FailureReason.CLIENT_BLOCKED)
            self._move(payment, PaymentStatus.CLIENT_VERIFIED)

            # Step 3: is there enough money?
            balance = self.wallet.get_balance(wallet_id)
            if balance < payment.amount:
                return self._fail(payment, FailureReason.INSUFFICIENT_FUNDS)
            self._move(payment, PaymentStatus.FUNDS_CONFIRMED)

            # Step 4: take the payment
            result = self.wallet.transfer_to_merchant(
                wallet_id, payment.amount, memo=f"payment:{payment.id}"
            )
            payment.tx_id = result.tx_id
            self._move(payment, PaymentStatus.PROCESSING)

            # If 0 confirmations are required we are done immediately.
            if self.required_confirmations == 0:
                self._move(payment, PaymentStatus.SUCCESS)
            else:
                self.refresh_confirmations(payment)

        except InsufficientFundsError:
            self._fail(payment, FailureReason.INSUFFICIENT_FUNDS)
        except ClientServiceUnavailable:
            self._fail(payment, FailureReason.CLIENT_SERVICE_UNAVAILABLE)
        except WalletError:
            log.exception("Wallet error for payment %s", payment.id)
            self._fail(payment, FailureReason.WALLET_ERROR)

    def _move(self, payment: Payment, status: PaymentStatus) -> None:
        payment.transition_to(status)
        self.repository.save(payment)
        log.info("payment %s -> %s", payment.id, status.value)

    def _fail(self, payment: Payment, reason: FailureReason) -> None:
        payment.fail(reason)
        self.repository.save(payment)
        log.info("payment %s FAILED: %s", payment.id, reason.value)
