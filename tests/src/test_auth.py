"""Registration and login contracts: bcrypt passwords and HS256 JWTs."""

from datetime import datetime

import jwt
import pytest
from passlib.context import CryptContext

JWT_SECRET = "login-tests-only-signing-key-at-least-32-bytes"
PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(autouse=True)
def jwt_signing_key(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)


@pytest.fixture(params=(1, 2), ids=("alice", "bob"))
def login_user(seeded_connection, request):
    """Give a seeded user a known password with a fresh salted hash."""
    password = f"correct-password-for-user-{request.param}"
    password_hash = PASSWORD_CONTEXT.hash(password)

    with seeded_connection.cursor() as cursor:
        cursor.execute(
            """UPDATE users SET hashed_password = %s WHERE id = %s
               RETURNING id, name, email""",
            (password_hash, request.param),
        )
        user_id, name, email = cursor.fetchone()

    return {
        "id": user_id,
        "name": name,
        "email": email,
        "password": password,
        "password_hash": password_hash,
    }


@pytest.fixture(params=("name", "email"))
def login_identifier(login_user, request):
    return {request.param: login_user[request.param]}


@pytest.mark.parametrize(
    ("submitted_password", "expected_status"),
    (
        pytest.param("password", 200, id="correct-plaintext-password"),
        pytest.param("incorrect-password", 401, id="incorrect-password"),
        pytest.param("password_hash", 401, id="stored-hash-is-not-a-password"),
    ),
)
def test_login_verifies_password_against_stored_hash(
    client, login_user, login_identifier, submitted_password, expected_status
):
    response = client.post(
        "/api/auth/login",
        json={
            **login_identifier,
            "password": login_user.get(submitted_password, submitted_password),
        },
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize("include_null_identifier", (False, True))
def test_login_returns_signed_jwt_identifying_user(
    client, login_user, login_identifier, include_null_identifier
):
    credentials = {**login_identifier, "password": login_user["password"]}
    if include_null_identifier:
        other_identifier = "email" if "name" in login_identifier else "name"
        credentials[other_identifier] = None

    response = client.post(
        "/api/auth/login",
        json=credentials,
    )

    assert response.status_code == 200
    payload = jwt.decode(
        response.json()["access_token"], JWT_SECRET, algorithms=["HS256"]
    )
    assert payload["sub"] == str(login_user["id"])


def test_login_does_not_reveal_which_credential_is_invalid(
    client, login_user, login_identifier
):
    wrong_password = client.post(
        "/api/auth/login",
        json={**login_identifier, "password": "incorrect-password"},
    )
    identifier = next(iter(login_identifier))
    unknown_identifier = client.post(
        "/api/auth/login",
        json={identifier: "unknown@example.com", "password": login_user["password"]},
    )

    assert wrong_password.status_code == unknown_identifier.status_code == 401
    assert wrong_password.json() == unknown_identifier.json()


@pytest.mark.parametrize(
    "identifiers",
    (
        pytest.param(
            {"name": "Alice Rahman", "email": "alice@example.com"},
            id="both-identifiers-same-user",
        ),
        pytest.param(
            {"name": "Alice Rahman", "email": "bob@example.com"},
            id="both-identifiers-different-users",
        ),
        pytest.param({}, id="neither-identifier"),
        pytest.param({"name": None}, id="null-name"),
        pytest.param({"email": None}, id="null-email"),
        pytest.param({"name": None, "email": None}, id="both-identifiers-null"),
    ),
)
def test_login_requires_exactly_one_identifier(client, identifiers):
    response = client.post(
        "/api/auth/login", json={**identifiers, "password": "password123"}
    )

    assert response.status_code == 422


def test_login_requires_password(client, login_identifier):
    response = client.post("/api/auth/login", json=login_identifier)

    assert response.status_code == 422


@pytest.fixture
def registration_data():
    return {
        "name": "Grace Hopper",
        "email": "grace@example.com",
        "password": "registration-password-123",
    }


def test_registration_responds_with_201_and_created_user(
    client, seeded_connection, registration_data
):
    response = client.post("/api/auth/register", json=registration_data)

    assert response.status_code == 201
    created_user = response.json()
    assert created_user["name"] == registration_data["name"]
    assert created_user["email"] == registration_data["email"]
    assert "password" not in created_user
    assert "hashed_password" not in created_user

    with seeded_connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, email, created_at FROM users WHERE email = %s",
            (registration_data["email"],),
        )
        stored_user = cursor.fetchone()

    assert stored_user is not None
    assert created_user["id"] == stored_user[0]
    assert created_user["name"] == stored_user[1]
    assert created_user["email"] == stored_user[2]
    assert datetime.fromisoformat(created_user["created_at"]) == stored_user[3]


def test_password_is_hashed(client, seeded_connection, registration_data):
    response = client.post("/api/auth/register", json=registration_data)

    assert response.status_code == 201
    with seeded_connection.cursor() as cursor:
        cursor.execute(
            "SELECT hashed_password FROM users WHERE email = %s",
            (registration_data["email"],),
        )
        stored_user = cursor.fetchone()

    assert stored_user is not None
    hashed_password = stored_user[0]
    assert hashed_password != registration_data["password"]
    assert PASSWORD_CONTEXT.identify(hashed_password) == "bcrypt"
    assert PASSWORD_CONTEXT.verify(registration_data["password"], hashed_password)


@pytest.mark.parametrize(
    "duplicate_details",
    (
        pytest.param({}, id="same-user"),
        pytest.param(
            {"name": "Another user", "password": "another-password"},
            id="same-email-different-details",
        ),
    ),
)
def test_duplicate_user_returns_409(
    client, seeded_connection, registration_data, duplicate_details
):
    first_response = client.post("/api/auth/register", json=registration_data)

    assert first_response.status_code == 201
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT id, name, email, hashed_password FROM users ORDER BY id")
        original_users = cursor.fetchall()

    response = client.post(
        "/api/auth/register", json={**registration_data, **duplicate_details}
    )

    assert response.status_code == 409
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT id, name, email, hashed_password FROM users ORDER BY id")
        assert cursor.fetchall() == original_users


@pytest.mark.parametrize(
    "missing_fields",
    (
        pytest.param(("name",), id="missing-name"),
        pytest.param(("email",), id="missing-email"),
        pytest.param(("password",), id="missing-password"),
        pytest.param(("name", "email", "password"), id="missing-all-fields"),
    ),
)
def test_missing_fields_return_422(
    client, seeded_connection, registration_data, missing_fields
):
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users")
        original_count = cursor.fetchone()[0]

    response = client.post(
        "/api/auth/register",
        json={
            field: value
            for field, value in registration_data.items()
            if field not in missing_fields
        },
    )

    assert response.status_code == 422
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users")
        assert cursor.fetchone()[0] == original_count
