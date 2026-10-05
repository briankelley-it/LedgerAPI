import datetime
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from apps.ledger.models import Budget, Category, Expense

DEFAULT_PASSWORD = "correct-horse-battery"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    # Same rule as registration: the username is the lowercased email.
    username = factory.LazyAttribute(lambda o: o.email.lower())
    password = factory.django.Password(DEFAULT_PASSWORD)


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Category {n}")
    color = "#336699"


class ExpenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Expense

    owner = factory.SubFactory(UserFactory)
    # The category, when present, belongs to the same owner as the expense.
    category = factory.SubFactory(CategoryFactory, owner=factory.SelfAttribute("..owner"))
    amount = Decimal("10.00")
    currency = "USD"
    description = factory.Sequence(lambda n: f"Expense {n}")
    date = datetime.date(2026, 1, 15)


class BudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Budget

    owner = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory, owner=factory.SelfAttribute("..owner"))
    month = datetime.date(2026, 1, 1)
    limit = Decimal("100.00")
    currency = "USD"
