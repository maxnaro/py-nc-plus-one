from fastapi import APIRouter

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
