from decimal import Decimal

from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.ledger.models import Category, Expense


class OwnedCategoryField(serializers.PrimaryKeyRelatedField):
    """Accepts only ids of categories that belong to the current user.

    Another user's category id gets the same "does not exist" error as an
    id that really does not exist, so nothing leaks.
    """

    def get_queryset(self):
        request = self.context.get("request")
        if request is None:
            return Category.objects.none()
        return Category.objects.filter(owner=request.user)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Create category",
            value={"name": "Groceries", "color": "#4CAF50"},
            request_only=True,
        ),
        OpenApiExample(
            "Category",
            value={
                "id": 1,
                "name": "Groceries",
                "color": "#4CAF50",
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "color", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        owner = self.context["request"].user
        duplicates = Category.objects.filter(owner=owner, name__iexact=value)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("You already have a category with this name.")
        return value

    def validate_color(self, value):
        return value.upper()


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Create expense",
            value={
                "amount": "42.50",
                "currency": "USD",
                "description": "Weekly groceries",
                "date": "2026-10-04",
                "category": 1,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Expense",
            value={
                "id": 7,
                "amount": "42.50",
                "currency": "USD",
                "description": "Weekly groceries",
                "date": "2026-10-04",
                "category": 1,
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class ExpenseSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    category = OwnedCategoryField(allow_null=True, required=False)
    currency = serializers.RegexField(
        r"^[A-Za-z]{3}$",
        required=False,
        error_messages={"invalid": "Use a 3-letter currency code like USD."},
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "amount",
            "currency",
            "description",
            "date",
            "category",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

    def validate_currency(self, value):
        return value.upper()
