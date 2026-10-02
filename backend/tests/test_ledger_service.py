from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import Client, PaymentMethod
from app.schemas import PaymentIn, PurchaseIn
from app.services import LedgerService, brl, month_range
from tests.conftest import new_id


@pytest.fixture
def service(db):
    return LedgerService(db)


@pytest.fixture
def joao(db):
    client = Client(name="João Pereira", phone="69999991234", credit_limit=Decimal("100.00"))
    db.add(client)
    db.commit()
    return client


def purchase(client_id, amount, **extra):
    return PurchaseIn(
        id=new_id(),
        client_id=client_id,
        amount=Decimal(amount),
        created_at=datetime(2026, 10, 8, 14, 0, tzinfo=timezone.utc),
        **extra,
    )


def payment(client_id, amount):
    return PaymentIn(
        id=new_id(),
        client_id=client_id,
        amount=Decimal(amount),
        method=PaymentMethod.pix,
        created_at=datetime(2026, 10, 9, 14, 0, tzinfo=timezone.utc),
    )


def test_balance_is_purchases_minus_payments(service, joao, users):
    service.record_purchase(purchase(joao.id, "45.00"), users["owner"])
    service.record_purchase(purchase(joao.id, "42.50"), users["owner"])
    result = service.record_payment(payment(joao.id, "20.00"), users["staff"])

    assert result.balance == Decimal("67.50")
    assert service.balance(joao.id) == Decimal("67.50")


def test_canceled_purchase_is_ignored(service, joao, users):
    first = service.record_purchase(purchase(joao.id, "30.00"), users["owner"])
    service.record_purchase(purchase(joao.id, "10.00"), users["owner"])

    result = service.cancel_purchase(first.id)

    assert result.balance == Decimal("10.00")


def test_same_purchase_twice_is_saved_once(service, joao, users):
    data = purchase(joao.id, "23.40")

    service.record_purchase(data, users["owner"])
    again = service.record_purchase(data, users["owner"])

    assert again.duplicate is True
    assert service.balance(joao.id) == Decimal("23.40")


def test_over_limit_flag(service, joao, users):
    result = service.record_purchase(purchase(joao.id, "110.90"), users["owner"])

    assert result.over_limit is True


def test_payment_can_leave_credit(service, joao, users):
    service.record_purchase(purchase(joao.id, "10.00"), users["owner"])

    result = service.record_payment(payment(joao.id, "15.00"), users["owner"])

    assert result.balance == Decimal("-5.00")


def test_statement_text_lists_entries_and_balance(service, joao, users):
    service.record_purchase(purchase(joao.id, "23.40", description="frutas"), users["owner"])
    service.record_payment(payment(joao.id, "10.00"), users["owner"])

    statement = service.statement(joao.id, "2026-10")

    assert "08/10  Compra  R$ 23,40 (frutas)" in statement.text
    assert "09/10  Pagamento  R$ 10,00 (Pix)" in statement.text
    assert statement.text.endswith("SALDO: R$ 13,40")


def test_unknown_client_raises_404(service, users):
    with pytest.raises(HTTPException) as error:
        service.record_purchase(purchase(new_id(), "5.00"), users["owner"])
    assert error.value.status_code == 404


@pytest.mark.parametrize("value,expected", [
    (Decimal("0"), "R$ 0,00"),
    (Decimal("1234.5"), "R$ 1.234,50"),
    (Decimal("87.5"), "R$ 87,50"),
])
def test_brl_format(value, expected):
    assert brl(value) == expected


def test_month_range_crosses_year():
    month, start, end = month_range("2026-12")
    assert month == "2026-12"
    assert start.year == 2026 and end.year == 2027 and end.month == 1
