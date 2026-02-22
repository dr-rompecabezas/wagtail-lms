from django.urls import path

from . import views

app_name = "wagtail_lms"

urlpatterns = [
    # SCORM
    path(
        "scorm-lesson/<int:lesson_id>/play/",
        views.scorm_player_view,
        name="scorm_player",
    ),
    path("scorm-api/<int:attempt_id>/", views.scorm_api_endpoint, name="scorm_api"),
    path(
        "course/<int:course_id>/enroll/", views.enroll_in_course, name="enroll_course"
    ),
    path(
        "scorm-content/<path:content_path>",
        views.ServeScormContentView.as_view(),
        name="serve_scorm_content",
    ),
    # H5P
    path(
        "h5p-xapi/<int:activity_id>/",
        views.h5p_xapi_view,
        name="h5p_xapi",
    ),
    path(
        "h5p-content-user-data/<int:activity_id>/",
        views.h5p_content_user_data_view,
        name="h5p_content_user_data",
    ),
    path(
        "h5p-content/<path:content_path>",
        views.ServeH5PContentView.as_view(),
        name="serve_h5p_content",
    ),
]
