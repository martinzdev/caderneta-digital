import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import create_app
from app.models import Role, User
from app.security import hash_password

PASSWORD = "horta-2026"


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def users(db):
    password_hash = hash_password(PASSWORD)
    owner = User(name="Marta", login="marta", password_hash=password_hash, role=Role.owner)
    staff = User(name="Bruno", login="bruno", password_hash=password_hash, role=Role.staff)
    db.add_all([owner, staff])
    db.commit()
    return {"owner": owner, "staff": staff}


@pytest.fixture
def client(session_factory, users):
    app = create_app()

    def override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, user: str = "marta") -> dict:
    response = client.post("/auth/login", json={"login": user, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def owner_headers(client):
    return login(client, "marta")


@pytest.fixture
def staff_headers(client):
    return login(client, "bruno")


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
