from django.contrib import admin

from apps.ledger.models import Budget, Category, Expense


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "owner", "created_at"]
    list_filter = ["owner"]
    search_fields = ["name"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["date", "amount", "currency", "description", "category", "owner"]
    list_filter = ["owner", "currency"]
    search_fields = ["description"]
    date_hierarchy = "date"


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["category", "month", "limit", "currency", "owner"]
    list_filter = ["owner", "month"]
