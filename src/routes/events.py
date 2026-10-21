from fastapi import APIRouter, HTTPException

from db.connection import query

EVENTS = "events"

router = APIRouter(prefix=f"/{EVENTS}", tags=[EVENTS])


@router.get("")
def list_events():
    query_str = """
        SELECT * FROM events
        ORDER BY starts_at DESC;
    """
    events = query(query_str)
    return events


@router.get("/{id}")
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
