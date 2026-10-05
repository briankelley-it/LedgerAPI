import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.ledger.models import Expense
from tests.factories import CategoryFactory, ExpenseFactory

pytestmark = pytest.mark.django_db

LIST = reverse("expense-list")


def detail(pk):
    return reverse("expense-detail", args=[pk])


def valid_payload(**overrides):
    payload = {"amount": "42.50", "description": "Groceries", "date": "2026-10-04"}
    payload.update(overrides)
    return payload


class TestCreate:
    def test_creates_expense_for_current_user(self, auth_client, user):
        category = CategoryFactory(owner=user)

        response = auth_client.post(LIST, valid_payload(category=category.pk))

        assert response.status_code == 201
        body = response.json()
        assert body["amount"] == "42.50"
        assert body["currency"] == "USD"
        assert body["category"] == category.pk
        expense = Expense.objects.get(pk=body["id"])
        assert expense.owner == user
        assert expense.amount == Decimal("42.50")

    def test_category_is_optional(self, auth_client):
        response = auth_client.post(LIST, valid_payload())

        assert response.status_code == 201
        assert response.json()["category"] is None

    def test_currency_is_uppercased(self, auth_client):
        response = auth_client.post(LIST, valid_payload(currency="eur"))

        assert response.json()["currency"] == "EUR"

    def test_numeric_amount_is_stored_exactly(self, auth_client):
        # A JSON number like 0.1 must not turn into 0.1000000000000000055...
        response = auth_client.post(LIST, valid_payload(amount=0.1))

        assert response.status_code == 201
        assert response.json()["amount"] == "0.10"

    def test_cannot_use_another_users_category(self, auth_client, other_user):
        foreign = CategoryFactory(owner=other_user)

        response = auth_client.post(LIST, valid_payload(category=foreign.pk))

        assert response.status_code == 400
        assert "category" in response.json()["error"]["details"]

    def test_owner_in_payload_is_ignored(self, auth_client, user, other_user):
        response = auth_client.post(LIST, valid_payload(owner=other_user.pk))

        assert Expense.objects.get(pk=response.json()["id"]).owner == user

    @pytest.mark.parametrize(
        "overrides, field",
        [
            ({"amount": "0"}, "amount"),
            ({"amount": "-5.00"}, "amount"),
            ({"amount": "1.234"}, "amount"),
            ({"amount": "abc"}, "amount"),
            ({"amount": "12345678901.00"}, "amount"),
            ({"amount": None}, "amount"),
            ({"date": "2026-13-01"}, "date"),
            ({"date": None}, "date"),
            ({"currency": "US"}, "currency"),
            ({"currency": "US1"}, "currency"),
            ({"description": "x" * 256}, "description"),
            ({"category": 999_999}, "category"),
        ],
    )
    def test_validation_errors(self, auth_client, overrides, field):
        response = auth_client.post(LIST, valid_payload(**overrides))

        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert field in error["details"]

    def test_amount_and_date_are_required(self, auth_client):
        response = auth_client.post(LIST, {})

        assert response.status_code == 400
        assert set(response.json()["error"]["details"]) == {"amount", "date"}

    def test_requires_authentication(self, api_client):
        assert api_client.post(LIST, valid_payload()).status_code == 401


class TestReadUpdateDelete:
    def test_list_returns_only_my_expenses_newest_first(self, auth_client, user, other_user):
        old = ExpenseFactory(owner=user, date=datetime.date(2026, 1, 1))
        new = ExpenseFactory(owner=user, date=datetime.date(2026, 2, 1))
        ExpenseFactory(owner=other_user)

        response = auth_client.get(LIST)

        assert response.status_code == 200
        assert [e["id"] for e in response.json()["results"]] == [new.pk, old.pk]

    def test_retrieve(self, auth_client, user):
        expense = ExpenseFactory(owner=user, amount=Decimal("9.99"))

        response = auth_client.get(detail(expense.pk))

        assert response.status_code == 200
        assert response.json()["amount"] == "9.99"

    def test_put_replaces_fields(self, auth_client, user):
        expense = ExpenseFactory(owner=user)

        response = auth_client.put(
            detail(expense.pk),
            {"amount": "5.00", "date": "2026-03-01", "description": "Coffee", "category": None},
        )

        assert response.status_code == 200
        expense.refresh_from_db()
        assert expense.amount == Decimal("5.00")
        assert expense.description == "Coffee"
        assert expense.category is None

    def test_patch_updates_one_field(self, auth_client, user):
        expense = ExpenseFactory(owner=user, description="Before")

        response = auth_client.patch(detail(expense.pk), {"description": "After"})

        assert response.status_code == 200
        expense.refresh_from_db()
        assert expense.description == "After"

    def test_patch_validates_amount(self, auth_client, user):
        expense = ExpenseFactory(owner=user)

        response = auth_client.patch(detail(expense.pk), {"amount": "-1"})

        assert response.status_code == 400

    def test_delete(self, auth_client, user):
        expense = ExpenseFactory(owner=user)

        response = auth_client.delete(detail(expense.pk))

        assert response.status_code == 204
        assert not Expense.objects.filter(pk=expense.pk).exists()

    def test_deleting_a_category_keeps_its_expenses(self, auth_client, user):
        expense = ExpenseFactory(owner=user)

        auth_client.delete(reverse("category-detail", args=[expense.category_id]))

        expense.refresh_from_db()
        assert expense.category is None


class TestIsolation:
    """Another user's expenses behave exactly like ids that do not exist."""

    @pytest.fixture
    def foreign(self, other_user):
        return ExpenseFactory(owner=other_user, description="Theirs")

    def test_cannot_retrieve(self, auth_client, foreign):
        assert auth_client.get(detail(foreign.pk)).status_code == 404

    def test_cannot_put(self, auth_client, foreign):
        response = auth_client.put(detail(foreign.pk), valid_payload())

        assert response.status_code == 404
        foreign.refresh_from_db()
        assert foreign.description == "Theirs"

    def test_cannot_patch(self, auth_client, foreign):
        response = auth_client.patch(detail(foreign.pk), {"description": "Mine"})

        assert response.status_code == 404
        foreign.refresh_from_db()
        assert foreign.description == "Theirs"

    def test_cannot_delete(self, auth_client, foreign):
        assert auth_client.delete(detail(foreign.pk)).status_code == 404
        assert Expense.objects.filter(pk=foreign.pk).exists()

    def test_cannot_move_my_expense_into_their_category(self, auth_client, user, other_user):
        mine = ExpenseFactory(owner=user)
        theirs = CategoryFactory(owner=other_user)

        response = auth_client.patch(detail(mine.pk), {"category": theirs.pk})

        assert response.status_code == 400
        mine.refresh_from_db()
        assert mine.category_id != theirs.pk


def test_database_rejects_non_positive_amounts(user):
    """The check constraint is a safety net if validation is ever bypassed."""
    with pytest.raises(IntegrityError), transaction.atomic():
        ExpenseFactory(owner=user, amount=Decimal("0"))


def test_str_mentions_date_and_amount():
    expense = Expense(date=datetime.date(2026, 1, 2), amount=Decimal("3.50"), currency="USD")

    assert str(expense) == "2026-01-02 3.50 USD"
