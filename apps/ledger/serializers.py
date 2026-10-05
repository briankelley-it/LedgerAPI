import datetime
from decimal import Decimal

from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from apps.ledger.models import Budget, Category, Expense
from apps.ledger.services import spent_for


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


@extend_schema_field(
    {"type": "string", "pattern": r"^\d{4}-(0[1-9]|1[0-2])$", "example": "2026-10"}
)
class MonthField(serializers.Field):
    """A calendar month written as "YYYY-MM", stored as the first day of that month."""

    default_error_messages = {"invalid": "Use the format YYYY-MM, for example 2026-10."}

    def to_internal_value(self, data):
        try:
            return datetime.datetime.strptime(str(data), "%Y-%m").date()
        except ValueError:
            self.fail("invalid")

    def to_representation(self, value):
        return value.strftime("%Y-%m")


MONEY = {"max_digits": 14, "decimal_places": 2}


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Create budget",
            value={"category": 1, "month": "2026-10", "limit": "400.00", "currency": "USD"},
            request_only=True,
        ),
        OpenApiExample(
            "Budget",
            value={
                "id": 3,
                "category": 1,
                "month": "2026-10",
                "limit": "400.00",
                "currency": "USD",
                "spent": "312.50",
                "remaining": "87.50",
                "over_budget": False,
                "created_at": "2026-10-01T09:00:00Z",
                "updated_at": "2026-10-01T09:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class BudgetSerializer(serializers.ModelSerializer):
    category = OwnedCategoryField()
    month = MonthField(help_text="YYYY-MM")
    limit = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.RegexField(
        r"^[A-Za-z]{3}$",
        required=False,
        error_messages={"invalid": "Use a 3-letter currency code like USD."},
    )
    spent = serializers.SerializerMethodField(
        help_text="Total of this category's expenses in this month and currency."
    )
    remaining = serializers.SerializerMethodField(
        help_text="limit minus spent. Negative when over budget."
    )
    over_budget = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "category",
            "month",
            "limit",
            "currency",
            "spent",
            "remaining",
            "over_budget",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_limit(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Limit must be greater than 0.")
        return value

    def validate_currency(self, value):
        return value.upper()

    def validate(self, attrs):
        # One budget per category per month. On PATCH a field may be missing,
        # so fall back to the current value.
        category = attrs.get("category", getattr(self.instance, "category", None))
        month = attrs.get("month", getattr(self.instance, "month", None))
        duplicates = Budget.objects.filter(category=category, month=month)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                {"month": ["This category already has a budget for this month."]}
            )
        return attrs

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        # The `spent` loaded with the old month or category is now out of date.
        instance.spent = None
        return instance

    def _spent(self, budget):
        # List and detail views add `spent` in SQL (services.with_spent).
        # After a create or update the instance is fresh, so work it out once.
        if getattr(budget, "spent", None) is None:
            budget.spent = spent_for(budget)
        return budget.spent

    @extend_schema_field(serializers.DecimalField(**MONEY))
    def get_spent(self, budget):
        return f"{self._spent(budget):.2f}"

    @extend_schema_field(serializers.DecimalField(**MONEY))
    def get_remaining(self, budget):
        return f"{budget.limit - self._spent(budget):.2f}"

    def get_over_budget(self, budget) -> bool:
        return self._spent(budget) > budget.limit
