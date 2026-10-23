from unittest.mock import Mock

import pytest

from nc_plus_one.errors import NotFoundError
from nc_plus_one.events import service


def test_missing_event_has_a_business_error(monkeypatch):
    monkeypatch.setattr(service.repository, "get_event_by_id", Mock(return_value=None))

    with pytest.raises(NotFoundError, match="^Event not found for id: 99$"):
        service.get_event_by_id(99)
