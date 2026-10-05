from django.urls import path

from apps.reports.views import SummaryView

urlpatterns = [
    path("summary/", SummaryView.as_view(), name="reports-summary"),
]
