"""Budget calculations: how much of a budget has been spent."""

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth

from apps.ledger.models import Budget, Expense

MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)


def with_spent(budgets):
    """Add a `spent` value to every budget in one SQL query.

    For each budget the subquery adds up the owner's expenses in the same
    category, currency and calendar month. Doing it in SQL avoids running
    one extra query per budget (the "N+1 queries" problem).
    """
    spent = (
        Expense.objects.filter(
            owner=OuterRef("owner"),
            category=OuterRef("category"),
            currency=OuterRef("currency"),
        )
        .annotate(expense_month=TruncMonth("date"))
        .filter(expense_month=OuterRef("month"))
        .values("category")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    return budgets.annotate(
        spent=Coalesce(Subquery(spent, output_field=MONEY_FIELD), Value(Decimal("0.00")))
    )


def spent_for(budget):
    """Spent amount for a single budget (used right after create or update)."""
    return with_spent(Budget.objects.filter(pk=budget.pk)).values_list("spent", flat=True).get()
