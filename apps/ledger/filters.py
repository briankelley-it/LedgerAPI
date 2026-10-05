import django_filters

from apps.ledger.models import Expense


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
