import datetime

import django_filters
from django.core.validators import RegexValidator
from django.db.models import F

from apps.ledger.models import Budget, Expense


class ExpenseFilter(django_filters.FilterSet):
    """Query parameters for GET /expenses/.

    Example: ?date_after=2026-01-01&date_before=2026-01-31&min_amount=10
    """

    # Gives two parameters, date_after and date_before (both inclusive).
    date = django_filters.DateFromToRangeFilter(label="Date range (inclusive)")
    category = django_filters.NumberFilter(field_name="category_id", label="Category id")
    uncategorized = django_filters.BooleanFilter(
        field_name="category", lookup_expr="isnull", label="Only expenses without a category"
    )
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")
    currency = django_filters.CharFilter(field_name="currency", lookup_expr="iexact")

    class Meta:
        model = Expense
        fields = ["date", "category", "uncategorized", "min_amount", "max_amount", "currency"]


class BudgetFilter(django_filters.FilterSet):
    """Query parameters for GET /budgets/. Example: ?month=2026-10&over_budget=true"""

    month = django_filters.CharFilter(
        method="filter_month",
        label="Month as YYYY-MM",
        validators=[RegexValidator(r"^\d{4}-(0[1-9]|1[0-2])$", "Use the format YYYY-MM.")],
    )
    category = django_filters.NumberFilter(field_name="category_id", label="Category id")
    over_budget = django_filters.BooleanFilter(
        method="filter_over_budget", label="Only budgets that are (or are not) over the limit"
    )

    class Meta:
        model = Budget
        fields = ["month", "category", "over_budget"]

    def filter_month(self, queryset, name, value):
        return queryset.filter(month=datetime.datetime.strptime(value, "%Y-%m").date())

    def filter_over_budget(self, queryset, name, value):
        # `spent` is added to the queryset by the view (services.with_spent).
        if value:
            return queryset.filter(spent__gt=F("limit"))
        return queryset.filter(spent__lte=F("limit"))
