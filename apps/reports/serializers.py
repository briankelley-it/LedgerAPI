from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

MONEY = {"max_digits": 14, "decimal_places": 2}


class SummaryQuerySerializer(serializers.Serializer):
    """Validates the query string of GET /reports/summary/."""

    start = serializers.DateField(required=False, help_text="First day to include (YYYY-MM-DD).")
    end = serializers.DateField(required=False, help_text="Last day to include (YYYY-MM-DD).")
    currency = serializers.RegexField(
        r"^[A-Za-z]{3}$",
        required=False,
        default="USD",
        help_text="Only expenses in this currency are added up. Defaults to USD.",
        error_messages={"invalid": "Use a 3-letter currency code like USD."},
    )

    def validate_currency(self, value):
        return value.upper()

    def validate(self, attrs):
        start, end = attrs.get("start"), attrs.get("end")
        if start and end and start > end:
            raise serializers.ValidationError({"end": ["End date must be on or after start."]})
        return attrs


class CategoryTotalSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(allow_null=True)
    category_name = serializers.CharField(allow_null=True)
    total = serializers.DecimalField(**MONEY)
    count = serializers.IntegerField()


class MonthTotalSerializer(serializers.Serializer):
    month = serializers.CharField(help_text="YYYY-MM")
    total = serializers.DecimalField(**MONEY)
    count = serializers.IntegerField()


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Summary",
            value={
                "start": "2026-01-01",
                "end": "2026-02-28",
                "currency": "USD",
                "total": "1342.50",
                "count": 14,
                "by_category": [
                    {"category_id": 2, "category_name": "Rent", "total": "1000.00", "count": 2},
                    {
                        "category_id": 1,
                        "category_name": "Groceries",
                        "total": "312.50",
                        "count": 10,
                    },
                    {"category_id": None, "category_name": None, "total": "30.00", "count": 2},
                ],
                "by_month": [
                    {"month": "2026-01", "total": "690.00", "count": 7},
                    {"month": "2026-02", "total": "652.50", "count": 7},
                ],
            },
        )
    ]
)
class SummarySerializer(serializers.Serializer):
    start = serializers.DateField(allow_null=True)
    end = serializers.DateField(allow_null=True)
    currency = serializers.CharField()
    total = serializers.DecimalField(**MONEY)
    count = serializers.IntegerField()
    by_category = CategoryTotalSerializer(many=True)
    by_month = MonthTotalSerializer(many=True)
