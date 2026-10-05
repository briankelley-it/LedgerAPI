"""The summary math, checked against totals worked out by hand."""

import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.reports.services import build_summary
from tests.factories import CategoryFactory, ExpenseFactory

pytestmark = pytest.mark.django_db

URL = reverse("reports-summary")


def d(month, day, year=2026):
    return datetime.date(year, month, day)


@pytest.fixture
def ledger(user, other_user):
    """A small, known set of expenses.

    Rent:       1000.00 (Jan 1) + 1000.00 (Feb 1)            = 2000.00
    Groceries:    45.10 (Jan 5) + 54.90 (Jan 20) + 12.25 (Feb 14) = 112.25
    No category:   9.99 (Feb 28)                                 =   9.99
    -------------------------------------------------------------------
    Total:                                                         2122.24
    January:  1000.00 + 45.10 + 54.90 = 1100.00
    February: 1000.00 + 12.25 + 9.99  = 1022.24

    Plus noise that must never be counted: a EUR expense and another
    user's expense.
    """
    rent = CategoryFactory(owner=user, name="Rent")
    groceries = CategoryFactory(owner=user, name="Groceries")

    ExpenseFactory(owner=user, category=rent, amount=Decimal("1000.00"), date=d(1, 1))
    ExpenseFactory(owner=user, category=rent, amount=Decimal("1000.00"), date=d(2, 1))
    ExpenseFactory(owner=user, category=groceries, amount=Decimal("45.10"), date=d(1, 5))
    ExpenseFactory(owner=user, category=groceries, amount=Decimal("54.90"), date=d(1, 20))
    ExpenseFactory(owner=user, category=groceries, amount=Decimal("12.25"), date=d(2, 14))
    ExpenseFactory(owner=user, category=None, amount=Decimal("9.99"), date=d(2, 28))

    ExpenseFactory(owner=user, category=rent, amount=Decimal("500.00"), currency="EUR")
    ExpenseFactory(owner=other_user, amount=Decimal("777.77"), date=d(1, 10))

    return {"rent": rent, "groceries": groceries}


def test_requires_authentication(api_client):
    assert api_client.get(URL).status_code == 401


def test_full_summary(auth_client, ledger):
    response = auth_client.get(URL)

    assert response.status_code == 200
    assert response.json() == {
        "start": None,
        "end": None,
        "currency": "USD",
        "total": "2122.24",
        "count": 6,
        "by_category": [
            {
                "category_id": ledger["rent"].pk,
                "category_name": "Rent",
                "total": "2000.00",
                "count": 2,
            },
            {
                "category_id": ledger["groceries"].pk,
                "category_name": "Groceries",
                "total": "112.25",
                "count": 3,
            },
            {"category_id": None, "category_name": None, "total": "9.99", "count": 1},
        ],
        "by_month": [
            {"month": "2026-01", "total": "1100.00", "count": 3},
            {"month": "2026-02", "total": "1022.24", "count": 3},
        ],
    }


def test_date_range_is_inclusive(auth_client, ledger):
    # Jan 5 through Feb 1: groceries 45.10 + 54.90 and rent 1000.00 (Feb 1).
    body = auth_client.get(URL, {"start": "2026-01-05", "end": "2026-02-01"}).json()

    assert body["start"] == "2026-01-05"
    assert body["end"] == "2026-02-01"
    assert body["total"] == "1100.00"
    assert body["count"] == 3
    assert body["by_month"] == [
        {"month": "2026-01", "total": "100.00", "count": 2},
        {"month": "2026-02", "total": "1000.00", "count": 1},
    ]


def test_only_start(auth_client, ledger):
    # Feb 14 onwards: 12.25 + 9.99
    body = auth_client.get(URL, {"start": "2026-02-14"}).json()

    assert body["total"] == "22.24"


def test_only_end(auth_client, ledger):
    # Up to Jan 5: 1000.00 + 45.10
    body = auth_client.get(URL, {"end": "2026-01-05"}).json()

    assert body["total"] == "1045.10"


def test_other_currency(auth_client, ledger):
    body = auth_client.get(URL, {"currency": "eur"}).json()

    assert body["currency"] == "EUR"
    assert body["total"] == "500.00"
    assert body["count"] == 1


def test_empty_result_is_zero_not_null(auth_client):
    body = auth_client.get(URL).json()

    assert body["total"] == "0.00"
    assert body["count"] == 0
    assert body["by_category"] == []
    assert body["by_month"] == []


def test_decimal_math_has_no_float_rounding_errors(user):
    # With floats, 0.1 + 0.2 == 0.30000000000000004.
    ExpenseFactory(owner=user, amount=Decimal("0.10"))
    ExpenseFactory(owner=user, amount=Decimal("0.20"))

    summary = build_summary(user)

    assert summary["total"] == Decimal("0.30")


def test_months_are_kept_apart_across_years(user):
    ExpenseFactory(owner=user, amount=Decimal("1.00"), date=d(12, 31, year=2025))
    ExpenseFactory(owner=user, amount=Decimal("2.00"), date=d(12, 1, year=2026))

    months = [row["month"] for row in build_summary(user)["by_month"]]

    assert months == ["2025-12", "2026-12"]


@pytest.mark.parametrize(
    "params, field",
    [
        ({"start": "2026-02-01", "end": "2026-01-01"}, "end"),
        ({"start": "yesterday"}, "start"),
        ({"end": "2026-02-30"}, "end"),
        ({"currency": "DOLLARS"}, "currency"),
    ],
)
def test_invalid_query_params(auth_client, params, field):
    response = auth_client.get(URL, params)

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]
