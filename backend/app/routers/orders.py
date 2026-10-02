from fastapi import APIRouter, status

from app.deps import CurrentUser, DbSession
from app.models import OrderStatus
from app.schemas import OrderIn, OrderOut, OrderStatusIn
from app.services import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
def list_orders(db: DbSession, _: CurrentUser, status_filter: OrderStatus | None = None):
    return OrderService(db).list(status_filter)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderIn, db: DbSession, user: CurrentUser):
    return OrderService(db).create(data, user)


@router.post("/{order_id}/status", response_model=OrderOut)
def change_status(order_id: str, data: OrderStatusIn, db: DbSession, user: CurrentUser):
    return OrderService(db).change_status(order_id, data, user)
