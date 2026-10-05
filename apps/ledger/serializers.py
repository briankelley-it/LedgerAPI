from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.ledger.models import Category


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Create category",
            value={"name": "Groceries", "color": "#4CAF50"},
            request_only=True,
        ),
        OpenApiExample(
            "Category",
            value={
                "id": 1,
                "name": "Groceries",
                "color": "#4CAF50",
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "color", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        owner = self.context["request"].user
        duplicates = Category.objects.filter(owner=owner, name__iexact=value)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("You already have a category with this name.")
        return value

    def validate_color(self, value):
        return value.upper()
