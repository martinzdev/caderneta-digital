import argparse
import getpass
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Client, Payment, PaymentMethod, Purchase, Role, User
from app.security import hash_password

COMMON_PASSWORDS = {"12345678", "123456789", "password", "senha123", "abcd1234"}

FIRST_NAMES = [
    "João", "Maria", "Antônio", "Rosa", "Josefa", "Jonas", "Luzia", "Pedro", "Ana", "Sebastião",
    "Francisca", "José", "Raimunda", "Carlos", "Fátima", "Paulo", "Neide", "Marcos", "Cleide",
    "Valdir", "Tereza", "Edson", "Lúcia", "Benedito", "Sandra", "Gilmar",
]
LAST_NAMES = [
    "Pereira", "Souza", "Lima", "Alves", "Ramos", "Ferreira", "Martins", "Rocha", "Nunes",
    "Oliveira", "Santos", "Costa", "Ribeiro", "Barbosa", "Gomes", "Cardoso", "Teixeira",
]


def create_user(name: str, login: str, role: str) -> None:
    password = os.environ.get("CADERNETA_PASSWORD") or getpass.getpass("Senha: ")
    if len(password) < 8 or password.lower() in COMMON_PASSWORDS:
        raise SystemExit("Senha fraca: use pelo menos 8 caracteres e evite senhas comuns.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.login == login.lower())):
            raise SystemExit("Login já cadastrado.")
        db.add(
            User(
                name=name,
                login=login.lower(),
                password_hash=hash_password(password),
                role=Role(role),
            )
        )
        db.commit()
    print(f"Usuário {login} criado.")


def seed_demo(clients: int, entries: int) -> None:
    rng = random.Random(42)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.role == Role.owner))
        if user is None:
            raise SystemExit("Crie primeiro um usuário com perfil owner.")
        created = []
        names = sorted({f"{f} {last}" for f in FIRST_NAMES for last in LAST_NAMES})
        for i, name in enumerate(rng.sample(names, clients)):
            client = Client(name=name, phone=f"6999{i:07d}", credit_limit=Decimal("150.00"))
            db.add(client)
            created.append(client)
        db.flush()
        now = datetime.now(timezone.utc)
        for _ in range(entries):
            client = rng.choice(created)
            when = now - timedelta(days=rng.randint(0, 60), minutes=rng.randint(0, 600))
            if rng.random() < 0.75:
                db.add(Purchase(
                    id=str(uuid.uuid4()), client_id=client.id, user_id=user.id, created_at=when,
                    amount=Decimal(rng.randint(300, 6000)) / 100,
                ))
            else:
                db.add(Payment(
                    id=str(uuid.uuid4()), client_id=client.id, user_id=user.id, created_at=when,
                    amount=Decimal(rng.randint(1000, 5000)) / 100,
                    method=rng.choice(list(PaymentMethod)),
                ))
        db.commit()
    print(f"{clients} clientes e {entries} lançamentos de teste criados.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    user_cmd = sub.add_parser("create-user")
    user_cmd.add_argument("--name", required=True)
    user_cmd.add_argument("--login", required=True)
    user_cmd.add_argument("--role", choices=[r.value for r in Role], default="staff")

    seed_cmd = sub.add_parser("seed-demo")
    seed_cmd.add_argument("--clients", type=int, default=110)
    seed_cmd.add_argument("--entries", type=int, default=1000)

    args = parser.parse_args()
    if args.command == "create-user":
        create_user(args.name, args.login, args.role)
    else:
        seed_demo(args.clients, args.entries)


if __name__ == "__main__":
    main()
