from django.conf import settings
from django.core.validators import RegexValidator
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
