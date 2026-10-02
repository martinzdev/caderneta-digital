from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Entre novamente.")
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized from None
    user = db.get(User, payload.get("sub"))
    if user is None or not user.active:
        raise unauthorized
    return user


def owner_only(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != Role.owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas a proprietária pode fazer isso.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
Owner = Annotated[User, Depends(owner_only)]
