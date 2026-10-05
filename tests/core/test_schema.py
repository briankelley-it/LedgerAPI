import pytest


@pytest.mark.django_db
def test_openapi_schema_is_public(api_client):
    response = api_client.get("/api/schema/")

    assert response.status_code == 200


def test_root_redirects_to_docs(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response["Location"] == "/api/docs/"


@pytest.mark.django_db
def test_swagger_ui_is_public(api_client):
    response = api_client.get("/api/docs/")

    assert response.status_code == 200
