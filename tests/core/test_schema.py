import pytest


@pytest.mark.django_db
def test_openapi_schema_is_public(api_client):
    response = api_client.get("/api/schema/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_swagger_ui_is_public(api_client):
    response = api_client.get("/api/docs/")

    assert response.status_code == 200
