from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

User = get_user_model()

DUPLICATE_EMAIL = "A user with this email already exists."


def normalize_email(email):
    return email.strip().lower()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "date_joined"]
        read_only_fields = fields


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Register",
            value={"email": "jane@example.com", "password": "correct-horse-battery"},
            request_only=True,
        ),
        OpenApiExample(
            "Created user",
            value={"id": 1, "email": "jane@example.com", "date_joined": "2026-10-05T12:00:00Z"},
            response_only=True,
        ),
    ]
)
class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "email", "password", "date_joined"]
        read_only_fields = ["id", "date_joined"]

    def validate_email(self, value):
        email = normalize_email(value)
        if User.objects.filter(username=email).exists():
            raise serializers.ValidationError(DUPLICATE_EMAIL)
        return email

    def validate(self, attrs):
        # Run Django's password validators (minimum length, common passwords,
        # too similar to the email, ...). They need a user to compare against.
        candidate = User(username=attrs["email"], email=attrs["email"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]
        try:
            # The username is the lowercased email. That keeps emails unique
            # at the database level without needing a custom user model.
            return User.objects.create_user(
                username=email, email=email, password=validated_data["password"]
            )
        except IntegrityError as exc:
            # Two requests registered the same email at the same moment.
            raise serializers.ValidationError({"email": [DUPLICATE_EMAIL]}) from exc


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Login",
            value={"email": "jane@example.com", "password": "correct-horse-battery"},
            request_only=True,
        ),
        OpenApiExample(
            "Tokens",
            value={"refresh": "eyJhbGciOiJIUzI1NiIs...", "access": "eyJhbGciOiJIUzI1NiIs..."},
            response_only=True,
        ),
    ]
)
class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Log in with email + password instead of username + password."""

    username_field = "email"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"] = serializers.EmailField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=normalize_email(attrs["email"]),
            password=attrs["password"],
        )
        if user is None or not api_settings.USER_AUTHENTICATION_RULE(user):
            raise exceptions.AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account"
            )

        refresh = self.get_token(user)
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}
