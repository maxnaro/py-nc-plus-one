import logging
import os
from contextlib import closing
from uuid import uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2 import sql
from psycopg2.extensions import make_dsn
from psycopg2.extras import RealDictCursor

from nc_plus_one.db.seed import seed
from nc_plus_one.main import app

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def seeded_connection():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL")

    with closing(psycopg2.connect(database_url)) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            schema = sql.Identifier(f"seed_test_{uuid4().hex}")
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            try:
                # Exclude public so the seed can only replace tables in this test schema.
                cursor.execute(sql.SQL("SET search_path TO {}").format(schema))
                seed(connection)
                yield connection
            finally:
                cursor.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))


@pytest.fixture
def events_data(seeded_connection):
    """Return the events loaded into this test's temporary schema."""
    with seeded_connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM events ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]


@pytest.fixture
def client(seeded_connection, monkeypatch):
    """Make API database connections use the test's temporary schema."""
    with seeded_connection.cursor() as cursor:
        cursor.execute("SELECT current_schema()")
        schema_name = cursor.fetchone()[0]

    test_dsn = make_dsn(
        os.environ["TEST_DATABASE_URL"],
        options=f"-c search_path={schema_name}",
    )
    monkeypatch.setenv("DSN", test_dsn)

    with TestClient(app) as test_client:
        yield test_client
