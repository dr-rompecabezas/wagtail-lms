"""Default settings for wagtail-lms"""

from django.conf import settings

WAGTAIL_LMS_SCORM_UPLOAD_PATH = getattr(
    settings, "WAGTAIL_LMS_SCORM_UPLOAD_PATH", "scorm_packages/"
)

WAGTAIL_LMS_CONTENT_PATH = getattr(
    settings, "WAGTAIL_LMS_CONTENT_PATH", "scorm_content/"
)

WAGTAIL_LMS_AUTO_ENROLL = getattr(settings, "WAGTAIL_LMS_AUTO_ENROLL", False)
