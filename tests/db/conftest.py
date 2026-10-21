import os
from contextlib import closing
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import sql

from db.seed import seed


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
