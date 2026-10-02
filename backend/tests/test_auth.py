from tests.conftest import PASSWORD


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401
    bad = {"Authorization": "Bearer not-a-token"}
    assert client.get("/auth/me", headers=bad).status_code == 401


def test_login_with_wrong_password_is_generic(client):
    response = client.post("/auth/login", json={"login": "marta", "password": "errada"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário ou senha inválidos."


def test_account_is_locked_after_five_failures(client):
    for _ in range(5):
        client.post("/auth/login", json={"login": "marta", "password": "errada"})
    response = client.post("/auth/login", json={"login": "marta", "password": PASSWORD})
    assert response.status_code == 429


def test_password_is_not_stored_in_plain_text(db, users):
    assert users["owner"].password_hash.startswith("$2b$12$")
    assert PASSWORD not in users["owner"].password_hash


def test_refresh_and_logout(client, owner_headers):
    assert client.post("/auth/refresh").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.post("/auth/refresh").status_code == 401
