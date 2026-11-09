"""Tests the Bitcoin Core adapter against a fake JSON-RPC server."""
import json
from decimal import Decimal

import httpx
import pytest

from app.adapters.wallets.bitcoin_core import BitcoinCoreWallet, BitcoinRpcClient
from app.domain.exceptions import InsufficientFundsError, WalletError


class FakeBitcoind:
    def __init__(self):
        self.loaded = ["merchant", "client_1"]
        self.on_disk = ["client_2"]
        self.balances = {"client_1": 5.0, "client_2": 0.1}
        self.calls = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method, params = body["method"], body["params"]
        wallet = request.url.path.removeprefix("/wallet/") if request.url.path.startswith("/wallet/") else None
        self.calls.append((wallet, method, params))

        def ok(result):
            return httpx.Response(200, json={"result": result, "error": None, "id": body["id"]})

        def err(code, msg):
            return httpx.Response(500, json={"result": None, "error": {"code": code, "message": msg}, "id": body["id"]})

        if method == "listwallets":
            return ok(self.loaded)
        if method == "loadwallet":
            if params[0] in self.on_disk:
                self.loaded.append(params[0])
                return ok({"name": params[0]})
            return err(-18, "Wallet file not found")
        if method == "getbalance":
            return ok(self.balances[wallet])
        if method == "getnewaddress":
            return ok("bcrt1qmerchant")
        if method == "sendtoaddress":
            if float(params[1]) > self.balances[wallet]:
                return err(-6, "Insufficient funds")
            return ok("ab" * 32)
        if method == "gettransaction":
            return ok({"confirmations": 2})
        return err(-32601, "Method not found")


@pytest.fixture
def fake():
    return FakeBitcoind()


@pytest.fixture
def btc(fake):
    rpc = BitcoinRpcClient("http://bitcoind:18443", "u", "p", transport=httpx.MockTransport(fake.handler))
    return BitcoinCoreWallet(rpc)


def test_find_loaded_wallet(btc):
    assert btc.find_wallet("1") == "client_1"


def test_find_wallet_on_disk_loads_it(btc, fake):
    assert btc.find_wallet("2") == "client_2"
    assert ("client_2" in fake.loaded)


def test_missing_wallet(btc):
    assert btc.find_wallet("99") is None


def test_balance(btc):
    assert btc.get_balance("client_1") == Decimal("5.0")


def test_transfer_goes_to_merchant(btc, fake):
    r = btc.transfer_to_merchant("client_1", Decimal("0.5"), "payment:x")
    assert r.tx_id == "ab" * 32
    assert (None, "getnewaddress", ["payments"]) not in fake.calls
    assert ("merchant", "getnewaddress", ["payments"]) in fake.calls
    assert ("client_1", "sendtoaddress", ["bcrt1qmerchant", "0.5", "payment:x"]) in fake.calls


def test_transfer_insufficient(btc):
    with pytest.raises(InsufficientFundsError):
        btc.transfer_to_merchant("client_2", Decimal("1"), "m")


def test_confirmations(btc):
    assert btc.get_transaction("client_1", "t").confirmations == 2


def test_unreachable_node():
    def down(request):
        raise httpx.ConnectError("refused")
    rpc = BitcoinRpcClient("http://bitcoind:18443", "u", "p", transport=httpx.MockTransport(down))
    with pytest.raises(WalletError):
        BitcoinCoreWallet(rpc).find_wallet("1")
