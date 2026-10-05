from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.core.openapi import UNAUTHORIZED, VALIDATION_ERROR


@extend_schema(
    tags=["auth"],
    summary="Register a new user",
    responses={201: RegisterSerializer, 400: VALIDATION_ERROR},
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    # Registration is public. Turning authentication off also means a stale
    # token sent by a client cannot make this endpoint fail with 401.
    authentication_classes = []
    permission_classes = [AllowAny]


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Log in: get an access and refresh token",
        responses={200: EmailTokenObtainPairSerializer, 400: VALIDATION_ERROR, 401: UNAUTHORIZED},
    )
)
class TokenView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Get a new access token using a refresh token",
        responses={401: UNAUTHORIZED},
    )
)
class RefreshView(TokenRefreshView):
    pass


@extend_schema(
    tags=["auth"],
    summary="Get the current user",
    responses={200: UserSerializer, 401: UNAUTHORIZED},
)
class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
