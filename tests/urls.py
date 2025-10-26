"""URL configuration for tests."""

from django.urls import include, path

urlpatterns = [
    path("lms/", include("wagtail_lms.urls")),
]
