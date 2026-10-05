import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.ledger.models import Category
from tests.factories import CategoryFactory

pytestmark = pytest.mark.django_db

LIST = reverse("category-list")


def detail(pk):
    return reverse("category-detail", args=[pk])


class TestList:
    def test_requires_authentication(self, api_client):
        assert api_client.get(LIST).status_code == 401

    def test_returns_only_my_categories_sorted_by_name(self, auth_client, user, other_user):
        CategoryFactory(owner=user, name="Rent")
        CategoryFactory(owner=user, name="Groceries")
        CategoryFactory(owner=other_user, name="Secret")

        response = auth_client.get(LIST)

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert [c["name"] for c in body["results"]] == ["Groceries", "Rent"]

    def test_search_by_name(self, auth_client, user):
        CategoryFactory(owner=user, name="Groceries")
        CategoryFactory(owner=user, name="Rent")

        response = auth_client.get(LIST, {"search": "groc"})

        assert [c["name"] for c in response.json()["results"]] == ["Groceries"]


class TestCreate:
    def test_creates_category_for_current_user(self, auth_client, user):
        response = auth_client.post(LIST, {"name": "Groceries", "color": "#4caf50"})

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Groceries"
        assert body["color"] == "#4CAF50"
        assert Category.objects.get(pk=body["id"]).owner == user

    def test_color_is_optional(self, auth_client):
        response = auth_client.post(LIST, {"name": "Misc"})

        assert response.status_code == 201
        assert response.json()["color"] == ""

    def test_owner_in_payload_is_ignored(self, auth_client, user, other_user):
        response = auth_client.post(LIST, {"name": "Sneaky", "owner": other_user.pk})

        assert response.status_code == 201
        assert Category.objects.get(pk=response.json()["id"]).owner == user

    def test_name_must_be_unique_per_user_ignoring_case(self, auth_client, user):
        CategoryFactory(owner=user, name="Groceries")

        response = auth_client.post(LIST, {"name": "groceries"})

        assert response.status_code == 400
        assert "name" in response.json()["error"]["details"]

    def test_same_name_is_fine_for_different_users(self, auth_client, other_user):
        CategoryFactory(owner=other_user, name="Groceries")

        response = auth_client.post(LIST, {"name": "Groceries"})

        assert response.status_code == 201

    @pytest.mark.parametrize(
        "payload, field",
        [
            ({}, "name"),
            ({"name": ""}, "name"),
            ({"name": "x" * 51}, "name"),
            ({"name": "Food", "color": "red"}, "color"),
            ({"name": "Food", "color": "#12345"}, "color"),
        ],
    )
    def test_validation_errors(self, auth_client, payload, field):
        response = auth_client.post(LIST, payload)

        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert field in error["details"]


class TestDetail:
    def test_retrieve(self, auth_client, user):
        category = CategoryFactory(owner=user, name="Rent")

        response = auth_client.get(detail(category.pk))

        assert response.status_code == 200
        assert response.json()["name"] == "Rent"

    def test_put_replaces_fields(self, auth_client, user):
        category = CategoryFactory(owner=user, name="Rent", color="#000000")

        response = auth_client.put(detail(category.pk), {"name": "Housing", "color": "#FFFFFF"})

        assert response.status_code == 200
        category.refresh_from_db()
        assert (category.name, category.color) == ("Housing", "#FFFFFF")

    def test_patch_updates_one_field(self, auth_client, user):
        category = CategoryFactory(owner=user, name="Rent", color="#000000")

        response = auth_client.patch(detail(category.pk), {"color": "#ABCDEF"})

        assert response.status_code == 200
        category.refresh_from_db()
        assert (category.name, category.color) == ("Rent", "#ABCDEF")

    def test_keeping_own_name_is_not_a_duplicate(self, auth_client, user):
        category = CategoryFactory(owner=user, name="Rent")

        response = auth_client.patch(detail(category.pk), {"name": "RENT"})

        assert response.status_code == 200

    def test_renaming_to_another_existing_name_fails(self, auth_client, user):
        CategoryFactory(owner=user, name="Rent")
        category = CategoryFactory(owner=user, name="Food")

        response = auth_client.patch(detail(category.pk), {"name": "rent"})

        assert response.status_code == 400

    def test_delete(self, auth_client, user):
        category = CategoryFactory(owner=user)

        response = auth_client.delete(detail(category.pk))

        assert response.status_code == 204
        assert not Category.objects.filter(pk=category.pk).exists()

    def test_missing_id_is_404(self, auth_client):
        response = auth_client.get(detail(999_999))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestIsolation:
    """One user must never see or change another user's categories.

    The answer is always 404, the same as for an id that does not exist.
    """

    @pytest.fixture
    def foreign(self, other_user):
        return CategoryFactory(owner=other_user, name="Theirs", color="#111111")

    def test_cannot_retrieve(self, auth_client, foreign):
        assert auth_client.get(detail(foreign.pk)).status_code == 404

    def test_cannot_put(self, auth_client, foreign):
        response = auth_client.put(detail(foreign.pk), {"name": "Mine now"})

        assert response.status_code == 404
        foreign.refresh_from_db()
        assert foreign.name == "Theirs"

    def test_cannot_patch(self, auth_client, foreign):
        response = auth_client.patch(detail(foreign.pk), {"color": "#222222"})

        assert response.status_code == 404
        foreign.refresh_from_db()
        assert foreign.color == "#111111"

    def test_cannot_delete(self, auth_client, foreign):
        assert auth_client.delete(detail(foreign.pk)).status_code == 404
        assert Category.objects.filter(pk=foreign.pk).exists()


def test_database_enforces_unique_name_ignoring_case(user):
    """The constraint is a safety net in case the serializer check is bypassed."""
    CategoryFactory(owner=user, name="Food")
    with pytest.raises(IntegrityError), transaction.atomic():
        CategoryFactory(owner=user, name="FOOD")


def test_str_is_the_name():
    assert str(Category(name="Rent")) == "Rent"
