"""User queries used by authentication and registration."""

from nc_plus_one.db.connection import query


def get_login_user(*, name: str | None, email: str | None):
    identifier, value = ("name", name) if name is not None else ("email", email)
    return query(
        f"SELECT id, hashed_password FROM users WHERE {identifier} = %s",
        value,
        fetch_one=True,
    )


def get_user_by_email(email: str):
    return query("SELECT id FROM users WHERE email = %s", email, fetch_one=True)


def create_user(name: str, email: str, hashed_password: str):
    return query(
        """
        INSERT INTO users (name, email, hashed_password)
        VALUES (%s, %s, %s)
        RETURNING id, name, email, created_at;
        """,
        name,
        email,
        hashed_password,
        fetch_one=True,
    )
