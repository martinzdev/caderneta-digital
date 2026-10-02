from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Client,
    Order,
    OrderPayment,
    OrderStatus,
    Payment,
    Purchase,
    User,
)
from app.repositories import ClientRepository, LedgerRepository, OrderRepository
from app.schemas import (
    ClientOut,
    DebtorOut,
    EntryOut,
    OrderIn,
    OrderOut,
    OrderStatusIn,
    PaymentIn,
    PurchaseIn,
    RecordResult,
    StatementOut,
    SummaryOut,
)

LOCAL_TZ = ZoneInfo("America/Porto_Velho")
ZERO = Decimal("0.00")

ORDER_FLOW = {
    OrderStatus.new: {OrderStatus.packed, OrderStatus.canceled},
    OrderStatus.packed: {OrderStatus.delivered, OrderStatus.canceled},
    OrderStatus.delivered: set(),
    OrderStatus.canceled: set(),
}

METHOD_LABELS = {"cash": "dinheiro", "pix": "Pix", "card": "cartão"}


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TZ)
    return value.astimezone(timezone.utc)


def month_range(month: str | None) -> tuple[str, datetime, datetime]:
    if month is None:
        now = datetime.now(LOCAL_TZ)
        month = f"{now.year:04d}-{now.month:02d}"
    try:
        year, mon = (int(part) for part in month.split("-"))
        start = datetime(year, mon, 1, tzinfo=LOCAL_TZ)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Mês inválido. Use AAAA-MM."
        ) from None
    end = datetime(year + (mon == 12), mon % 12 + 1, 1, tzinfo=LOCAL_TZ)
    return month, start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def brl(value: Decimal) -> str:
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} não encontrado.")


@dataclass
class LedgerService:
    db: Session

    def __post_init__(self):
        self.clients = ClientRepository(self.db)
        self.ledger = LedgerRepository(self.db)

    def balance(self, client_id: str) -> Decimal:
        return self.ledger.total_purchases(client_id) - self.ledger.total_payments(client_id)

    def client_out(self, client: Client, balance: Decimal | None = None) -> ClientOut:
        if balance is None:
            balance = self.balance(client.id)
        over = client.credit_limit is not None and balance > client.credit_limit
        return ClientOut.model_validate(client).model_copy(
            update={"balance": balance, "over_limit": over}
        )

    def list_clients(self, term: str | None) -> list[ClientOut]:
        balances = self.ledger.balances()
        return [self.client_out(c, balances.get(c.id, ZERO)) for c in self.clients.search(term)]

    def require_client(self, client_id: str) -> Client:
        client = self.clients.get(client_id)
        if client is None or not client.active:
            raise not_found("Cliente")
        return client

    def _result(self, record_id: str, client: Client, duplicate: bool) -> RecordResult:
        out = self.client_out(client)
        return RecordResult(
            id=record_id,
            client_id=client.id,
            balance=out.balance,
            over_limit=out.over_limit,
            duplicate=duplicate,
        )

    def record_purchase(self, data: PurchaseIn, user: User) -> RecordResult:
        client = self.require_client(data.client_id)
        existing = self.ledger.get_purchase(data.id)
        if existing:
            if existing.client_id != client.id:
                raise HTTPException(status.HTTP_409_CONFLICT, "Registro já existe.")
            return self._result(existing.id, client, duplicate=True)
        self.ledger.add(
            Purchase(
                id=data.id,
                client_id=client.id,
                amount=data.amount,
                description=data.description or None,
                created_at=to_utc(data.created_at),
                user_id=user.id,
            )
        )
        return self._result(data.id, client, duplicate=False)

    def record_payment(self, data: PaymentIn, user: User) -> RecordResult:
        client = self.require_client(data.client_id)
        existing = self.ledger.get_payment(data.id)
        if existing:
            if existing.client_id != client.id:
                raise HTTPException(status.HTTP_409_CONFLICT, "Registro já existe.")
            return self._result(existing.id, client, duplicate=True)
        self.ledger.add(
            Payment(
                id=data.id,
                client_id=client.id,
                amount=data.amount,
                method=data.method,
                created_at=to_utc(data.created_at),
                user_id=user.id,
            )
        )
        return self._result(data.id, client, duplicate=False)

    def cancel_purchase(self, purchase_id: str) -> RecordResult:
        record = self.ledger.get_purchase(purchase_id)
        if record is None:
            raise not_found("Lançamento")
        record.canceled = True
        self.ledger.save()
        return self._result(record.id, record.client, duplicate=False)

    def cancel_payment(self, payment_id: str) -> RecordResult:
        record = self.ledger.get_payment(payment_id)
        if record is None:
            raise not_found("Pagamento")
        record.canceled = True
        self.ledger.save()
        return self._result(record.id, record.client, duplicate=False)

    def statement(self, client_id: str, month: str | None) -> StatementOut:
        client = self.require_client(client_id)
        month, start, end = month_range(month)
        purchases, payments = self.ledger.entries_between(client.id, start, end)
        entries = [
            EntryOut(
                id=p.id,
                kind="purchase",
                amount=p.amount,
                description=p.description,
                created_at=p.created_at,
                canceled=p.canceled,
            )
            for p in purchases
        ] + [
            EntryOut(
                id=p.id,
                kind="payment",
                amount=p.amount,
                method=p.method,
                created_at=p.created_at,
                canceled=p.canceled,
            )
            for p in payments
        ]
        entries.sort(key=lambda e: e.created_at)
        out = self.client_out(client)
        previous = self.ledger.balance_before(client.id, start)
        return StatementOut(
            client=out,
            month=month,
            entries=entries,
            previous_balance=previous,
            balance=out.balance,
            text=self._statement_text(client.name, month, entries, previous, out.balance),
        )

    @staticmethod
    def _statement_text(
        name: str, month: str, entries: list[EntryOut], previous: Decimal, balance: Decimal
    ) -> str:
        year, mon = month.split("-")
        lines = ["Hortifrúti Recanto Verde", f"Extrato de {name} - {mon}/{year}", ""]
        if previous != 0:
            lines.append(f"Saldo anterior: {brl(previous)}")
        header = len(lines)
        for entry in entries:
            if entry.canceled:
                continue
            day = to_utc(entry.created_at).astimezone(LOCAL_TZ).strftime("%d/%m")
            if entry.kind == "purchase":
                label = "Compra"
                extra = f" ({entry.description})" if entry.description else ""
            else:
                label = "Pagamento"
                extra = f" ({METHOD_LABELS[entry.method.value]})"
            lines.append(f"{day}  {label}  {brl(entry.amount)}{extra}")
        if len(lines) == header:
            lines.append("Nenhuma movimentação no mês.")
        lines += ["", f"SALDO: {brl(balance)}"]
        return "\n".join(lines)

    def summary(self, month: str | None) -> SummaryOut:
        month, start, end = month_range(month)
        balances = self.ledger.balances()
        sold, received = self.ledger.month_totals(start, end)
        debtors = sorted(
            ((cid, b) for cid, b in balances.items() if b > 0), key=lambda item: -item[1]
        )[:5]
        top = []
        for cid, value in debtors:
            client = self.clients.get(cid)
            if client:
                top.append(DebtorOut(id=cid, name=client.name, balance=value))
        receivable = sum((b for b in balances.values() if b > 0), ZERO)
        return SummaryOut(
            month=month,
            total_receivable=receivable,
            received_in_month=received,
            sold_on_tab_in_month=sold,
            top_debtors=top,
        )


