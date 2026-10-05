from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.openapi import UNAUTHORIZED, VALIDATION_ERROR
from apps.reports.serializers import SummaryQuerySerializer, SummarySerializer
from apps.reports.services import build_summary


class SummaryView(APIView):
    @extend_schema(
        tags=["reports"],
        summary="Spending summary",
        description=(
            "Total spent, totals by category and totals by month for the current "
            "user. Dates are inclusive and both are optional. Only one currency "
            "is summed at a time, because adding different currencies together "
            "would give a meaningless number."
        ),
        parameters=[SummaryQuerySerializer],
        responses={200: SummarySerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED},
    )
    def get(self, request):
        query = SummaryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        summary = build_summary(request.user, **query.validated_data)
        return Response(SummarySerializer(summary).data)
