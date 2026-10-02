from tests.conftest import new_id, now_iso


def create_client(client, headers, **extra):
    body = {"name": "João Pereira", "phone": "69999991234", "credit_limit": "100.00", **extra}
    response = client.post("/clients", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def add_purchase(client, headers, client_id, amount="23.40", purchase_id=None):
    return client.post(
        "/purchases",
        json={
            "id": purchase_id or new_id(),
            "client_id": client_id,
            "amount": amount,
            "description": "frutas e verduras",
            "created_at": now_iso(),
        },
        headers=headers,
    )


def test_routes_require_token(client):
    assert client.get("/clients").status_code == 401
    assert client.post("/purchases", json={}).status_code == 401


def test_search_ignores_accents_and_case(client, owner_headers):
    create_client(client, owner_headers)
    create_client(client, owner_headers, name="Antônio Lima", phone="69988887777")

    names = [c["name"] for c in client.get("/clients?q=ANTONIO", headers=owner_headers).json()]

    assert names == ["Antônio Lima"]


def test_duplicate_phone_is_rejected(client, owner_headers):
    create_client(client, owner_headers)
    response = client.post(
        "/clients", json={"name": "Outro", "phone": "69999991234"}, headers=owner_headers
    )
    assert response.status_code == 409


def test_purchase_flow_updates_balance(client, staff_headers):
    joao = create_client(client, staff_headers)

    response = add_purchase(client, staff_headers, joao["id"])

    assert response.status_code == 201
    assert response.json()["balance"] == "23.40"
    detail = client.get(f"/clients/{joao['id']}", headers=staff_headers).json()
    assert detail["balance"] == "23.40"


def test_sync_retry_does_not_duplicate(client, owner_headers):
    joao = create_client(client, owner_headers)
    purchase_id = new_id()

    first = add_purchase(client, owner_headers, joao["id"], purchase_id=purchase_id)
    second = add_purchase(client, owner_headers, joao["id"], purchase_id=purchase_id)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["balance"] == "23.40"


def test_invalid_amount_is_rejected(client, owner_headers):
    joao = create_client(client, owner_headers)
    for amount in ("0", "-5", "10.555"):
        assert add_purchase(client, owner_headers, joao["id"], amount=amount).status_code == 422


def test_sql_injection_is_treated_as_text(client, owner_headers):
    create_client(client, owner_headers)
    response = client.get("/clients", params={"q": "x' OR '1'='1"}, headers=owner_headers)
    assert response.status_code == 200
    assert response.json() == []
    assert len(client.get("/clients", headers=owner_headers).json()) == 1


def test_markup_is_rejected(client, owner_headers):
    response = client.post(
        "/clients", json={"name": "<script>alert(1)</script>"}, headers=owner_headers
    )
    assert response.status_code == 422
    assert "Traceback" not in response.text


def test_staff_cannot_cancel(client, owner_headers, staff_headers):
    joao = create_client(client, owner_headers)
    purchase = add_purchase(client, owner_headers, joao["id"]).json()

    url = f"/purchases/{purchase['id']}/cancel"

    assert client.post(url, headers=staff_headers).status_code == 403
    response = client.post(url, headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["balance"] == "0.00"


def test_statement_endpoint(client, owner_headers):
    joao = create_client(client, owner_headers)
    add_purchase(client, owner_headers, joao["id"])

    response = client.get(f"/clients/{joao['id']}/statement", headers=owner_headers)

    assert response.status_code == 200
    assert "SALDO: R$ 23,40" in response.json()["text"]


def test_tab_order_creates_purchase_on_delivery(client, owner_headers):
    joao = create_client(client, owner_headers, address="Rua das Flores, 10")
    order = client.post(
        "/orders",
        json={
            "id": new_id(),
            "client_id": joao["id"],
            "items": "2 kg tomate, 1 alface",
            "payment": "tab",
            "created_at": now_iso(),
        },
        headers=owner_headers,
    ).json()
    assert order["address"] == "Rua das Flores, 10"

    skip = client.post(
        f"/orders/{order['id']}/status", json={"status": "delivered"}, headers=owner_headers
    )
    assert skip.status_code == 409

    client.post(f"/orders/{order['id']}/status", json={"status": "packed"}, headers=owner_headers)
    missing_amount = client.post(
        f"/orders/{order['id']}/status", json={"status": "delivered"}, headers=owner_headers
    )
    assert missing_amount.status_code == 422

    delivered = client.post(
        f"/orders/{order['id']}/status",
        json={"status": "delivered", "amount": "18.90", "purchase_id": new_id()},
        headers=owner_headers,
    )
    assert delivered.json()["status"] == "delivered"
    assert client.get(f"/clients/{joao['id']}", headers=owner_headers).json()["balance"] == "18.90"


def test_summary(client, owner_headers):
    joao = create_client(client, owner_headers)
    add_purchase(client, owner_headers, joao["id"], amount="50.00")

    summary = client.get("/summary", headers=owner_headers).json()

    assert summary["total_receivable"] == "50.00"
    assert summary["top_debtors"][0]["name"] == "João Pereira"


def add_payment(client, headers, client_id, amount="10.00"):
    return client.post(
        "/payments",
        json={
            "id": new_id(),
            "client_id": client_id,
            "amount": amount,
            "method": "cash",
            "created_at": now_iso(),
        },
        headers=headers,
    )


def test_payment_and_cancel(client, owner_headers):
    joao = create_client(client, owner_headers)
    add_purchase(client, owner_headers, joao["id"], amount="30.00")

    payment = add_payment(client, owner_headers, joao["id"])
    assert payment.status_code == 201
    assert payment.json()["balance"] == "20.00"

    canceled = client.post(f"/payments/{payment.json()['id']}/cancel", headers=owner_headers)
    assert canceled.json()["balance"] == "30.00"


def test_update_client(client, owner_headers):
    joao = create_client(client, owner_headers)
    create_client(client, owner_headers, name="Maria Souza", phone="69988887777")

    response = client.patch(
        f"/clients/{joao['id']}", json={"address": "Rua A, 15"}, headers=owner_headers
    )
    assert response.json()["address"] == "Rua A, 15"

    taken = client.patch(
        f"/clients/{joao['id']}", json={"phone": "69988887777"}, headers=owner_headers
    )
    assert taken.status_code == 409


def test_client_with_open_balance_cannot_be_deactivated(client, owner_headers, staff_headers):
    joao = create_client(client, owner_headers)
    add_purchase(client, owner_headers, joao["id"], amount="10.00")
    url = f"/clients/{joao['id']}/deactivate"

    assert client.post(url, headers=staff_headers).status_code == 403
    assert client.post(url, headers=owner_headers).status_code == 409

    add_payment(client, owner_headers, joao["id"], amount="10.00")
    assert client.post(url, headers=owner_headers).json()["active"] is False
    assert client.get(f"/clients/{joao['id']}", headers=owner_headers).status_code == 404


def test_orders_can_be_filtered_by_status(client, owner_headers):
    joao = create_client(client, owner_headers, address="Rua das Flores, 10")
    for _ in range(2):
        client.post(
            "/orders",
            json={
                "id": new_id(),
                "client_id": joao["id"],
                "items": "1 alface",
                "payment": "on_delivery",
                "created_at": now_iso(),
            },
            headers=owner_headers,
        )

    orders = client.get("/orders", params={"status_filter": "new"}, headers=owner_headers).json()

    assert len(orders) == 2
    assert client.get("/orders?status_filter=delivered", headers=owner_headers).json() == []
