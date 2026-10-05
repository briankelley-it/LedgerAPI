from unittest import mock

import pytest
from django.db import DatabaseError
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_ok_without_auth(api_client):
    response = api_client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_database_down(api_client):
    with mock.patch("apps.core.views.connection.cursor", side_effect=DatabaseError):
        response = api_client.get(reverse("health"))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
