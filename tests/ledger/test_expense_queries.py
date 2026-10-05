"""Filtering, search, ordering and pagination for GET /expenses/."""

import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from tests.factories import CategoryFactory, ExpenseFactory

pytestmark = pytest.mark.django_db

LIST = reverse("expense-list")


def ids(response):
    assert response.status_code == 200, response.json()
    return {e["id"] for e in response.json()["results"]}


def day(n):
    return datetime.date(2026, 1, n)


class TestFilters:
    def test_date_range_is_inclusive(self, auth_client, user):
        before = ExpenseFactory(owner=user, date=day(1))
        first = ExpenseFactory(owner=user, date=day(10))
        last = ExpenseFactory(owner=user, date=day(20))
        after = ExpenseFactory(owner=user, date=day(21))

        response = auth_client.get(LIST, {"date_after": "2026-01-10", "date_before": "2026-01-20"})

        assert ids(response) == {first.pk, last.pk}
        assert before.pk not in ids(response) and after.pk not in ids(response)

    def test_open_ended_date_range(self, auth_client, user):
        ExpenseFactory(owner=user, date=day(1))
        later = ExpenseFactory(owner=user, date=day(15))

        assert ids(auth_client.get(LIST, {"date_after": "2026-01-15"})) == {later.pk}

    def test_category(self, auth_client, user):
        food = CategoryFactory(owner=user)
        wanted = ExpenseFactory(owner=user, category=food)
        ExpenseFactory(owner=user)

        assert ids(auth_client.get(LIST, {"category": food.pk})) == {wanted.pk}

    def test_uncategorized(self, auth_client, user):
        loose = ExpenseFactory(owner=user, category=None)
        ExpenseFactory(owner=user)

        assert ids(auth_client.get(LIST, {"uncategorized": "true"})) == {loose.pk}

    def test_amount_range_is_inclusive(self, auth_client, user):
        ExpenseFactory(owner=user, amount=Decimal("4.99"))
        low = ExpenseFactory(owner=user, amount=Decimal("5.00"))
        high = ExpenseFactory(owner=user, amount=Decimal("10.00"))
        ExpenseFactory(owner=user, amount=Decimal("10.01"))

        response = auth_client.get(LIST, {"min_amount": "5", "max_amount": "10"})

        assert ids(response) == {low.pk, high.pk}

    def test_currency_ignores_case(self, auth_client, user):
        euro = ExpenseFactory(owner=user, currency="EUR")
        ExpenseFactory(owner=user, currency="USD")

        assert ids(auth_client.get(LIST, {"currency": "eur"})) == {euro.pk}

    def test_filters_combine(self, auth_client, user):
        food = CategoryFactory(owner=user)
        match = ExpenseFactory(owner=user, category=food, amount=Decimal("50"), date=day(5))
        ExpenseFactory(owner=user, category=food, amount=Decimal("5"), date=day(5))
        ExpenseFactory(owner=user, category=food, amount=Decimal("50"), date=day(25))

        response = auth_client.get(
            LIST, {"category": food.pk, "min_amount": "10", "date_before": "2026-01-10"}
        )

        assert ids(response) == {match.pk}

    def test_filters_never_reach_other_users_data(self, auth_client, other_user):
        theirs = CategoryFactory(owner=other_user)
        ExpenseFactory(owner=other_user, category=theirs)

        assert ids(auth_client.get(LIST, {"category": theirs.pk})) == set()

    @pytest.mark.parametrize(
        "params",
        [{"min_amount": "abc"}, {"date_after": "not-a-date"}, {"category": "x"}],
    )
    def test_invalid_filter_values_are_400(self, auth_client, params):
        response = auth_client.get(LIST, params)

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "validation_error"


class TestSearch:
    def test_searches_description_ignoring_case(self, auth_client, user):
        coffee = ExpenseFactory(owner=user, description="Morning COFFEE")
        ExpenseFactory(owner=user, description="Rent")

        assert ids(auth_client.get(LIST, {"search": "coffee"})) == {coffee.pk}


class TestOrdering:
    def test_default_is_newest_first(self, auth_client, user):
        a = ExpenseFactory(owner=user, date=day(1))
        b = ExpenseFactory(owner=user, date=day(3))
        c = ExpenseFactory(owner=user, date=day(2))

        results = auth_client.get(LIST).json()["results"]

        assert [e["id"] for e in results] == [b.pk, c.pk, a.pk]

    @pytest.mark.parametrize(
        "ordering, expected",
        [
            ("amount", ["1.00", "2.00", "3.00"]),
            ("-amount", ["3.00", "2.00", "1.00"]),
        ],
    )
    def test_by_amount(self, auth_client, user, ordering, expected):
        for amount in ["2.00", "3.00", "1.00"]:
            ExpenseFactory(owner=user, amount=Decimal(amount))

        results = auth_client.get(LIST, {"ordering": ordering}).json()["results"]

        assert [e["amount"] for e in results] == expected

    def test_by_date_ascending(self, auth_client, user):
        later = ExpenseFactory(owner=user, date=day(2))
        earlier = ExpenseFactory(owner=user, date=day(1))

        results = auth_client.get(LIST, {"ordering": "date"}).json()["results"]

        assert [e["id"] for e in results] == [earlier.pk, later.pk]

    def test_unknown_ordering_field_is_ignored(self, auth_client, user):
        ExpenseFactory(owner=user)

        assert auth_client.get(LIST, {"ordering": "owner"}).status_code == 200


class TestPagination:
    def test_default_page_size_is_20(self, auth_client, user):
        ExpenseFactory.create_batch(25, owner=user)

        body = auth_client.get(LIST).json()

        assert body["count"] == 25
        assert len(body["results"]) == 20
        assert body["next"] is not None
        assert body["previous"] is None

    def test_second_page(self, auth_client, user):
        ExpenseFactory.create_batch(25, owner=user)

        body = auth_client.get(LIST, {"page": 2}).json()

        assert len(body["results"]) == 5
        assert body["next"] is None
        assert body["previous"] is not None

    def test_pages_do_not_overlap(self, auth_client, user):
        ExpenseFactory.create_batch(6, owner=user)

        page1 = ids(auth_client.get(LIST, {"page_size": 3, "page": 1}))
        page2 = ids(auth_client.get(LIST, {"page_size": 3, "page": 2}))

        assert len(page1 | page2) == 6

    def test_page_size_is_capped_at_100(self, auth_client, user):
        ExpenseFactory.create_batch(105, owner=user)

        body = auth_client.get(LIST, {"page_size": 500}).json()

        assert len(body["results"]) == 100

    def test_page_out_of_range_is_404(self, auth_client, user):
        ExpenseFactory(owner=user)

        response = auth_client.get(LIST, {"page": 99})

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
