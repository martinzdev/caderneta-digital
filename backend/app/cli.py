import argparse
import getpass
import os

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Role, User
from app.security import hash_password

COMMON_PASSWORDS = {"12345678", "123456789", "password", "senha123", "abcd1234"}

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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    user_cmd = sub.add_parser("create-user")
    user_cmd.add_argument("--name", required=True)
    user_cmd.add_argument("--login", required=True)
    user_cmd.add_argument("--role", choices=[r.value for r in Role], default="staff")

    args = parser.parse_args()
    if args.command == "create-user":
        create_user(args.name, args.login, args.role)


if __name__ == "__main__":
    main()
