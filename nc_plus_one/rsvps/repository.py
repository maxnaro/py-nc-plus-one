"""RSVP queries; each uses the shared query helper's transaction boundary."""

from nc_plus_one.db.connection import query


def get_rsvp(event_id: int, attendee_id: str):
    return query(
        "SELECT id FROM rsvps WHERE attendee_id = %s AND event_id = %s",
        attendee_id,
        event_id,
        fetch_one=True,
    )


def create_rsvp(event_id: int, attendee_id: str):
    return query(
        """
        INSERT INTO rsvps (attendee_id, event_id)
        VALUES (%s, %s)
        RETURNING id, attendee_id, event_id, created_at;
        """,
        attendee_id,
        event_id,
        fetch_one=True,
    )


def delete_rsvp(event_id: int, attendee_id: str):
    return query(
        """
        DELETE FROM rsvps WHERE event_id = %s AND attendee_id = %s
        RETURNING id;
        """,
        event_id,
        attendee_id,
        fetch_one=True,
    )
