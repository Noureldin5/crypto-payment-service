from decimal import Decimal

import pytest

from app.domain.exceptions import ClientServiceUnavailable, InvalidStateTransition
from app.domain.models import FailureReason, Payment, PaymentStatus


def pay(service, client_id, amount, key=None):
    return service.create_payment(client_id, Decimal(amount), "BTC", "shop", idempotency_key=key)


def test_successful_payment(service, wallet):
    p = pay(service, "1", "0.5")
    assert p.status == PaymentStatus.SUCCESS
    assert p.tx_id
    assert wallet.balances["1"] == Decimal("4.5")
    assert wallet.merchant_balance == Decimal("0.5")


def test_wallet_not_found(service):
    p = pay(service, "99", "1")
    assert p.status == PaymentStatus.FAILED
    assert p.failure_reason == FailureReason.WALLET_NOT_FOUND


def test_client_not_in_abc(service, wallet):
    wallet.balances["7"] = Decimal("1")  # has wallet, unknown to ABC
    p = pay(service, "7", "0.1")
    assert p.failure_reason == FailureReason.CLIENT_NOT_FOUND


def test_blocked_client(service, wallet):
    p = pay(service, "3", "0.1")
    assert p.failure_reason == FailureReason.CLIENT_BLOCKED
    assert wallet.balances["3"] == Decimal("10")  # money untouched


def test_insufficient_funds(service, wallet):
    p = pay(service, "2", "1")
    assert p.failure_reason == FailureReason.INSUFFICIENT_FUNDS
    assert wallet.balances["2"] == Decimal("0.1")


def test_abc_down(service, clients):
    def boom(_):
        raise ClientServiceUnavailable("down")
    clients.get_client = boom
    p = pay(service, "1", "0.1")
    assert p.failure_reason == FailureReason.CLIENT_SERVICE_UNAVAILABLE


def test_idempotency_charges_once(service, wallet):
    a = pay(service, "1", "1", key="order-1")
    b = pay(service, "1", "1", key="order-1")
    assert a.id == b.id
    assert wallet.balances["1"] == Decimal("4")


def test_processing_until_confirmed(service, wallet, repo):
    original = wallet.transfer_to_merchant

    def unconfirmed(*args, **kwargs):
        r = original(*args, **kwargs)
        wallet.transactions[r.tx_id] = 0
        return r
    wallet.transfer_to_merchant = unconfirmed

    p = pay(service, "1", "0.2")
    assert p.status == PaymentStatus.PROCESSING
    wallet.transactions[p.tx_id] = 1  # a block was mined
    assert service.get_payment(p.id).status == PaymentStatus.SUCCESS


def test_payment_is_persisted(service, repo):
    p = pay(service, "1", "0.3")
    stored = repo.get(p.id)
    assert stored.status == PaymentStatus.SUCCESS
    assert stored.amount == Decimal("0.3")


def test_state_machine_blocks_illegal_jumps():
    p = Payment(client_id="1", amount=Decimal("1"), currency="BTC", caller_service="shop")
    with pytest.raises(InvalidStateTransition):
        p.transition_to(PaymentStatus.SUCCESS)  # cannot skip steps
    p.fail(FailureReason.WALLET_NOT_FOUND)
    with pytest.raises(InvalidStateTransition):
        p.transition_to(PaymentStatus.WALLET_FOUND)  # FAILED is final
