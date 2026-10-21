from datetime import datetime


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
