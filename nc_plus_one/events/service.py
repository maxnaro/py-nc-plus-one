"""Event browsing and missing-event rules."""

from nc_plus_one.errors import NotFoundError
from nc_plus_one.events import repository


def list_events():
    return repository.list_events()


def get_event_by_id(event_id: int):
    event = repository.get_event_by_id(event_id)
    if event is None:
        raise NotFoundError(f"Event not found for id: {event_id}")

    return event