@dataclass
class OrderService:
    db: Session

    def __post_init__(self):
        self.orders = OrderRepository(self.db)
        self.ledger = LedgerService(self.db)

    @staticmethod
    def to_out(order: Order) -> OrderOut:
        return OrderOut(
            id=order.id,
            client_id=order.client_id,
            client_name=order.client.name,
            items=order.items,
            address=order.address,
            status=order.status,
            payment=order.payment,
            created_at=order.created_at,
        )

    def list(self, status_filter: OrderStatus | None) -> list[OrderOut]:
        return [self.to_out(o) for o in self.orders.list(status_filter)]

    def create(self, data: OrderIn, user: User) -> OrderOut:
        existing = self.orders.get(data.id)
        if existing:
            return self.to_out(existing)
        client = self.ledger.require_client(data.client_id)
        address = data.address or client.address
        if not address:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe o endereço de entrega."
            )
        order = Order(
            id=data.id,
            client_id=client.id,
            items=data.items,
            address=address,
            payment=data.payment,
            created_at=to_utc(data.created_at),
            user_id=user.id,
        )
        return self.to_out(self.orders.add(order))

    def change_status(self, order_id: str, data: OrderStatusIn, user: User) -> OrderOut:
        order = self.orders.get(order_id)
        if order is None:
            raise not_found("Pedido")
        if data.status == order.status:
            return self.to_out(order)
        if data.status not in ORDER_FLOW[order.status]:
            raise HTTPException(status.HTTP_409_CONFLICT, "Mudança de situação não permitida.")
        if data.status == OrderStatus.delivered and order.payment == OrderPayment.tab:
            if data.amount is None or data.purchase_id is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Informe o valor do pedido para anotar no fiado.",
                )
            self.ledger.record_purchase(
                PurchaseIn(
                    id=data.purchase_id,
                    client_id=order.client_id,
                    amount=data.amount,
                    description="Entrega",
                    created_at=datetime.now(timezone.utc),
                ),
                user,
            )
            order.purchase_id = data.purchase_id
        order.status = data.status
        return self.to_out(self.orders.save(order))
