from django.contrib import admin

from apps.ledger.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "owner", "created_at"]
    list_filter = ["owner"]
    search_fields = ["name"]
