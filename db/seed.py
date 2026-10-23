"""Create the NC Plus One tables and load their JSON seed data."""

import json
import os
from contextlib import closing
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as Connection

DB_DIR = Path(__file__).resolve().parent
DATA_DIR = DB_DIR / "data"

INSERT_QUERIES = {
    "users": """
        INSERT INTO users (name, email, hashed_password)
        VALUES (%(name)s, %(email)s, %(hashed_password)s)
    """,
    "venues": """
        INSERT INTO venues (name, address, capacity)
        VALUES (%(name)s, %(address)s, %(capacity)s)
    """,
    "events": """
        INSERT INTO events (
            title, description, starts_at, ends_at, organiser_id, venue_id
        )
        VALUES (
            %(title)s, %(description)s, %(starts_at)s, %(ends_at)s,
            %(organiser_id)s, %(venue_id)s
        )
    """,
    "rsvps": """
        INSERT INTO rsvps (attendee_id, event_id)
        VALUES (%(attendee_id)s, %(event_id)s)
    """,
}


def seed(connection: Connection, data_dir: str | Path = DATA_DIR) -> None:
    data_dir = Path(data_dir)
    data = {
        table: json.loads((data_dir / f"{table}.json").read_text(encoding="utf-8"))
        for table in INSERT_QUERIES
    }
    schema = (DB_DIR / "schema.sql").read_text(encoding="utf-8")

    with connection, connection.cursor() as cursor:
        cursor.execute(schema)
        for table, query in INSERT_QUERIES.items():
            cursor.executemany(query, data[table])


if __name__ == "__main__":
    with closing(
        psycopg2.connect(os.environ.get("DATABASE_URL", "dbname=nc_plus_one"))
    ) as connection:
        seed(connection)
    print("Database seeded successfully.")
