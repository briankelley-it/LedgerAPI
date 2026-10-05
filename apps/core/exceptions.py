"""
One error format for the whole API.

Every error response has this shape:

    {
        "error": {
            "code": "validation_error",
            "message": "Invalid input.",
            "details": {"amount": ["Ensure this value is greater than 0."]}
        }
    }

"details" is only filled in for validation errors, where it holds the
field-by-field messages. For everything else it is null.
"""

from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def error_payload(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details}}


def api_exception_handler(exc, context):
    """Wrap DRF's default handler so every error uses the format above."""
    response = exception_handler(exc, context)
    if response is None:
        # Not an API exception (a real bug). Django turns it into a 500,
        # which server_error() below renders in the same format.
        return None

    if isinstance(exc, ValidationError):
        detail = response.data
        # A ValidationError raised with a plain message (not tied to a field)
        # arrives as a list. Put it under "non_field_errors" for consistency.
        if isinstance(detail, list):
            detail = {"non_field_errors": detail}
        response.data = error_payload("validation_error", "Invalid input.", detail)
        return response

    data = response.data
    if isinstance(data, dict) and "detail" in data:
        detail = data["detail"]
        code = getattr(detail, "code", None) or getattr(exc, "default_code", "error")
        message = str(detail)
    else:
        code = getattr(exc, "default_code", "error")
        message = str(data)
    response.data = error_payload(code, message)
    return response


def not_found(request, exception=None):
    """JSON 404 for URLs that do not match any route."""
    return JsonResponse(
        error_payload("not_found", "The requested resource was not found."),
        status=status.HTTP_404_NOT_FOUND,
    )


def server_error(request):
    """JSON 500 so even unexpected crashes follow the error format."""
    return JsonResponse(
        error_payload("server_error", "An unexpected error occurred."),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
