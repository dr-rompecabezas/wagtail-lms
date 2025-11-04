"""Default settings for wagtail-lms"""

from django.conf import settings

WAGTAIL_LMS_SCORM_UPLOAD_PATH = getattr(
    settings, "WAGTAIL_LMS_SCORM_UPLOAD_PATH", "scorm_packages/"
)

WAGTAIL_LMS_CONTENT_PATH = getattr(
    settings, "WAGTAIL_LMS_CONTENT_PATH", "scorm_content/"
)

WAGTAIL_LMS_AUTO_ENROLL = getattr(settings, "WAGTAIL_LMS_AUTO_ENROLL", False)

# Default CSS class mappings (Bootstrap by default)
DEFAULT_CSS_CLASSES = {
    # Layout
    "container": "container",
    "row": "row",
    "col_main": "col-md-8",
    "col_sidebar": "col-md-4",
    # Buttons
    "btn": "btn",
    "btn_primary": "btn btn-primary",
    "btn_success": "btn btn-success",
    "btn_secondary": "btn btn-secondary",
    "btn_lg": "btn-lg",
    # Alerts
    "alert": "alert",
    "alert_info": "alert alert-info",
    "alert_warning": "alert alert-warning",
    "alert_success": "alert alert-success",
    # Lists
    "list_unstyled": "list-unstyled",
}

WAGTAIL_LMS_CSS_CLASSES = getattr(
    settings,
    "WAGTAIL_LMS_CSS_CLASSES",
    DEFAULT_CSS_CLASSES,
)
