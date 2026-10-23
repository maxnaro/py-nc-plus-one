"""RSVP existence checks and creation/deletion rules."""

from nc_plus_one.errors import ConflictError, NotFoundError
from nc_plus_one.events import repository as events_repository
from nc_plus_one.rsvps import repository


def create_rsvp(event_id: int, attendee_id: str):
    if not events_repository.get_event_id(event_id):
        raise NotFoundError(f"No event found for ID: {event_id}.")

    if repository.get_rsvp(event_id, attendee_id):
        raise ConflictError(
            f"Existing RSVP found for event ID: {event_id}, attendee: {attendee_id}."
        )

    return repository.create_rsvp(event_id, attendee_id)


def delete_rsvp(event_id: int, attendee_id: str):
    if repository.delete_rsvp(event_id, attendee_id) is None:
        raise NotFoundError(
            f"No RSVP found for event: {event_id}, user: {attendee_id}"
        )
