"""Integration tests using a temporary schema in TEST_DATABASE_URL."""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from psycopg2 import errors, sql
from psycopg2.extensions import make_dsn

from nc_plus_one.db.seed import DATA_DIR, seed


def assert_seed_data(connection, table):
    expected = json.loads((DATA_DIR / f"{table}.json").read_text(encoding="utf-8"))
    columns = list(expected[0])
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT id, {} FROM {} ORDER BY id").format(
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.Identifier(table),
            )
        )
        rows = cursor.fetchall()
    assert len(rows) == len(expected)
    for index, (row, fixture) in enumerate(zip(rows, expected), 1):
        assert row[0] == index
        values = tuple(
            (
                datetime.fromisoformat(fixture[column])
                if column in ("starts_at", "ends_at")
                else fixture[column]
            )
            for column in columns
        )
        assert row[1:] == values
    if table != "venues":
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT created_at FROM {}").format(sql.Identifier(table))
            )
            timestamps = cursor.fetchall()
        assert all(isinstance(row[0], datetime) for row in timestamps)


@pytest.mark.parametrize("table", ("users", "venues", "events", "rsvps"))
def test_loads_json_data_and_generated_values(seeded_connection, table):
    assert_seed_data(seeded_connection, table)


def test_reseeding_replaces_data_and_resets_ids(seeded_connection):
    with seeded_connection.cursor() as cursor:
        cursor.execute("UPDATE users SET name = 'Changed'")
    seed(seeded_connection)
    for table in ("users", "venues", "events", "rsvps"):
        assert_seed_data(seeded_connection, table)
    with seeded_connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO users (name, email, hashed_password)
               VALUES (%s, %s, %s) RETURNING id""",
            ("New user", "new@example.com", "example"),
        )
        new_id = cursor.fetchone()[0]
    assert new_id == 7


def test_seed_finds_assets_outside_project_directory(
    seeded_connection, monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)

    seed(seeded_connection)

    for table in ("users", "venues", "events", "rsvps"):
        assert_seed_data(seeded_connection, table)


def test_seed_module_command(seeded_connection):
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT current_schema()")
        schema = cursor.fetchone()[0]
    dsn = make_dsn(os.environ["TEST_DATABASE_URL"], options=f"-c search_path={schema}")

    result = subprocess.run(
        [sys.executable, "-m", "nc_plus_one.db.seed"],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "DATABASE_URL": dsn},
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "Database seeded successfully."
    for table in ("users", "venues", "events", "rsvps"):
        assert_seed_data(seeded_connection, table)


@pytest.mark.parametrize(
    ("error", "query", "parameters"),
    (
        pytest.param(
            errors.NotNullViolation,
            "INSERT INTO users (email, hashed_password) VALUES (%s, %s)",
            ("missing-name@example.com", "example"),
            id="required-name",
        ),
        pytest.param(
            errors.UniqueViolation,
            "INSERT INTO users (name, email, hashed_password) VALUES (%s, %s, %s)",
            ("Duplicate", "alice@example.com", "example"),
            id="unique-email",
        ),
        pytest.param(
            errors.ForeignKeyViolation,
            "UPDATE events SET organiser_id = %s WHERE id = 1",
            (9999,),
            id="event-organiser",
        ),
        pytest.param(
            errors.ForeignKeyViolation,
            "UPDATE events SET venue_id = %s WHERE id = 1",
            (9999,),
            id="event-venue",
        ),
        pytest.param(
            errors.ForeignKeyViolation,
            "INSERT INTO rsvps (attendee_id, event_id) VALUES (%s, %s)",
            (9999, 1),
            id="rsvp-attendee",
        ),
        pytest.param(
            errors.ForeignKeyViolation,
            "INSERT INTO rsvps (attendee_id, event_id) VALUES (%s, %s)",
            (1, 9999),
            id="rsvp-event",
        ),
    ),
)
def test_enforces_required_fields_uniqueness_and_foreign_keys(
    seeded_connection, error, query, parameters
):
    with pytest.raises(error), seeded_connection.cursor() as cursor:
        cursor.execute(query, parameters)


def test_failed_seed_restores_existing_tables_and_data(seeded_connection, tmp_path):
    with seeded_connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO users (name, email, hashed_password)
               VALUES (%s, %s, %s)""",
            ("Keep me", "keep@example.com", "example"),
        )
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    events_file = data_dir / "events.json"
    events = json.loads(events_file.read_text(encoding="utf-8"))
    events[0]["venue_id"] = 9999
    events_file.write_text(json.dumps(events), encoding="utf-8")
    with pytest.raises(errors.ForeignKeyViolation):
        seed(seeded_connection, data_dir)

    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users")
        assert cursor.fetchone()[0] == 7
        cursor.execute("SELECT name FROM users WHERE email = %s", ("keep@example.com",))
        assert cursor.fetchone() == ("Keep me",)
        cursor.execute("SELECT COUNT(*) FROM events")
        assert cursor.fetchone()[0] == 10
