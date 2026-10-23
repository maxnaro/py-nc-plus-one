from typing import Self

from pydantic import BaseModel, model_validator


class LoginRequest(BaseModel):
    email: str | None = None
    name: str | None = None
    password: str

    @model_validator(mode="after")
    def require_either(self) -> Self:
        has_email = self.email is not None
        has_name = self.name is not None

        if has_email == has_name:
            raise ValueError("LoginRequest requires either email or name, not both")

        return self
