"""Connection tests using a temporary schema in TEST_DATABASE_URL."""

import os
from contextlib import closing
from unittest.mock import Mock

import pytest
from psycopg2 import OperationalError, errors
from psycopg2.extensions import make_dsn

from db.connection import get_connection, query


@pytest.fixture
def query_connection(seeded_connection, monkeypatch):
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT current_schema()")
        schema = cursor.fetchone()[0]
    dsn = make_dsn(os.environ["TEST_DATABASE_URL"], options=f"-c search_path={schema}")
    monkeypatch.setenv("DSN", dsn)

    # Use a separate transaction so the seed connection can observe committed data.
    with closing(get_connection()) as connection:
        monkeypatch.setattr("db.connection._get_connection", lambda: connection)
        yield connection


@pytest.mark.parametrize(
    "dsn",
    (
        "dbname=nc_plus_one_test",
        "postgresql://test_user:test_password@localhost/nc_plus_one_test",
        None,
    ),
)
def test_get_connection_uses_dsn_environment_variable(monkeypatch, dsn):
    if dsn is None:
        monkeypatch.delenv("DSN", raising=False)
    else:
        monkeypatch.setenv("DSN", dsn)
    connect = Mock()
    monkeypatch.setattr("db.connection.psycopg2.connect", connect)

    assert get_connection() is connect.return_value
    connect.assert_called_once_with(dsn)


def test_query_returns_all_rows_as_dictionaries(query_connection):
    result = query("SELECT id, name FROM users WHERE id <= %s ORDER BY id", 2)

    assert result == [
        {"id": 1, "name": "Alice Rahman"},
        {"id": 2, "name": "Bob Nguyen"},
    ]
    assert query_connection.closed


def test_query_fetch_one_returns_first_row_as_dictionary(query_connection):
    result = query("SELECT id, name FROM users ORDER BY id", fetch_one=True)

    assert result == {"id": 1, "name": "Alice Rahman"}
    assert query_connection.closed


@pytest.mark.parametrize(("fetch_one", "expected"), ((False, []), (True, None)))
def test_query_with_no_matching_rows(query_connection, fetch_one, expected):
    result = query("SELECT id FROM users WHERE id = %s", 9999, fetch_one=fetch_one)

    assert result == expected
    assert query_connection.closed


@pytest.mark.parametrize("value", ("O'Reilly", "'); DROP TABLE users; --", None))
def test_query_binds_multiple_parameters_as_values(query_connection, value):
    result = query("SELECT %s::text AS value, %s::integer AS number", value, 42)

    assert result == [{"value": value, "number": 42}]
    assert query_connection.closed


@pytest.mark.parametrize("fetch_one", (False, True))
def test_query_without_returning_commits_and_returns_none(
    seeded_connection, query_connection, fetch_one
):
    result = query(
        "UPDATE users SET name = %s WHERE id = %s", "Changed", 1, fetch_one=fetch_one
    )

    assert result is None
    assert query_connection.closed
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT name FROM users WHERE id = 1")
        assert cursor.fetchone() == ("Changed",)


@pytest.mark.parametrize("fetch_one", (False, True))
def test_query_with_returning_commits_and_returns_inserted_row(
    seeded_connection, query_connection, fetch_one
):
    result = query(
        """INSERT INTO users (name, email, password)
           VALUES (%s, %s, %s) RETURNING id, name""",
        "New user",
        "new@example.com",
        "example",
        fetch_one=fetch_one,
    )

    expected = {"id": 7, "name": "New user"}
    assert result == (expected if fetch_one else [expected])
    assert query_connection.closed
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT name FROM users WHERE email = %s", ("new@example.com",))
        assert cursor.fetchone() == ("New user",)


@pytest.mark.parametrize(
    ("error", "statement", "parameters"),
    (
        pytest.param(
            errors.SyntaxError,
            "UPDATE users SET name = %s WHERE id = 1; SELECT FROM",
            ("Changed",),
            id="invalid-sql",
        ),
        pytest.param(
            errors.NotNullViolation,
            """UPDATE users SET name = %s WHERE id = 1;
               INSERT INTO users (email, password) VALUES (%s, %s)""",
            ("Changed", "missing-name@example.com", "example"),
            id="required-name",
        ),
        pytest.param(
            errors.UniqueViolation,
            """UPDATE users SET name = %s WHERE id = 1;
               INSERT INTO users (name, email, password) VALUES (%s, %s, %s)""",
            ("Changed", "Duplicate", "alice@example.com", "example"),
            id="unique-email",
        ),
    ),
)
def test_failed_query_rolls_back_changes_and_closes_connection(
    seeded_connection, query_connection, error, statement, parameters
):
    with pytest.raises(error):
        query(statement, *parameters)

    assert query_connection.closed
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT name FROM users WHERE id = 1")
        assert cursor.fetchone() == ("Alice Rahman",)
        cursor.execute("SELECT COUNT(*) FROM users")
        assert cursor.fetchone()[0] == 6


def test_query_propagates_connection_errors(monkeypatch):
    error = OperationalError("Database unavailable")
    monkeypatch.setattr("db.connection._get_connection", Mock(side_effect=error))

    with pytest.raises(OperationalError) as raised:
        query("SELECT 1")

    assert raised.value is error
