import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.ledger.models import Budget
from tests.factories import BudgetFactory, CategoryFactory, ExpenseFactory

pytestmark = pytest.mark.django_db

LIST = reverse("budget-list")
JAN = datetime.date(2026, 1, 1)
FEB = datetime.date(2026, 2, 1)


def detail(pk):
    return reverse("budget-detail", args=[pk])


@pytest.fixture
def food(user):
    return CategoryFactory(owner=user, name="Food")


class TestCreate:
    def test_creates_budget(self, auth_client, user, food):
        response = auth_client.post(
            LIST, {"category": food.pk, "month": "2026-10", "limit": "400.00"}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["month"] == "2026-10"
        assert body["limit"] == "400.00"
        assert body["currency"] == "USD"
        assert body["spent"] == "0.00"
        assert body["remaining"] == "400.00"
        assert body["over_budget"] is False
        budget = Budget.objects.get(pk=body["id"])
        assert budget.owner == user
        assert budget.month == datetime.date(2026, 10, 1)

    def test_new_budget_counts_existing_expenses(self, auth_client, user, food):
        ExpenseFactory(owner=user, category=food, amount=Decimal("30"), date=JAN)

        body = auth_client.post(
            LIST, {"category": food.pk, "month": "2026-01", "limit": "100"}
        ).json()

        assert body["spent"] == "30.00"

    def test_one_budget_per_category_per_month(self, auth_client, user, food):
        BudgetFactory(owner=user, category=food, month=JAN)

        response = auth_client.post(LIST, {"category": food.pk, "month": "2026-01", "limit": "5"})

        assert response.status_code == 400
        assert "month" in response.json()["error"]["details"]

    def test_same_category_different_month_is_fine(self, auth_client, user, food):
        BudgetFactory(owner=user, category=food, month=JAN)

        response = auth_client.post(LIST, {"category": food.pk, "month": "2026-02", "limit": "5"})

        assert response.status_code == 201

    def test_cannot_budget_another_users_category(self, auth_client, other_user):
        theirs = CategoryFactory(owner=other_user)

        response = auth_client.post(LIST, {"category": theirs.pk, "month": "2026-01", "limit": "5"})

        assert response.status_code == 400
        assert "category" in response.json()["error"]["details"]

    @pytest.mark.parametrize(
        "overrides, field",
        [
            ({"limit": "0"}, "limit"),
            ({"limit": "-10"}, "limit"),
            ({"limit": "1.001"}, "limit"),
            ({"month": "2026-13"}, "month"),
            ({"month": "2026-01-15"}, "month"),
            ({"month": "October"}, "month"),
            ({"currency": "EURO"}, "currency"),
            ({"category": None}, "category"),
        ],
    )
    def test_validation_errors(self, auth_client, food, overrides, field):
        payload = {"category": food.pk, "month": "2026-01", "limit": "100"}
        payload.update(overrides)

        response = auth_client.post(LIST, payload)

        assert response.status_code == 400
        assert field in response.json()["error"]["details"]

    def test_requires_authentication(self, api_client):
        assert api_client.get(LIST).status_code == 401


class TestSpent:
    """`spent` = this category's expenses in the budget's month and currency."""

    def test_spent_remaining_and_over_budget(self, auth_client, user, food, other_user):
        budget = BudgetFactory(owner=user, category=food, month=JAN, limit=Decimal("100.00"))
        # Counted: 60.25 + 45.00 = 105.25
        ExpenseFactory(owner=user, category=food, amount=Decimal("60.25"), date=JAN)
        ExpenseFactory(
            owner=user, category=food, amount=Decimal("45.00"), date=datetime.date(2026, 1, 31)
        )
        # Not counted: other month, other category, other currency, uncategorized
        ExpenseFactory(owner=user, category=food, amount=Decimal("999"), date=FEB)
        ExpenseFactory(owner=user, amount=Decimal("999"), date=JAN)
        ExpenseFactory(owner=user, category=food, amount=Decimal("999"), date=JAN, currency="EUR")
        ExpenseFactory(owner=user, category=None, amount=Decimal("999"), date=JAN)

        body = auth_client.get(detail(budget.pk)).json()

        assert body["spent"] == "105.25"
        assert body["remaining"] == "-5.25"
        assert body["over_budget"] is True

    def test_exactly_at_limit_is_not_over(self, auth_client, user, food):
        budget = BudgetFactory(owner=user, category=food, month=JAN, limit=Decimal("50"))
        ExpenseFactory(owner=user, category=food, amount=Decimal("50"), date=JAN)

        body = auth_client.get(detail(budget.pk)).json()

        assert body["remaining"] == "0.00"
        assert body["over_budget"] is False

    def test_list_annotates_every_budget_in_one_query(
        self, auth_client, user, django_assert_max_num_queries
    ):
        for month in range(1, 7):
            category = CategoryFactory(owner=user)
            BudgetFactory(owner=user, category=category, month=datetime.date(2026, month, 1))
            ExpenseFactory(owner=user, category=category, date=datetime.date(2026, month, 2))

        # One COUNT for pagination and one SELECT for the page, however many budgets.
        with django_assert_max_num_queries(2):
            body = auth_client.get(LIST).json()

        assert {b["spent"] for b in body["results"]} == {"10.00"}

    def test_patch_month_recalculates_spent(self, auth_client, user, food):
        budget = BudgetFactory(owner=user, category=food, month=JAN)
        ExpenseFactory(owner=user, category=food, amount=Decimal("20"), date=FEB)

        body = auth_client.patch(detail(budget.pk), {"month": "2026-02"}).json()

        assert body["month"] == "2026-02"
        assert body["spent"] == "20.00"


class TestFiltersAndOrdering:
    def test_filter_by_month(self, auth_client, user):
        jan = BudgetFactory(owner=user, month=JAN)
        BudgetFactory(owner=user, month=FEB)

        results = auth_client.get(LIST, {"month": "2026-01"}).json()["results"]

        assert [b["id"] for b in results] == [jan.pk]

    def test_filter_by_category(self, auth_client, user, food):
        wanted = BudgetFactory(owner=user, category=food)
        BudgetFactory(owner=user)

        results = auth_client.get(LIST, {"category": food.pk}).json()["results"]

        assert [b["id"] for b in results] == [wanted.pk]

    def test_filter_over_budget(self, auth_client, user):
        over = BudgetFactory(owner=user, limit=Decimal("5"))
        ExpenseFactory(owner=user, category=over.category, amount=Decimal("6"), date=JAN)
        under = BudgetFactory(owner=user, limit=Decimal("500"))

        over_ids = [
            b["id"] for b in auth_client.get(LIST, {"over_budget": "true"}).json()["results"]
        ]
        under_ids = [
            b["id"] for b in auth_client.get(LIST, {"over_budget": "false"}).json()["results"]
        ]

        assert over_ids == [over.pk]
        assert under_ids == [under.pk]

    def test_invalid_month_filter_is_400(self, auth_client):
        response = auth_client.get(LIST, {"month": "2026-1"})

        assert response.status_code == 400
        assert "month" in response.json()["error"]["details"]

    def test_order_by_spent(self, auth_client, user):
        low = BudgetFactory(owner=user)
        high = BudgetFactory(owner=user)
        ExpenseFactory(owner=user, category=high.category, amount=Decimal("80"), date=JAN)

        results = auth_client.get(LIST, {"ordering": "-spent"}).json()["results"]

        assert [b["id"] for b in results] == [high.pk, low.pk]


class TestUpdateDelete:
    def test_put(self, auth_client, user, food):
        budget = BudgetFactory(owner=user, category=food)

        response = auth_client.put(
            detail(budget.pk),
            {"category": food.pk, "month": "2026-03", "limit": "250.00", "currency": "eur"},
        )

        assert response.status_code == 200
        budget.refresh_from_db()
        assert (budget.month, budget.limit, budget.currency) == (
            datetime.date(2026, 3, 1),
            Decimal("250.00"),
            "EUR",
        )

    def test_patch_keeping_same_month_is_not_a_duplicate(self, auth_client, user):
        budget = BudgetFactory(owner=user)

        response = auth_client.patch(detail(budget.pk), {"limit": "75"})

        assert response.status_code == 200
        assert response.json()["limit"] == "75.00"

    def test_patch_into_an_existing_month_fails(self, auth_client, user, food):
        BudgetFactory(owner=user, category=food, month=JAN)
        budget = BudgetFactory(owner=user, category=food, month=FEB)

        response = auth_client.patch(detail(budget.pk), {"month": "2026-01"})

        assert response.status_code == 400

    def test_delete(self, auth_client, user):
        budget = BudgetFactory(owner=user)

        assert auth_client.delete(detail(budget.pk)).status_code == 204
        assert not Budget.objects.filter(pk=budget.pk).exists()

    def test_deleting_the_category_deletes_its_budgets(self, auth_client, user, food):
        budget = BudgetFactory(owner=user, category=food)

        auth_client.delete(reverse("category-detail", args=[food.pk]))

        assert not Budget.objects.filter(pk=budget.pk).exists()


class TestIsolation:
    @pytest.fixture
    def foreign(self, other_user):
        return BudgetFactory(owner=other_user, limit=Decimal("10"))

    def test_not_listed(self, auth_client, foreign):
        assert auth_client.get(LIST).json()["count"] == 0

    def test_cannot_retrieve(self, auth_client, foreign):
        assert auth_client.get(detail(foreign.pk)).status_code == 404

    def test_cannot_patch(self, auth_client, foreign):
        assert auth_client.patch(detail(foreign.pk), {"limit": "1"}).status_code == 404
        foreign.refresh_from_db()
        assert foreign.limit == Decimal("10")

    def test_cannot_delete(self, auth_client, foreign):
        assert auth_client.delete(detail(foreign.pk)).status_code == 404
        assert Budget.objects.filter(pk=foreign.pk).exists()

    def test_other_users_expenses_never_count(self, auth_client, user, other_user, food):
        budget = BudgetFactory(owner=user, category=food, month=JAN)
        # Even an expense forced into my category id by another owner is ignored.
        ExpenseFactory(owner=other_user, category=food, amount=Decimal("50"), date=JAN)

        assert auth_client.get(detail(budget.pk)).json()["spent"] == "0.00"


class TestDatabaseConstraints:
    def test_month_must_be_first_day(self, user):
        with pytest.raises(IntegrityError), transaction.atomic():
            BudgetFactory(owner=user, month=datetime.date(2026, 1, 15))

    def test_limit_must_be_positive(self, user):
        with pytest.raises(IntegrityError), transaction.atomic():
            BudgetFactory(owner=user, limit=Decimal("0"))

    def test_unique_per_category_and_month(self, user, food):
        BudgetFactory(owner=user, category=food, month=JAN)
        with pytest.raises(IntegrityError), transaction.atomic():
            BudgetFactory(owner=user, category=food, month=JAN)


def test_str():
    budget = Budget(month=JAN, limit=Decimal("5.00"), currency="USD")
    budget.category = CategoryFactory.build(name="Food")

    assert str(budget) == "Food 2026-01: 5.00 USD"
