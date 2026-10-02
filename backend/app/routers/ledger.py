from fastapi import APIRouter, Query, Response, status

from app.deps import CurrentUser, DbSession, Owner
from app.schemas import PaymentIn, PurchaseIn, RecordResult, SummaryOut
from app.services import LedgerService

router = APIRouter(tags=["ledger"])


@router.post("/purchases", response_model=RecordResult, status_code=status.HTTP_201_CREATED)
def create_purchase(data: PurchaseIn, db: DbSession, user: CurrentUser, response: Response):
    result = LedgerService(db).record_purchase(data, user)
    if result.duplicate:
        response.status_code = status.HTTP_200_OK
    return result


@router.post("/purchases/{purchase_id}/cancel", response_model=RecordResult)
def cancel_purchase(purchase_id: str, db: DbSession, _: Owner):
    return LedgerService(db).cancel_purchase(purchase_id)


@router.post("/payments", response_model=RecordResult, status_code=status.HTTP_201_CREATED)
def create_payment(data: PaymentIn, db: DbSession, user: CurrentUser, response: Response):
    result = LedgerService(db).record_payment(data, user)
    if result.duplicate:
        response.status_code = status.HTTP_200_OK
    return result


@router.post("/payments/{payment_id}/cancel", response_model=RecordResult)
def cancel_payment(payment_id: str, db: DbSession, _: Owner):
    return LedgerService(db).cancel_payment(payment_id)


@router.get("/summary", response_model=SummaryOut)
def summary(
    db: DbSession, _: CurrentUser, month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")
):
    return LedgerService(db).summary(month)
