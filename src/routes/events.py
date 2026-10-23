from enum import StrEnum, auto
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from db.connection import query
from src.auth.auth import require_token


class ROUTES(StrEnum):
    EVENTS = auto()
    ID = "{id}"
    RSVP = auto()
    ME = auto()


router = APIRouter(prefix=f"/{ROUTES.EVENTS.value}", tags=[ROUTES.EVENTS.value])


@router.get("")
def list_events():
    query_str = """
        SELECT * FROM events
        ORDER BY starts_at DESC;
    """
    events = query(query_str)
    return events


@router.get("/" + ROUTES.ID.value)
def get_event_by_id(id: int):
    query_str = """
        SELECT * FROM events
        WHERE id = %s;
    """
    event = query(query_str, id, fetch_one=True)

    if event is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Event not found for id: {id}"},
        )

    return event


@router.post("/" + ROUTES.ID.value + "/" + ROUTES.RSVP.value, status_code=201)
def rsvp(
    id: int,
    payload: Annotated[dict, Depends(require_token)],
):
    if not query("SELECT id FROM events WHERE id = %s", id, fetch_one=True):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": f"No event found for ID: {id}.",
            },
        )

    attendee_id = payload["sub"]
    if query(
        "SELECT id FROM rsvps WHERE attendee_id = %s AND event_id = %s",
        attendee_id,
        id,
        fetch_one=True,
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CONFLICT",
                "message": f"Existing RSVP found for event ID: {id}, attendee: {attendee_id}.",
            },
        )

    return query(
        """
        INSERT INTO rsvps (attendee_id, event_id)
        VALUES (%s, %s)
        RETURNING id, attendee_id, event_id, created_at;
    """,
        attendee_id,
        id,
        fetch_one=True,
    )


@router.delete("/{id}/rsvp/me", status_code=204)
def delete_rsvp(id: int, payload: Annotated[dict, Depends(require_token)]):
    attendee_id = payload["sub"]
    result = query(
        """
        DELETE FROM rsvps WHERE event_id = %s AND attendee_id = %s
        RETURNING id;
    """,
        id,
        attendee_id,
        fetch_one=True,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": f"No RSVP found for event: {id}, user: {attendee_id}",
            },
        )
