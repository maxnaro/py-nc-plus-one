from fastapi import APIRouter

from nc_plus_one.events import service

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def list_events():
    return service.list_events()


@router.get("/{id}")
def get_event_by_id(id: int):
    return service.get_event_by_id(id)
