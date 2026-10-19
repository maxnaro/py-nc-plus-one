"""Integration tests using a temporary schema in TEST_DATABASE_URL."""

import json
import os
import shutil
from datetime import datetime
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from db.seed import DATA_DIR, seed


@pytest.fixture
def seeded_connection():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL")

    with psycopg.connect(database_url, autocommit=True) as connection:
        schema = sql.Identifier(f"seed_test_{uuid4().hex}")
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
        try:
            # Exclude public so the seed can only replace tables in this test schema.
            connection.execute(sql.SQL("SET search_path TO {}").format(schema))
            seed(connection)
            yield connection
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))


def assert_seed_data(connection, table):
    expected = json.loads(
        (DATA_DIR / f"{table}.json").read_text(encoding="utf-8")
    )
    columns = list(expected[0])
    rows = connection.execute(
        sql.SQL("SELECT id, {} FROM {} ORDER BY id").format(
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.Identifier(table),
        )
    ).fetchall()
    assert len(rows) == len(expected)
    for index, (row, fixture) in enumerate(zip(rows, expected), 1):
        assert row[0] == index
        values = tuple(
            datetime.fromisoformat(fixture[column])
            if column in ("starts_at", "ends_at")
            else fixture[column]
            for column in columns
        )
        assert row[1:] == values
    if table != "venues":
        timestamps = connection.execute(
            sql.SQL("SELECT created_at FROM {}").format(sql.Identifier(table))
        ).fetchall()
        assert all(isinstance(row[0], datetime) for row in timestamps)


@pytest.mark.parametrize("table", ("users", "venues", "events", "rsvps"))
def test_loads_json_data_and_generated_values(seeded_connection, table):
    assert_seed_data(seeded_connection, table)


def test_reseeding_replaces_data_and_resets_ids(seeded_connection):
    seeded_connection.execute("UPDATE users SET name = 'Changed'")
    seed(seeded_connection)
    for table in ("users", "venues", "events", "rsvps"):
        assert_seed_data(seeded_connection, table)
    new_id = seeded_connection.execute(
        """INSERT INTO users (name, email, password)
           VALUES (%s, %s, %s) RETURNING id""",
        ("New user", "new@example.com", "example"),
    ).fetchone()[0]
    assert new_id == 7


@pytest.mark.parametrize(
    ("error", "query", "parameters"),
    (
        pytest.param(
            psycopg.errors.NotNullViolation,
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            ("missing-name@example.com", "example"),
            id="required-name",
        ),
        pytest.param(
            psycopg.errors.UniqueViolation,
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            ("Duplicate", "alice@example.com", "example"),
            id="unique-email",
        ),
        pytest.param(
            psycopg.errors.ForeignKeyViolation,
            "UPDATE events SET organiser_id = %s WHERE id = 1",
            (9999,),
            id="event-organiser",
        ),
        pytest.param(
            psycopg.errors.ForeignKeyViolation,
            "UPDATE events SET venue_id = %s WHERE id = 1",
            (9999,),
            id="event-venue",
        ),
        pytest.param(
            psycopg.errors.ForeignKeyViolation,
            "INSERT INTO rsvps (attendee_id, event_id) VALUES (%s, %s)",
            (9999, 1),
            id="rsvp-attendee",
        ),
        pytest.param(
            psycopg.errors.ForeignKeyViolation,
            "INSERT INTO rsvps (attendee_id, event_id) VALUES (%s, %s)",
            (1, 9999),
            id="rsvp-event",
        ),
    ),
)
def test_enforces_required_fields_uniqueness_and_foreign_keys(
    seeded_connection, error, query, parameters
):
    with pytest.raises(error):
        seeded_connection.execute(query, parameters)


def test_failed_seed_restores_existing_tables_and_data(seeded_connection, tmp_path):
    seeded_connection.execute(
        """INSERT INTO users (name, email, password)
           VALUES (%s, %s, %s)""",
        ("Keep me", "keep@example.com", "example"),
    )
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    events_file = data_dir / "events.json"
    events = json.loads(events_file.read_text(encoding="utf-8"))
    events[0]["venue_id"] = 9999
    events_file.write_text(json.dumps(events), encoding="utf-8")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        seed(seeded_connection, data_dir)

    assert seeded_connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 7
    assert seeded_connection.execute(
        "SELECT name FROM users WHERE email = %s", ("keep@example.com",)
    ).fetchone() == ("Keep me",)
    assert seeded_connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 10
