from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower

hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a hex color like #1A2B3C.",
)


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimestampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, blank=True, validators=[hex_color_validator])

    class Meta:
        ordering = ["name", "id"]
        verbose_name_plural = "categories"
        constraints = [
            # "Food" and "food" count as the same category for one user.
            models.UniqueConstraint("owner", Lower("name"), name="unique_category_name_per_owner"),
        ]

    def __str__(self):
        return self.name


class Expense(TimestampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses"
    )
    # Deleting a category keeps its expenses; they just become uncategorized.
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    # Decimal, never float: 0.1 + 0.2 must equal 0.3 when adding up money.
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    currency = models.CharField(max_length=3, default="USD")
    description = models.CharField(max_length=255, blank=True)
    date = models.DateField()

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="expense_amount_positive"
            ),
        ]
        indexes = [
            # Most queries are "my expenses in a date range".
            models.Index(fields=["owner", "date"], name="expense_owner_date_idx"),
        ]

    def __str__(self):
        return f"{self.date} {self.amount} {self.currency} {self.description}".strip()


class Budget(TimestampedModel):
    """A monthly spending limit for one category."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets"
    )
    # A budget only makes sense for its category, so it goes when the category goes.
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    # Always the first day of the month. The API shows it as "YYYY-MM".
    month = models.DateField()
    limit = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    currency = models.CharField(max_length=3, default="USD")

    class Meta:
        ordering = ["-month", "category__name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "category", "month"], name="unique_budget_per_category_month"
            ),
            models.CheckConstraint(condition=models.Q(limit__gt=0), name="budget_limit_positive"),
            models.CheckConstraint(
                condition=models.Q(month__day=1), name="budget_month_is_first_day"
            ),
        ]

    def __str__(self):
        return f"{self.category} {self.month:%Y-%m}: {self.limit} {self.currency}"
