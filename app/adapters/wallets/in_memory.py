"""Adapter: fake wallet kept in memory.

Used by the tests and for a quick demo without bitcoind (WALLET_BACKEND=memory).
It implements the same WalletProvider interface as BitcoinCoreWallet, so it can
replace it anywhere (Liskov Substitution Principle).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from app.domain.exceptions import InsufficientFundsError
from app.ports.wallet import TransactionInfo, TransferResult, WalletProvider


class InMemoryWallet(WalletProvider):
    def __init__(self, balances: dict[str, Decimal] | None = None):
        # client_id -> balance
        self.balances: dict[str, Decimal] = dict(balances or {})
        self.merchant_balance = Decimal("0")
        self.transactions: dict[str, int] = {}

    def find_wallet(self, client_id: str) -> str | None:
        return f"client_{client_id}" if client_id in self.balances else None

    def _client(self, wallet_id: str) -> str:
        return wallet_id.removeprefix("client_")

    def get_balance(self, wallet_id: str) -> Decimal:
        return self.balances[self._client(wallet_id)]

    def transfer_to_merchant(self, wallet_id: str, amount: Decimal, memo: str) -> TransferResult:
        client = self._client(wallet_id)
        if self.balances[client] < amount:
            raise InsufficientFundsError("not enough funds")
        self.balances[client] -= amount
        self.merchant_balance += amount
        tx_id = uuid.uuid4().hex
        self.transactions[tx_id] = 1  # instantly "confirmed"
        return TransferResult(tx_id=tx_id)

    def get_transaction(self, wallet_id: str, tx_id: str) -> TransactionInfo:
        return TransactionInfo(tx_id=tx_id, confirmations=self.transactions.get(tx_id, 0))
