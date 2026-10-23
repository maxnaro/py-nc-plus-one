from enum import StrEnum, auto
from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from db.connection import query
from src.auth.auth import create_access_token, hash_password, verify_password
from src.auth.models import LoginRequest, RegisterRequest


class ROUTES(StrEnum):
    AUTH = auto()
    LOGIN = auto()
    REGISTER = auto()


router = APIRouter(prefix=f"/{ROUTES.AUTH.value}", tags=[ROUTES.AUTH.value])


@router.post(f"/{ROUTES.LOGIN.value}")
def login(login_request: LoginRequest):
    identifier, value = (
        ("name", login_request.name)
        if login_request.name is not None
        else ("email", login_request.email)
    )
    result = query(
        f"SELECT id, hashed_password FROM users WHERE {identifier} = %s",
        value,
        fetch_one=True,
    )

    def raise_login_error() -> NoReturn:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid login credentials.",
            },
        )

    if result is None or not verify_password(
        login_request.password, result["hashed_password"]
    ):
        raise_login_error()

    return {"access_token": create_access_token(result["id"])}


@router.post(f"/{ROUTES.REGISTER.value}", status_code=status.HTTP_201_CREATED)
def register(register_request: RegisterRequest):
    result = query(
        "SELECT id FROM users WHERE email = %s", register_request.email, fetch_one=True
    )
    if result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Email already registered."},
        )

    hashed_password = hash_password(register_request.password)

    return query(
        """
        INSERT INTO users (name, email, hashed_password)
        VALUES (%s, %s, %s)
        RETURNING id, name, email, created_at;
    """,
        register_request.name,
        register_request.email,
        hashed_password,
        fetch_one=True,
    )
