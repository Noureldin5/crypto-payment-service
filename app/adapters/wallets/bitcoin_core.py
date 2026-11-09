"""Adapter: Bitcoin Core (open-source crypto wallet) via its JSON-RPC API.

Each client gets a named wallet inside bitcoind: client "1" -> wallet "client_1".
The merchant (us) has a wallet called "merchant" that receives payments.
Runs on regtest (a private local blockchain) so no real money is involved.
"""
from __future__ import annotations

import itertools
from decimal import Decimal

import httpx

from app.domain.exceptions import InsufficientFundsError, WalletError
from app.ports.wallet import TransactionInfo, TransferResult, WalletProvider

RPC_WALLET_NOT_FOUND = -18
RPC_INSUFFICIENT_FUNDS = -6
RPC_WALLET_ALREADY_LOADED = -35


class BitcoinRpcClient:
    """Small JSON-RPC client. Separate class = Single Responsibility."""

    def __init__(self, url: str, user: str, password: str, timeout: float = 10.0,
                 transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(
            base_url=url, auth=(user, password), timeout=timeout, transport=transport
        )
        self._ids = itertools.count(1)

    def call(self, method: str, params: list | None = None, wallet: str | None = None):
        path = f"/wallet/{wallet}" if wallet else "/"
        body = {"jsonrpc": "1.0", "id": next(self._ids), "method": method, "params": params or []}
        try:
            resp = self._http.post(path, json=body)
        except httpx.HTTPError as exc:
            raise WalletError(f"bitcoind unreachable: {exc}") from exc
        try:
            data = resp.json()
        except ValueError as exc:
            raise WalletError(f"bad response from bitcoind (HTTP {resp.status_code})") from exc
        if data.get("error"):
            raise RpcError(data["error"].get("code"), data["error"].get("message"))
        return data["result"]


class RpcError(WalletError):
    def __init__(self, code: int, message: str):
        super().__init__(f"RPC error {code}: {message}")
        self.code = code


class BitcoinCoreWallet(WalletProvider):
    def __init__(self, rpc: BitcoinRpcClient, merchant_wallet: str = "merchant",
                 wallet_prefix: str = "client_"):
        self.rpc = rpc
        self.merchant_wallet = merchant_wallet
        self.wallet_prefix = wallet_prefix

    def _wallet_name(self, client_id: str) -> str:
        return f"{self.wallet_prefix}{client_id}"

    def find_wallet(self, client_id: str) -> str | None:
        name = self._wallet_name(client_id)
        if name in self.rpc.call("listwallets"):
            return name
        # Wallet may exist on disk but not be loaded (e.g. after a restart).
        try:
            self.rpc.call("loadwallet", [name])
            return name
        except RpcError as exc:
            if exc.code == RPC_WALLET_ALREADY_LOADED:
                return name
            if exc.code == RPC_WALLET_NOT_FOUND:
                return None
            raise

    def get_balance(self, wallet_id: str) -> Decimal:
        result = self.rpc.call("getbalance", [], wallet=wallet_id)
        return Decimal(str(result))

    def transfer_to_merchant(self, wallet_id: str, amount: Decimal, memo: str) -> TransferResult:
        merchant_address = self.rpc.call("getnewaddress", ["payments"], wallet=self.merchant_wallet)
        try:
            # params: address, amount, comment
            tx_id = self.rpc.call("sendtoaddress", [merchant_address, str(amount), memo],
                                  wallet=wallet_id)
        except RpcError as exc:
            if exc.code == RPC_INSUFFICIENT_FUNDS:
                raise InsufficientFundsError(str(exc)) from exc
            raise
        return TransferResult(tx_id=tx_id)

    def get_transaction(self, wallet_id: str, tx_id: str) -> TransactionInfo:
        tx = self.rpc.call("gettransaction", [tx_id], wallet=wallet_id)
        return TransactionInfo(tx_id=tx_id, confirmations=int(tx.get("confirmations", 0)))
