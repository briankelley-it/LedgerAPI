from django.urls import path

from apps.accounts.views import MeView, RefreshView, RegisterView, TokenView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("token/", TokenView.as_view(), name="auth-token"),
    path("token/refresh/", RefreshView.as_view(), name="auth-token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
]
