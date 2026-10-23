import logging
from datetime import datetime

import pytest

LOGGER = logging.getLogger(__name__)


def test_get_api_events(client, events_data):
    response = client.get("/api/events", follow_redirects=False)
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert {event["starts_at"] for event in events_data} <= {
        datetime.fromisoformat(event["starts_at"]) for event in events
    }
    for event in events:
        assert set(event) == {
            "id",
            "title",
            "description",
            "starts_at",
            "ends_at",
            "organiser_id",
            "venue_id",
            "created_at",
        }


@pytest.mark.parametrize(
    ("id", "status_code"),
    (
        pytest.param(1, 200, id="exists"),
        pytest.param(0, 404, id="does-not-exist"),
        pytest.param("this-is-not-an-integer", 422, id="non-int-id"),
    ),
)
def test_get_api_events_by_id(client, events_data, id, status_code):
    response = client.get(f"/api/events/{id}", follow_redirects=False)
    assert response.status_code == status_code

    if status_code == 404:
        assert response.json() == {
            "error": {"code": "NOT_FOUND", "message": "Event not found for id: 0"}
        }

    if status_code == 200:
        event = response.json()
        assert isinstance(event, dict)
        assert set(event) == {
            "id",
            "title",
            "description",
            "starts_at",
            "ends_at",
            "organiser_id",
            "venue_id",
            "created_at",
        }
