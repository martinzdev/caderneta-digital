import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.models import OrderPayment, OrderStatus, PaymentMethod, Role

TAG_PATTERN = re.compile(r"[<>]")


def no_markup(value: str | None) -> str | None:
    if value is not None and TAG_PATTERN.search(value):
        raise ValueError("HTML is not allowed")
    return value


def valid_uuid(value: str) -> str:
    uuid.UUID(value)
    return value


Text = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(no_markup)]
Uuid = Annotated[str, AfterValidator(valid_uuid)]
Money = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
Phone = Annotated[str, StringConstraints(pattern=r"^\d{10,11}$")]


class LoginIn(BaseModel):
    login: str = Field(max_length=120)
    password: str = Field(max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    role: Role


class ClientIn(BaseModel):
    id: Uuid | None = None
    name: Annotated[Text, StringConstraints(min_length=1, max_length=100)]
    phone: Phone | None = None
    address: Annotated[Text, StringConstraints(max_length=200)] | None = None
    credit_limit: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)] | None = None


class ClientUpdate(BaseModel):
    name: Annotated[Text, StringConstraints(min_length=1, max_length=100)] | None = None
    phone: Phone | None = None
    address: Annotated[Text, StringConstraints(max_length=200)] | None = None
    credit_limit: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)] | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str | None
    address: str | None
    credit_limit: Decimal | None
    active: bool
    balance: Decimal = Decimal("0.00")
    over_limit: bool = False


class PurchaseIn(BaseModel):
    id: Uuid
    client_id: Uuid
    amount: Money
    description: Annotated[Text, StringConstraints(max_length=120)] | None = None
    created_at: datetime


class PaymentIn(BaseModel):
    id: Uuid
    client_id: Uuid
    amount: Money
    method: PaymentMethod
    created_at: datetime


class EntryOut(BaseModel):
    id: str
    kind: str
    amount: Decimal
    description: str | None = None
    method: PaymentMethod | None = None
    created_at: datetime
    canceled: bool


class RecordResult(BaseModel):
    id: str
    client_id: str
    balance: Decimal
    over_limit: bool
    duplicate: bool = False


class StatementOut(BaseModel):
    client: ClientOut
    month: str
    entries: list[EntryOut]
    balance: Decimal
    text: str


class OrderIn(BaseModel):
    id: Uuid
    client_id: Uuid
    items: Annotated[Text, StringConstraints(min_length=1, max_length=500)]
    address: Annotated[Text, StringConstraints(min_length=1, max_length=200)] | None = None
    payment: OrderPayment
    created_at: datetime


class OrderStatusIn(BaseModel):
    status: OrderStatus
    amount: Money | None = None
    purchase_id: Uuid | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    client_name: str
    items: str
    address: str
    status: OrderStatus
    payment: OrderPayment
    created_at: datetime


class DebtorOut(BaseModel):
    id: str
    name: str
    balance: Decimal


class SummaryOut(BaseModel):
    month: str
    total_receivable: Decimal
    received_in_month: Decimal
    sold_on_tab_in_month: Decimal
    top_debtors: list[DebtorOut]
