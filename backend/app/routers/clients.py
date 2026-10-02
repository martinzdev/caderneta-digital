from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DbSession, Owner
from app.models import Client
from app.repositories import ClientRepository
from app.schemas import ClientIn, ClientOut, ClientUpdate, StatementOut
from app.services import LedgerService

router = APIRouter(prefix="/clients", tags=["clients"])

PHONE_TAKEN = "Já existe um cliente com esse telefone."


@router.get("", response_model=list[ClientOut])
def list_clients(db: DbSession, _: CurrentUser, q: str | None = Query(None, max_length=100)):
    return LedgerService(db).list_clients(q)


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(data: ClientIn, db: DbSession, _: CurrentUser):
    repo = ClientRepository(db)
    service = LedgerService(db)
    if data.id and (existing := repo.get(data.id)):
        return service.client_out(existing)
    if data.phone and repo.phone_taken(data.phone):
        raise HTTPException(status.HTTP_409_CONFLICT, PHONE_TAKEN)
    client = repo.add(Client(**data.model_dump(exclude_none=True)))
    return service.client_out(client)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: str, db: DbSession, _: CurrentUser):
    service = LedgerService(db)
    return service.client_out(service.require_client(client_id))


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: str, data: ClientUpdate, db: DbSession, _: CurrentUser):
    service = LedgerService(db)
    repo = ClientRepository(db)
    client = service.require_client(client_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("phone") and repo.phone_taken(changes["phone"], ignore_id=client.id):
        raise HTTPException(status.HTTP_409_CONFLICT, PHONE_TAKEN)
    for field, value in changes.items():
        setattr(client, field, value)
    return service.client_out(repo.save(client))


@router.post("/{client_id}/deactivate", response_model=ClientOut)
def deactivate_client(client_id: str, db: DbSession, _: Owner):
    service = LedgerService(db)
    client = service.require_client(client_id)
    if service.balance(client.id) != 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Cliente com saldo em aberto não pode ser desativado."
        )
    client.active = False
    return service.client_out(ClientRepository(db).save(client))


@router.get("/{client_id}/statement", response_model=StatementOut)
def statement(
    client_id: str,
    db: DbSession,
    _: CurrentUser,
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
):
    return LedgerService(db).statement(client_id, month)
