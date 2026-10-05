from django.db import DatabaseError, connection
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import error_payload
from apps.core.serializers import ErrorSerializer, HealthSerializer


class HealthView(APIView):
    """Liveness check for load balancers and Docker. Needs no token."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["health"],
        summary="Health check",
        responses={
            200: OpenApiResponse(
                HealthSerializer,
                examples=[OpenApiExample("ok", value={"status": "ok", "database": "ok"})],
            ),
            503: OpenApiResponse(ErrorSerializer, description="Database unreachable"),
        },
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            return Response(
                error_payload("service_unavailable", "Database is unreachable."),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})
