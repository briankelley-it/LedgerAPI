from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import HealthView

api_v1 = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.ledger.urls")),
]

urlpatterns = [
    # Visiting the bare host in a browser lands on the interactive API docs.
    path("", RedirectView.as_view(pattern_name="swagger-ui"), name="root"),
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

handler404 = "apps.core.exceptions.not_found"
handler500 = "apps.core.exceptions.server_error"
