import os

import pytest
from fastapi.testclient import TestClient
from psycopg2.extensions import make_dsn
from psycopg2.extras import RealDictCursor

from src.main import app
from tests.db.fixtures import seeded_connection

_ = seeded_connection  # HACK: suppresses unused import warning


@pytest.fixture
def event_data(seeded_connection):
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
