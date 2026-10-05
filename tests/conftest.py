import pytest
from rest_framework.test import APIClient

from tests.factories import UserFactory


@pytest.fixture
def api_client():
    """A client with no credentials."""
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user):
    """A client logged in as `user`.

    force_authenticate skips the JWT step to keep tests fast and focused.
    The real token flow is covered in tests/accounts.
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_client(other_user):
    """A client logged in as a second, unrelated user."""
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client
