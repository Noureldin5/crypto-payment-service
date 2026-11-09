"""Port (interface) for any crypto wallet.

The PaymentService depends on THIS abstraction, never on Bitcoin Core directly.
That is the Dependency Inversion Principle (the "D" in SOLID).
To support Ethereum, write a new class that implements WalletProvider;
the service code does not change (Open/Closed Principle).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TransferResult:
    tx_id: str


@dataclass(frozen=True)
class TransactionInfo:
    tx_id: str
    confirmations: int


class WalletProvider(ABC):
    @abstractmethod
    def find_wallet(self, client_id: str) -> str | None:
        """Return the wallet id for this client, or None if the client has no wallet."""

    @abstractmethod
    def get_balance(self, wallet_id: str) -> Decimal:
        """Spendable balance of the wallet."""

    @abstractmethod
    def transfer_to_merchant(self, wallet_id: str, amount: Decimal, memo: str) -> TransferResult:
        """Move `amount` from the client's wallet to the merchant wallet."""

    @abstractmethod
    def get_transaction(self, wallet_id: str, tx_id: str) -> TransactionInfo:
        """Current state of a transaction (how many confirmations)."""
