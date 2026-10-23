import os
import time
from enum import Enum
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()


class JWT(Enum):
    ALGORITHM = "HS256"
    TYPE = "JWT"
    EXPIRY = 1800  # Expiry in seconds


def hash_password(password: str | bytes) -> str:
    return pwd_context.hash(password)


def verify_password(
    password: str | bytes,
    hashed_password: str | bytes,
) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    now = int(time.time())

    payload = {"sub": str(user_id), "iat": now, "exp": now + JWT.EXPIRY.value}

    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT.ALGORITHM.value)


def _validate_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        os.environ["JWT_SECRET"],
        algorithms=[JWT.ALGORITHM.value],
        options={"require": ["sub", "iat", "exp"]},
    )


def require_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> dict:
    try:
        return _validate_access_token(credentials.credentials)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
