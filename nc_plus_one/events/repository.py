"""Event queries shared by browsing and RSVP services."""

from nc_plus_one.db.connection import query


def list_events():
    return query(
        """
        SELECT * FROM events
        ORDER BY starts_at DESC;
        """
    )


def get_event_by_id(event_id: int):
    return query(
        """
        SELECT * FROM events
        WHERE id = %s;
        """,
        event_id,
        fetch_one=True,
    )


def get_event_id(event_id: int):
    return query("SELECT id FROM events WHERE id = %s", event_id, fetch_one=True)
