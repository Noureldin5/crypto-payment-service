# Requirements Specification — Crypto Payment Service

**Version:** 1.0 (midterm) · **Author:** Noureldin, COMSE-23

## 1. Purpose
The service lets any internal service (e.g. an online shop) **take a payment from a client's crypto wallet**.
It checks that the client has a wallet, gets the client's data from the ABC service, checks that there is enough money,
withdraws the money to the merchant wallet and returns the result.

## 2. Scope
| In scope (midterm) | Out of scope (planned for final) |
|---|---|
| Withdraw (pay) from a client wallet | Refunds (merchant → client) |
| One currency: BTC (test network) | Other coins (ETH, USDT) |
| REST API for other services | Web UI / admin panel |
| Payment status tracking | Webhooks/notifications to callers |

## 3. Actors and external systems
| Actor / system | Role |
|---|---|
| **Calling service** (Shop) | Sends payment requests, reads results. Authenticated by API key. |
| **ABC service** | Owns client personal data (name, email, status ACTIVE/BLOCKED). |
| **Bitcoin Core** | Open-source crypto wallet. Holds one wallet per client + the merchant wallet. Runs on *regtest* (private test chain, no real money). |
| **PostgreSQL** | Stores payments and their status. |

## 4. Functional requirements
| ID | Requirement |
|---|---|
| FR-1 | The system shall accept a payment request `POST /payments` with `client_id`, `amount`, `currency`, optional `description`. |
| FR-2 | The system shall authenticate the calling service with the `X-API-Key` header and reject unknown keys (401). |
| FR-3 | The system shall check in the wallet that the client has a wallet. If not → `FAILED / WALLET_NOT_FOUND`. |
| FR-4 | The system shall request the client's data from the ABC service. Unknown client → `CLIENT_NOT_FOUND`; blocked client → `CLIENT_BLOCKED`; ABC unreachable → `CLIENT_SERVICE_UNAVAILABLE`. |
| FR-5 | The system shall make a second wallet request to read the balance. Balance < amount → `INSUFFICIENT_FUNDS`. |
| FR-6 | The system shall transfer the amount from the client wallet to the merchant wallet and store the transaction id. |
| FR-7 | The system shall return the result: `201` with status `SUCCESS`/`PROCESSING`, or `402` with status `FAILED` and a `failure_reason`. |
| FR-8 | The system shall mark a payment `SUCCESS` once its transaction has the required number of confirmations (default 1). |
| FR-9 | The system shall let callers read a payment with `GET /payments/{id}` and list payments with `GET /payments`. |
| FR-10 | The system shall support the `Idempotency-Key` header: the same key from the same caller never charges twice and returns the original payment. |
| FR-11 | The system shall record every status change and only allow transitions defined in the state diagram. |

## 5. Non-functional requirements
| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Security | Only the API port (8000) is public. Wallet RPC, ABC and DB are on a private Docker network. Secrets come from `.env`, never from code. |
| NFR-2 | Reliability | Money amounts use `Decimal` (8 decimal places), never `float`. A failed step never leaves money half-moved. |
| NFR-3 | Extensibility | New wallets (e.g. Ethereum) or a new client-data source must be addable **without changing** `PaymentService` (via interfaces). |
| NFR-4 | Scalability | The API is stateless; all state is in PostgreSQL / the wallet, so more API containers can be added behind a load balancer. |
| NFR-5 | Deployability | Whole system starts with one command: `docker compose up -d`, on any VPS (DigitalOcean). |
| NFR-6 | Testability | Business logic is covered by automated tests that run without Bitcoin or a database server. |
| NFR-7 | Performance | A payment request completes in < 2 s under normal conditions. |

## 6. Main use case — "Take payment"
1. Shop sends `POST /payments {client_id: "1", amount: "0.5"}`.
2. Service checks the wallet → client 1 has wallet `client_1`.
3. Service calls ABC → client is ACTIVE.
4. Service checks the wallet balance → 5 BTC ≥ 0.5.
5. Service sends 0.5 BTC to the merchant wallet → gets `tx_id`.
6. Service returns `PROCESSING` (or `SUCCESS` if already confirmed). After the next block it becomes `SUCCESS`.

**Alternative flows:** see failure reasons in FR-3…FR-5 (all end in `FAILED`).

## 7. API summary
| Method | Path | Description |
|---|---|---|
| POST | `/payments` | Create and process a payment |
| GET | `/payments/{id}` | Get payment (refreshes confirmations) |
| GET | `/payments` | List recent payments |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

## 8. Future work (final)
- **Refunds:** new `transfer_from_merchant()` on `WalletProvider`, new state `REFUNDED` after `SUCCESS`, endpoint `POST /payments/{id}/refund`.
- **More wallets:** `EthereumWallet` implementing `WalletProvider`.
- **Interfaces:** web dashboard, webhooks to callers, message queue (Celery/RabbitMQ) for async processing.
- **Real-world model:** non-custodial "pull payments" (ERC-20 `approve` + `transferFrom`) instead of the service holding client wallets.
