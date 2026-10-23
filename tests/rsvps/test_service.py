"""RSVP rules prevent invalid writes before reaching the database."""

from unittest.mock import Mock

import pytest

from nc_plus_one.errors import ConflictError, NotFoundError
from nc_plus_one.rsvps import service


def test_missing_event_prevents_rsvp_creation(monkeypatch):
    monkeypatch.setattr(
        service.events_repository, "get_event_id", Mock(return_value=None)
    )
    find_rsvp = Mock()
    create_rsvp = Mock()
    monkeypatch.setattr(service.repository, "get_rsvp", find_rsvp)
    monkeypatch.setattr(service.repository, "create_rsvp", create_rsvp)

    with pytest.raises(NotFoundError, match=r"^No event found for ID: 99\.$"):
        service.create_rsvp(99, "2")

    find_rsvp.assert_not_called()
    create_rsvp.assert_not_called()


def test_duplicate_rsvp_prevents_another_insert(monkeypatch):
    monkeypatch.setattr(
        service.events_repository, "get_event_id", Mock(return_value={"id": 9})
    )
    monkeypatch.setattr(service.repository, "get_rsvp", Mock(return_value={"id": 1}))
    create_rsvp = Mock()
    monkeypatch.setattr(service.repository, "create_rsvp", create_rsvp)

    with pytest.raises(
        ConflictError,
        match=r"^Existing RSVP found for event ID: 9, attendee: 2\.$",
    ):
        service.create_rsvp(9, "2")

    create_rsvp.assert_not_called()


def test_missing_rsvp_cannot_be_deleted(monkeypatch):
    monkeypatch.setattr(service.repository, "delete_rsvp", Mock(return_value=None))

    with pytest.raises(NotFoundError, match="^No RSVP found for event: 9, user: 2$"):
        service.delete_rsvp(9, "2")
