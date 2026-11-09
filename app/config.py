"""All settings come from environment variables (.env file)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./payments.db"

    # Which wallet implementation to use: "bitcoin" (real, Bitcoin Core) or "memory" (fake)
    wallet_backend: str = "bitcoin"
    btc_rpc_url: str = "http://bitcoind:18443"
    btc_rpc_user: str = "payuser"
    btc_rpc_password: str = "paypass"
    merchant_wallet: str = "merchant"
    required_confirmations: int = 1

    abc_base_url: str = "http://abc-service:8001"
    abc_api_key: str = "abc-secret"

    # API keys of services allowed to call us, "name:key,name:key"
    caller_api_keys: str = "shop-service:shop-secret"

    @property
    def callers(self) -> dict[str, str]:
        """key -> caller name"""
        pairs = (p.split(":", 1) for p in self.caller_api_keys.split(",") if ":" in p)
        return {key.strip(): name.strip() for name, key in pairs}
