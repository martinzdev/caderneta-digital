import unicodedata
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Client, Order, OrderStatus, Payment, Purchase


def normalize(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text)
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower()


class ClientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, client_id: str) -> Client | None:
        return self.db.get(Client, client_id)

    def search(self, term: str | None) -> list[Client]:
        clients = self.db.scalars(
            select(Client).where(Client.active.is_(True)).order_by(Client.name)
        ).all()
        if not term:
            return list(clients)
        needle = normalize(term)
        return [c for c in clients if needle in normalize(c.name)]

    def add(self, client: Client) -> Client:
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def save(self, client: Client) -> Client:
        self.db.commit()
        self.db.refresh(client)
        return client

    def phone_taken(self, phone: str, ignore_id: str | None = None) -> bool:
        query = select(Client.id).where(Client.phone == phone, Client.active.is_(True))
        if ignore_id:
            query = query.where(Client.id != ignore_id)
        return self.db.scalar(query) is not None


class LedgerRepository:
    def __init__(self, db: Session):
        self.db = db

    def total_purchases(self, client_id: str) -> Decimal:
        return self._sum(Purchase, client_id)

    def total_payments(self, client_id: str) -> Decimal:
        return self._sum(Payment, client_id)

    def _sum(self, model, client_id: str) -> Decimal:
        value = self.db.scalar(
            select(func.coalesce(func.sum(model.amount), 0)).where(
                model.client_id == client_id, model.canceled.is_(False)
            )
        )
        return Decimal(value).quantize(Decimal("0.01"))

    def balances(self) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for model, sign in ((Purchase, 1), (Payment, -1)):
            rows = self.db.execute(
                select(model.client_id, func.sum(model.amount))
                .where(model.canceled.is_(False))
                .group_by(model.client_id)
            ).all()
            for client_id, total in rows:
                result[client_id] = result.get(client_id, Decimal("0")) + sign * Decimal(total)
        return {k: v.quantize(Decimal("0.01")) for k, v in result.items()}

    def get_purchase(self, purchase_id: str) -> Purchase | None:
        return self.db.get(Purchase, purchase_id)

    def get_payment(self, payment_id: str) -> Payment | None:
        return self.db.get(Payment, payment_id)

    def add(self, record: Purchase | Payment) -> None:
        self.db.add(record)
        self.db.commit()

    def save(self) -> None:
        self.db.commit()

    def entries_between(
        self, client_id: str, start: datetime, end: datetime
    ) -> tuple[list[Purchase], list[Payment]]:
        purchases = self.db.scalars(
            select(Purchase).where(
                Purchase.client_id == client_id,
                Purchase.created_at >= start,
                Purchase.created_at < end,
            )
        ).all()
        payments = self.db.scalars(
            select(Payment).where(
                Payment.client_id == client_id,
                Payment.created_at >= start,
                Payment.created_at < end,
            )
        ).all()
        return list(purchases), list(payments)

    def month_totals(self, start: datetime, end: datetime) -> tuple[Decimal, Decimal]:
        def total(model) -> Decimal:
            value = self.db.scalar(
                select(func.coalesce(func.sum(model.amount), 0)).where(
                    model.canceled.is_(False),
                    model.created_at >= start,
                    model.created_at < end,
                )
            )
            return Decimal(value).quantize(Decimal("0.01"))

        return total(Purchase), total(Payment)


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, order_id: str) -> Order | None:
        return self.db.get(Order, order_id)

    def list(self, status: OrderStatus | None) -> list[Order]:
        query = select(Order).order_by(Order.created_at.desc())
        if status:
            query = query.where(Order.status == status)
        return list(self.db.scalars(query).all())

    def add(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def save(self, order: Order) -> Order:
        self.db.commit()
        self.db.refresh(order)
        return order
