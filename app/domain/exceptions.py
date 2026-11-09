"""Domain and integration exceptions."""


class InvalidStateTransition(Exception):
    def __init__(self, current, new):
        super().__init__(f"Cannot move payment from {current} to {new}")
        self.current = current
        self.new = new


class WalletError(Exception):
    """Generic problem talking to the wallet (network down, RPC error...)."""


class InsufficientFundsError(WalletError):
    """Wallet rejected the transfer because the balance is too low."""


class ClientServiceUnavailable(Exception):
    """The ABC client-data service could not be reached."""


class PaymentNotFound(Exception):
    pass
