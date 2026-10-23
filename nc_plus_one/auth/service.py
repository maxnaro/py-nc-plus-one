"""Login and registration rules, independent of HTTP request handling."""

from nc_plus_one.auth import repository
from nc_plus_one.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from nc_plus_one.errors import ConflictError, UnauthorizedError


def login(*, password: str, name: str | None = None, email: str | None = None):
    user = repository.get_login_user(name=name, email=email)
    if user is None or not verify_password(password, user["hashed_password"]):
        raise UnauthorizedError("Invalid login credentials.")

    return {"access_token": create_access_token(user["id"])}


def register(*, name: str, email: str, password: str):
    if repository.get_user_by_email(email):
        raise ConflictError("Email already registered.")

    return repository.create_user(name, email, hash_password(password))
