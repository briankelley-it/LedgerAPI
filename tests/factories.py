import factory
from django.contrib.auth import get_user_model

DEFAULT_PASSWORD = "correct-horse-battery"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    # Same rule as registration: the username is the lowercased email.
    username = factory.LazyAttribute(lambda o: o.email.lower())
    password = factory.django.Password(DEFAULT_PASSWORD)
