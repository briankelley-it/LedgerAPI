"""Shared OpenAPI response definitions so every endpoint documents errors the same way."""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse

from apps.core.serializers import ErrorSerializer


def _error(description, code, message, details=None):
    return OpenApiResponse(
        response=ErrorSerializer,
        description=description,
        examples=[
            OpenApiExample(
                code,
                value={"error": {"code": code, "message": message, "details": details}},
            )
        ],
    )


VALIDATION_ERROR = _error(
    "Validation error",
    "validation_error",
    "Invalid input.",
    {"field_name": ["This field is required."]},
)
UNAUTHORIZED = _error(
    "Missing or invalid token",
    "not_authenticated",
    "Authentication credentials were not provided.",
)
NOT_FOUND = _error(
    "Not found (or it belongs to another user)",
    "not_found",
    "No Expense matches the given query.",
)
