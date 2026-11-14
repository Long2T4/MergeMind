"""Test helper: act as a signed-in user in a test app built without the
Stage 12 middleware. Authentication and cross-user isolation themselves are
tested in test_stage12_authorization.py."""
from app.stage12.security import CurrentUser, get_current_user


def act_as(app, user_id: int, name: str = "Test user", email: str = "test@example.com") -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=user_id, name=name, email=email)
