from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse

from tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

User = get_user_model()

REGISTER = reverse("auth-register")
TOKEN = reverse("auth-token")
REFRESH = reverse("auth-token-refresh")
ME = reverse("auth-me")


def get_tokens(client, email, password=DEFAULT_PASSWORD):
    response = client.post(TOKEN, {"email": email, "password": password})
    assert response.status_code == 200, response.json()
    return response.json()


class TestRegister:
    def test_creates_user_and_hides_password(self, api_client):
        response = api_client.post(
            REGISTER, {"email": "Jane@Example.com", "password": DEFAULT_PASSWORD}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "jane@example.com"
        assert set(body) == {"id", "email", "date_joined"}

        user = User.objects.get(pk=body["id"])
        assert user.username == "jane@example.com"
        assert user.check_password(DEFAULT_PASSWORD)

    def test_rejects_duplicate_email_ignoring_case(self, api_client):
        UserFactory(email="jane@example.com")

        response = api_client.post(
            REGISTER, {"email": "JANE@example.com", "password": DEFAULT_PASSWORD}
        )

        assert response.status_code == 400
        assert "email" in response.json()["error"]["details"]

    @pytest.mark.parametrize("password", ["short", "password123", "12345678901"])
    def test_rejects_weak_password(self, api_client, password):
        response = api_client.post(REGISTER, {"email": "jane@example.com", "password": password})

        assert response.status_code == 400
        assert "password" in response.json()["error"]["details"]

    def test_requires_email_and_password(self, api_client):
        response = api_client.post(REGISTER, {})

        assert response.status_code == 400
        assert set(response.json()["error"]["details"]) == {"email", "password"}

    def test_rejects_invalid_email(self, api_client):
        response = api_client.post(
            REGISTER, {"email": "not-an-email", "password": DEFAULT_PASSWORD}
        )

        assert response.status_code == 400
        assert "email" in response.json()["error"]["details"]

    def test_ignores_a_bad_token_header(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer garbage")

        response = api_client.post(
            REGISTER, {"email": "jane@example.com", "password": DEFAULT_PASSWORD}
        )

        assert response.status_code == 201

    def test_race_on_duplicate_email_is_a_validation_error(self, api_client):
        # Simulate two requests where both pass the "email is free" check and
        # the second insert hits the database unique constraint.
        with mock.patch.object(User.objects, "create_user", side_effect=IntegrityError):
            response = api_client.post(
                REGISTER, {"email": "jane@example.com", "password": DEFAULT_PASSWORD}
            )

        assert response.status_code == 400
        assert "email" in response.json()["error"]["details"]


class TestToken:
    def test_returns_access_and_refresh(self, api_client, user):
        tokens = get_tokens(api_client, user.email)

        assert set(tokens) == {"access", "refresh"}

    def test_email_is_case_insensitive(self, api_client):
        UserFactory(email="jane@example.com")

        tokens = get_tokens(api_client, "JANE@Example.com")

        assert "access" in tokens

    def test_wrong_password_is_401(self, api_client, user):
        response = api_client.post(TOKEN, {"email": user.email, "password": "wrong-password"})

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "no_active_account"

    def test_inactive_user_cannot_log_in(self, api_client):
        user = UserFactory(is_active=False)

        response = api_client.post(TOKEN, {"email": user.email, "password": DEFAULT_PASSWORD})

        assert response.status_code == 401

    def test_missing_fields_is_400(self, api_client):
        response = api_client.post(TOKEN, {})

        assert response.status_code == 400
        assert set(response.json()["error"]["details"]) == {"email", "password"}

    def test_refresh_returns_new_access_token(self, api_client, user):
        tokens = get_tokens(api_client, user.email)

        response = api_client.post(REFRESH, {"refresh": tokens["refresh"]})

        assert response.status_code == 200
        assert "access" in response.json()

    def test_invalid_refresh_token_is_401(self, api_client):
        response = api_client.post(REFRESH, {"refresh": "not-a-token"})

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "token_not_valid"


class TestMe:
    def test_requires_authentication(self, api_client):
        response = api_client.get(ME)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "not_authenticated"

    def test_rejects_invalid_token(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")

        response = api_client.get(ME)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "token_not_valid"

    def test_refresh_token_cannot_be_used_as_access_token(self, api_client, user):
        tokens = get_tokens(api_client, user.email)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['refresh']}")

        response = api_client.get(ME)

        assert response.status_code == 401


def test_full_flow_register_login_me(api_client):
    """The happy path a real client follows: register, log in, call the API."""
    api_client.post(REGISTER, {"email": "jane@example.com", "password": DEFAULT_PASSWORD})
    tokens = get_tokens(api_client, "jane@example.com")

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = api_client.get(ME)

    assert response.status_code == 200
    assert response.json()["email"] == "jane@example.com"
