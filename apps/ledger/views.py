from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from apps.core.mixins import OwnedQuerysetMixin
from apps.core.openapi import NOT_FOUND, UNAUTHORIZED, VALIDATION_ERROR
from apps.ledger.filters import ExpenseFilter
from apps.ledger.models import Category, Expense
from apps.ledger.serializers import CategorySerializer, ExpenseSerializer


@extend_schema_view(
    list=extend_schema(summary="List your categories", responses={401: UNAUTHORIZED}),
    create=extend_schema(
        summary="Create a category",
        responses={201: CategorySerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED},
    ),
    retrieve=extend_schema(
        summary="Get a category", responses={200: CategorySerializer, 404: NOT_FOUND}
    ),
    update=extend_schema(
        summary="Replace a category",
        responses={200: CategorySerializer, 400: VALIDATION_ERROR, 404: NOT_FOUND},
    ),
    partial_update=extend_schema(
        summary="Update some fields of a category",
        responses={200: CategorySerializer, 400: VALIDATION_ERROR, 404: NOT_FOUND},
    ),
    destroy=extend_schema(
        summary="Delete a category",
        description="Expenses in this category are kept and become uncategorized.",
        responses={204: None, 404: NOT_FOUND},
    ),
)
@extend_schema(tags=["categories"])
class CategoryViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


@extend_schema_view(
    list=extend_schema(
        summary="List your expenses",
        description=(
            "Filter with date_after, date_before, category, uncategorized, "
            "min_amount, max_amount and currency. Search the description with "
            "search=. Sort with ordering=date, -date, amount or -amount. "
            "Paginate with page= and page_size= (max 100)."
        ),
        responses={400: VALIDATION_ERROR, 401: UNAUTHORIZED},
    ),
    create=extend_schema(
        summary="Create an expense",
        responses={201: ExpenseSerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED},
    ),
    retrieve=extend_schema(
        summary="Get an expense", responses={200: ExpenseSerializer, 404: NOT_FOUND}
    ),
    update=extend_schema(
        summary="Replace an expense",
        responses={200: ExpenseSerializer, 400: VALIDATION_ERROR, 404: NOT_FOUND},
    ),
    partial_update=extend_schema(
        summary="Update some fields of an expense",
        responses={200: ExpenseSerializer, 400: VALIDATION_ERROR, 404: NOT_FOUND},
    ),
    destroy=extend_schema(summary="Delete an expense", responses={204: None, 404: NOT_FOUND}),
)
@extend_schema(tags=["expenses"])
class ExpenseViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    filterset_class = ExpenseFilter
    search_fields = ["description"]
    ordering_fields = ["date", "amount", "created_at"]
    ordering = ["-date", "-id"]
