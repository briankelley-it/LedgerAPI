"""Spending summary calculations.

Kept out of the view so the math can be read and tested on its own.
All sums are done by the database with Decimal values, never floats.
"""

from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from apps.ledger.models import Expense

ZERO = Decimal("0.00")


def expenses_for(user, *, currency, start=None, end=None):
    """The user's expenses in one currency, optionally limited to a date range (inclusive)."""
    queryset = Expense.objects.filter(owner=user, currency=currency)
    if start is not None:
        queryset = queryset.filter(date__gte=start)
    if end is not None:
        queryset = queryset.filter(date__lte=end)
    return queryset


def build_summary(user, *, currency="USD", start=None, end=None):
    expenses = expenses_for(user, currency=currency, start=start, end=end)

    overall = expenses.aggregate(total=Sum("amount"), count=Count("id"))

    # .values() before .annotate() is the ORM's way of writing GROUP BY.
    by_category = (
        expenses.values("category_id", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total", "category__name")
    )

    by_month = (
        expenses.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("month")
    )

    return {
        "start": start,
        "end": end,
        "currency": currency,
        "total": overall["total"] or ZERO,
        "count": overall["count"],
        "by_category": [
            {
                "category_id": row["category_id"],
                # Expenses without a category are grouped under a null id.
                "category_name": row["category__name"],
                "total": row["total"],
                "count": row["count"],
            }
            for row in by_category
        ],
        "by_month": [
            {
                "month": row["month"].strftime("%Y-%m"),
                "total": row["total"],
                "count": row["count"],
            }
            for row in by_month
        ],
    }
