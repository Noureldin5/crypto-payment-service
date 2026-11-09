"""Adapter: stores payments in PostgreSQL (or SQLite in tests) with SQLAlchemy."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime, Integer, Numeric, String, UniqueConstraint, create_engine, select,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.domain.models import FailureReason, Payment, PaymentStatus
from app.ports.repository import PaymentRepository


class Base(DeclarativeBase):
    pass


class PaymentRow(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("caller_service", "idempotency_key", name="uq_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    currency: Mapped[str] = mapped_column(String(10))
    caller_service: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    wallet_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tx_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmations: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _to_row(p: Payment, row: PaymentRow) -> PaymentRow:
    for f in ("id", "client_id", "amount", "currency", "caller_service", "description",
              "idempotency_key", "wallet_id", "tx_id", "confirmations", "created_at",
              "updated_at"):
        setattr(row, f, getattr(p, f))
    row.status = p.status.value
    row.failure_reason = p.failure_reason.value if p.failure_reason else None
    return row


def _to_domain(r: PaymentRow) -> Payment:
    return Payment(
        id=r.id, client_id=r.client_id, amount=Decimal(r.amount), currency=r.currency,
        caller_service=r.caller_service, description=r.description,
        idempotency_key=r.idempotency_key, status=PaymentStatus(r.status),
        failure_reason=FailureReason(r.failure_reason) if r.failure_reason else None,
        wallet_id=r.wallet_id, tx_id=r.tx_id, confirmations=r.confirmations,
        created_at=r.created_at, updated_at=r.updated_at,
    )


class SqlPaymentRepository(PaymentRepository):
    def __init__(self, database_url: str):
        kwargs = {}
        if database_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            if database_url in ("sqlite://", "sqlite:///:memory:"):
                kwargs["poolclass"] = StaticPool  # one shared in-memory DB (tests)
        self.engine = create_engine(database_url, pool_pre_ping=True, **kwargs)
        self._session = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def save(self, payment: Payment) -> None:
        with self._session.begin() as s:
            row = s.get(PaymentRow, payment.id) or PaymentRow()
            s.add(_to_row(payment, row))

    def get(self, payment_id: str) -> Payment | None:
        with Session(self.engine) as s:
            row = s.get(PaymentRow, payment_id)
            return _to_domain(row) if row else None

    def get_by_idempotency_key(self, caller_service: str, key: str) -> Payment | None:
        with Session(self.engine) as s:
            row = s.scalar(select(PaymentRow).where(
                PaymentRow.caller_service == caller_service, PaymentRow.idempotency_key == key))
            return _to_domain(row) if row else None

    def list_recent(self, limit: int = 50) -> list[Payment]:
        with Session(self.engine) as s:
            rows = s.scalars(select(PaymentRow).order_by(PaymentRow.created_at.desc()).limit(limit))
            return [_to_domain(r) for r in rows]
