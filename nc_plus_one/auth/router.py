from fastapi import APIRouter, status

from nc_plus_one.auth import service
from nc_plus_one.auth.schemas import LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(login_request: LoginRequest):
    return service.login(
        name=login_request.name,
        email=login_request.email,
        password=login_request.password,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(register_request: RegisterRequest):
    return service.register(
        name=register_request.name,
        email=register_request.email,
        password=register_request.password,
    )
