from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.models import RefreshToken, User
from app.schemas import LoginIn, TokenOut, UserOut
from app.security import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
INVALID_LOGIN = "Usuário ou senha inválidos."


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _issue_tokens(db: DbSession, user: User, response: Response) -> TokenOut:
    settings = get_settings()
    raw, token_hash = new_refresh_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
    db.commit()
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/auth",
    )
    return TokenOut(access_token=create_access_token(user.id, user.role.value))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: DbSession, response: Response):
    settings = get_settings()
    user = db.scalar(select(User).where(User.login == data.login.strip().lower()))
    now = datetime.now(timezone.utc)
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)
    if user.locked_until and _aware(user.locked_until) > now:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitas tentativas. Aguarde alguns minutos e tente de novo.",
        )
    if not verify_password(data.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= settings.max_login_attempts:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_attempts = 0
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)
    user.failed_attempts = 0
    user.locked_until = None
    return _issue_tokens(db, user, response)


@router.post("/refresh", response_model=TokenOut)
def refresh(db: DbSession, response: Response, refresh_token: str | None = Cookie(None)):
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Entre novamente.")
    if not refresh_token:
        raise unauthorized
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(refresh_token))
    )
    if stored is None or stored.revoked or _aware(stored.expires_at) < datetime.now(timezone.utc):
        raise unauthorized
    user = db.get(User, stored.user_id)
    if user is None or not user.active:
        raise unauthorized
    stored.revoked = True
    return _issue_tokens(db, user, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(db: DbSession, response: Response, refresh_token: str | None = Cookie(None)):
    if refresh_token:
        stored = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(refresh_token)
            )
        )
        if stored:
            stored.revoked = True
            db.commit()
    response.delete_cookie(REFRESH_COOKIE, path="/auth")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
