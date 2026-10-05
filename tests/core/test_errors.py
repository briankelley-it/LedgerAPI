"""The error format must be the same no matter where the error comes from."""

import pytest
from rest_framework import serializers
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.core.exceptions import api_exception_handler, not_found, server_error


def test_not_found_handler_returns_json():
    response = not_found(request=None)

    assert response.status_code == 404
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
def test_unknown_route_uses_error_format(client, settings):
    settings.DEBUG = False
    response = client.get("/api/v1/does-not-exist/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_server_error_uses_error_format():
    response = server_error(request=None)

    assert response.status_code == 500
    assert b'"server_error"' in response.content


def test_field_validation_error_keeps_field_details():
    exc = ValidationError({"amount": ["Must be positive."]})

    response = api_exception_handler(exc, context={})

    assert response.status_code == 400
    assert response.data == {
        "error": {
            "code": "validation_error",
            "message": "Invalid input.",
            "details": {"amount": ["Must be positive."]},
        }
    }


def test_non_field_validation_error_is_wrapped():
    exc = serializers.ValidationError("Something is wrong.")

    response = api_exception_handler(exc, context={})

    assert response.data["error"]["details"] == {"non_field_errors": ["Something is wrong."]}


def test_other_api_errors_carry_their_code():
    response = api_exception_handler(NotFound(), context={})

    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"
    assert response.data["error"]["details"] is None


def test_unexpected_exceptions_are_left_to_django():
    assert api_exception_handler(RuntimeError("boom"), context={}) is None


def test_errors_without_a_detail_key_are_still_wrapped():
    response = api_exception_handler(APIException(["first", "second"]), context={})

    assert response.status_code == 500
    assert response.data["error"]["code"] == "error"
