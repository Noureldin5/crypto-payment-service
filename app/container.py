"""Composition root: the ONLY place that knows which concrete classes are used.

Everything else depends on interfaces. Swapping Bitcoin for another wallet
means changing this file only.
"""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from app.adapters.client_data.abc_http import AbcHttpClientDataProvider
from app.adapters.persistence.sql_repository import SqlPaymentRepository
from app.adapters.wallets.bitcoin_core import BitcoinCoreWallet, BitcoinRpcClient
from app.adapters.wallets.in_memory import InMemoryWallet
from app.config import Settings
from app.ports.wallet import WalletProvider
from app.services.payment_service import PaymentService


@lru_cache
def get_settings() -> Settings:
    return Settings()


def build_wallet(settings: Settings) -> WalletProvider:
    if settings.wallet_backend == "memory":
        return InMemoryWallet({"1": Decimal("5"), "2": Decimal("0.1"), "3": Decimal("10")})
    rpc = BitcoinRpcClient(settings.btc_rpc_url, settings.btc_rpc_user, settings.btc_rpc_password)
    return BitcoinCoreWallet(rpc, merchant_wallet=settings.merchant_wallet)


@lru_cache
def get_payment_service() -> PaymentService:
    s = get_settings()
    return PaymentService(
        wallet=build_wallet(s),
        client_data=AbcHttpClientDataProvider(s.abc_base_url, s.abc_api_key),
        repository=SqlPaymentRepository(s.database_url),
        required_confirmations=s.required_confirmations,
    )
