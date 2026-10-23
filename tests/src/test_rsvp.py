"""RSVP contract: authenticated creation, missing events, and duplicates."""

from datetime import datetime

import pytest

from src.auth.auth import create_access_token


@pytest.fixture(autouse=True)
def jwt_signing_key(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "rsvp-tests-only-signing-key-at-least-32-bytes")


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {create_access_token(2)}"}


def test_rsvp_returns_201_and_created_rsvp(client, seeded_connection, auth_headers):
    # User 2 has not RSVPed to event 9 in the seed data.
    response = client.post("/api/events/9/rsvp", headers=auth_headers)

    assert response.status_code == 201
    created_rsvp = response.json()
    assert set(created_rsvp) == {"id", "attendee_id", "event_id", "created_at"}

    with seeded_connection.cursor() as cursor:
        cursor.execute(
            "SELECT attendee_id, event_id, created_at FROM rsvps WHERE id = %s",
            (created_rsvp["id"],),
        )
        stored_rsvp = cursor.fetchone()

    assert stored_rsvp is not None
    assert created_rsvp["attendee_id"] == stored_rsvp[0] == 2
    assert created_rsvp["event_id"] == stored_rsvp[1] == 9
    assert datetime.fromisoformat(created_rsvp["created_at"]) == stored_rsvp[2]


@pytest.mark.parametrize(
    "headers",
    (
        pytest.param({}, id="missing-token"),
        pytest.param({"Authorization": "Bearer invalid-token"}, id="invalid-token"),
    ),
)
def test_rsvp_without_valid_token_returns_401(client, seeded_connection, headers):
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT * FROM rsvps ORDER BY id")
        original_rsvps = cursor.fetchall()

    response = client.post("/api/events/9/rsvp", headers=headers)

    assert response.status_code == 401
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT * FROM rsvps ORDER BY id")
        assert cursor.fetchall() == original_rsvps


def test_rsvp_for_nonexistent_event_returns_404(client, seeded_connection, auth_headers):
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM events")
        missing_event_id = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM rsvps ORDER BY id")
        original_rsvps = cursor.fetchall()

    response = client.post(
        f"/api/events/{missing_event_id}/rsvp", headers=auth_headers
    )

    assert response.status_code == 404
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT * FROM rsvps ORDER BY id")
        assert cursor.fetchall() == original_rsvps


def test_duplicate_rsvp_returns_409(client, seeded_connection, auth_headers):
    with seeded_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO rsvps (attendee_id, event_id) VALUES (%s, %s)", (2, 9)
        )
        cursor.execute("SELECT * FROM rsvps ORDER BY id")
        original_rsvps = cursor.fetchall()

    response = client.post("/api/events/9/rsvp", headers=auth_headers)

    assert response.status_code == 409
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT * FROM rsvps ORDER BY id")
        assert cursor.fetchall() == original_rsvps
