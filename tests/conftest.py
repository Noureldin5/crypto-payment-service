import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.client_data.abc_http import InMemoryClientDataProvider  # noqa: E402
from app.adapters.persistence.sql_repository import SqlPaymentRepository  # noqa: E402
from app.adapters.wallets.in_memory import InMemoryWallet  # noqa: E402
from app.ports.client_data import ClientData  # noqa: E402
from app.services.payment_service import PaymentService  # noqa: E402


@pytest.fixture
def wallet():
    return InMemoryWallet({"1": Decimal("5"), "2": Decimal("0.1"), "3": Decimal("10")})


@pytest.fixture
def clients():
    return InMemoryClientDataProvider({
        "1": ClientData("1", "Aibek", "a@x.com", "ACTIVE"),
        "2": ClientData("2", "Aliya", "b@x.com", "ACTIVE"),
        "3": ClientData("3", "Blocked", "c@x.com", "BLOCKED"),
    })


@pytest.fixture
def repo():
    return SqlPaymentRepository("sqlite://")


@pytest.fixture
def service(wallet, clients, repo):
    return PaymentService(wallet, clients, repo, required_confirmations=1)
