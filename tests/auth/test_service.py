"""Authentication rules can be checked without HTTP or a database."""

from unittest.mock import Mock

import pytest

from nc_plus_one.auth import service
from nc_plus_one.errors import ConflictError, UnauthorizedError


@pytest.mark.parametrize(
    "user",
    (None, {"id": 1, "hashed_password": "stored-hash"}),
    ids=("unknown-user", "wrong-password"),
)
def test_invalid_login_has_the_same_failure(monkeypatch, user):
    monkeypatch.setattr(service.repository, "get_login_user", Mock(return_value=user))
    monkeypatch.setattr(service, "verify_password", Mock(return_value=False))
    issue_token = Mock()
    monkeypatch.setattr(service, "create_access_token", issue_token)

    with pytest.raises(UnauthorizedError, match=r"^Invalid login credentials\.$"):
        service.login(email="user@example.com", password="incorrect-password")

    issue_token.assert_not_called()


def test_duplicate_email_is_rejected_before_creating_user(monkeypatch):
    monkeypatch.setattr(
        service.repository, "get_user_by_email", Mock(return_value={"id": 1})
    )
    create_user = Mock()
    monkeypatch.setattr(service.repository, "create_user", create_user)

    with pytest.raises(ConflictError, match=r"^Email already registered\.$"):
        service.register(name="User", email="user@example.com", password="password")

    create_user.assert_not_called()
