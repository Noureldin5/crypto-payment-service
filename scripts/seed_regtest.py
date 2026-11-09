"""Prepare the local blockchain for the demo.

Creates wallets (miner, merchant, client_1..3), mines coins and gives
each client some test BTC. Safe to run more than once.

Run:  docker compose exec api python -m scripts.seed_regtest
"""
from decimal import Decimal

from app.adapters.wallets.bitcoin_core import BitcoinRpcClient, RpcError
from app.config import Settings

CLIENT_FUNDS = {"1": Decimal("5"), "2": Decimal("0.1"), "3": Decimal("10")}


def ensure_wallet(rpc: BitcoinRpcClient, name: str) -> None:
    if name in rpc.call("listwallets"):
        return
    try:
        # name, disable_private_keys, blank, passphrase, avoid_reuse, descriptors, load_on_startup
        rpc.call("createwallet", [name, False, False, "", False, True, True])
        print(f"created wallet {name}")
    except RpcError:
        rpc.call("loadwallet", [name])  # already exists on disk
        print(f"loaded wallet {name}")


def main() -> None:
    s = Settings()
    rpc = BitcoinRpcClient(s.btc_rpc_url, s.btc_rpc_user, s.btc_rpc_password)

    for name in ["miner", s.merchant_wallet, *(f"client_{c}" for c in CLIENT_FUNDS)]:
        ensure_wallet(rpc, name)

    # Coinbase rewards need 100 blocks before they can be spent.
    miner_addr = rpc.call("getnewaddress", [], wallet="miner")
    height = rpc.call("getblockcount")
    if height < 101:
        rpc.call("generatetoaddress", [101 - height, miner_addr])
        print(f"mined {101 - height} blocks")

    for client, amount in CLIENT_FUNDS.items():
        wallet = f"client_{client}"
        balance = Decimal(str(rpc.call("getbalance", [], wallet=wallet)))
        if balance < amount:
            addr = rpc.call("getnewaddress", [], wallet=wallet)
            rpc.call("sendtoaddress", [addr, str(amount - balance)], wallet="miner")
            print(f"funded {wallet} with {amount - balance} BTC")

    rpc.call("generatetoaddress", [1, miner_addr])  # confirm the funding txs

    print("\nBalances:")
    for name in [s.merchant_wallet, *(f"client_{c}" for c in CLIENT_FUNDS)]:
        print(f"  {name:10} {rpc.call('getbalance', [], wallet=name)} BTC")


if __name__ == "__main__":
    main()
