# Architecture & SOLID — defense notes

## Architecture approach: Layered / Hexagonal (Ports & Adapters)

```
api/        HTTP only (FastAPI routes, request/response schemas)
   ↓
services/   PaymentService — the 4-step business flow
   ↓ depends on interfaces only
ports/      WalletProvider, ClientDataProvider, PaymentRepository  (abstract classes)
   ↑ implemented by
adapters/   BitcoinCoreWallet, InMemoryWallet, AbcHttpClientDataProvider, SqlPaymentRepository
domain/     Payment entity + state machine (no framework code at all)
container.py  the only place that chooses concrete classes (composition root)
```

**Why:** the business logic (domain + service) doesn't know about Bitcoin, HTTP or Postgres.
I can change the wallet, the database or the ABC client without touching the business logic,
and I can test the logic with fake adapters (25 tests run in under a second).

**Deployment:** 5 Docker containers on one VPS: `api`, `abc-service`, `db` (Postgres), `bitcoind`, `miner`.
Only `api:8000` is public.

## Where SOLID is

| Principle | Where in the code | What to say |
|---|---|---|
| **S** — Single Responsibility | `routes.py` (HTTP only), `PaymentService` (flow only), `SqlPaymentRepository` (DB only), `BitcoinRpcClient` (JSON-RPC transport) vs `BitcoinCoreWallet` (wallet logic), `Payment` (state rules) | Each class has one reason to change. If the DB changes, only the repository changes. |
| **O** — Open/Closed | `WalletProvider` interface | To add Ethereum I **add** `EthereumWallet(WalletProvider)` and register it in `container.py`. `PaymentService` is **not modified**. |
| **L** — Liskov Substitution | `InMemoryWallet` and `BitcoinCoreWallet` | Both can be used wherever `WalletProvider` is expected. The tests run the real service with the fake wallet, and production runs it with Bitcoin Core, with the same behavior. |
| **I** — Interface Segregation | Three small interfaces instead of one big "ExternalServices" | `ClientDataProvider` has 1 method. A class only implements what it needs. |
| **D** — Dependency Inversion | `PaymentService.__init__(wallet: WalletProvider, client_data: ClientDataProvider, repository: PaymentRepository)` | The high-level service depends on abstractions; the concrete classes are injected from `container.py` (FastAPI `Depends`). |

Other patterns worth naming: **Adapter** (each adapter wraps an external system), **Repository**, **State machine** (`ALLOWED_TRANSITIONS`), **Dependency Injection**, **Idempotency key**.

## Likely questions and answers

**Why Bitcoin Core and regtest?**
Bitcoin Core is the reference open-source Bitcoin wallet with a full JSON-RPC API. Regtest is a private
blockchain: free, instant, no faucet needed, no real money. Switching to testnet only means changing the node flags.

**How do you "take" money from the client's wallet?**
For the demo the service is *custodial*: each client has a wallet inside our Bitcoin Core node (`client_1`, …),
like an exchange. We call `sendtoaddress` from the client's wallet to a fresh address of the `merchant` wallet.
In a non-custodial version the client would pre-approve a spending limit (ERC-20 `approve`/`transferFrom`).

**Why are there two wallet requests?**
That's the order the assignment asks for: first check that the wallet exists, then (after ABC) check the balance.
We also handle the race where the balance changes between the check and the send: Bitcoin then returns
"insufficient funds" (RPC code -6), which we map to `INSUFFICIENT_FUNDS`.

**What if the shop sends the same request twice (network retry)?**
`Idempotency-Key` header + unique DB constraint `(caller_service, idempotency_key)`. The second call returns the first payment, so there's no double charge.

**Why PROCESSING and SUCCESS separately?**
A broadcast transaction isn't final until it's in a block. A `miner` container mines a block every 10 s;
`GET /payments/{id}` checks confirmations and moves the payment to `SUCCESS`. `REQUIRED_CONFIRMATIONS` is configurable.

**Why `Decimal`, not `float`?**
`0.1 + 0.2 != 0.3` in float. Money must be exact. DB column is `NUMERIC(18,8)` (BTC has 8 decimals).

**Why 402 for a failed payment?**
The request itself was valid, so it's not a 4xx validation error. 402 Payment Required says the payment was declined; the reason is in `failure_reason`.

**How does it scale?**
The API is stateless, so you can run N containers behind Nginx/a load balancer. The DB holds the state. Next steps: Celery/RabbitMQ
workers for async processing and a background job to confirm PROCESSING payments (instead of on read).

**How will you add refunds?**
Add `transfer_from_merchant()` to `WalletProvider`, a `REFUNDED` state reachable from `SUCCESS`, and
`POST /payments/{id}/refund`. The existing flow doesn't change (Open/Closed).

**Security?**
API keys per calling service, secrets in `.env`, RPC/DB/ABC not exposed publicly, input validation with Pydantic
(amount > 0, max 8 decimals, currency whitelist).
