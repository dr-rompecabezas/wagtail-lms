from django.urls import path

from . import views

app_name = "wagtail_lms"

urlpatterns = [
    path("course/<int:course_id>/play/", views.scorm_player_view, name="scorm_player"),
    path("scorm-api/<int:attempt_id>/", views.scorm_api_endpoint, name="scorm_api"),
    path(
        "course/<int:course_id>/enroll/", views.enroll_in_course, name="enroll_course"
    ),
    path(
        "scorm-content/<path:content_path>",
        views.ServeScormContentView.as_view(),
        name="serve_scorm_content",
    ),
]
