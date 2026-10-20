import os

import dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

dotenv.load_dotenv()
DSN = "DSN"


def _get_connection():
    return psycopg2.connect(os.environ.get(DSN))


def query(sql: str, *args, fetch_one: bool = False):
    connection = _get_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, args)
            result = (
                None
                if cursor.description is None
                else (cursor.fetchone() if fetch_one else cursor.fetchall())
            )
            connection.commit()
            return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
