"""Default settings for wagtail-lms"""

from django.conf import settings

WAGTAIL_LMS_SCORM_UPLOAD_PATH = getattr(
    settings, "WAGTAIL_LMS_SCORM_UPLOAD_PATH", "scorm_packages/"
)

WAGTAIL_LMS_CONTENT_PATH = getattr(
    settings, "WAGTAIL_LMS_CONTENT_PATH", "scorm_content/"
)

WAGTAIL_LMS_AUTO_ENROLL = getattr(settings, "WAGTAIL_LMS_AUTO_ENROLL", True)

WAGTAIL_LMS_CACHE_CONTROL = getattr(
    settings,
    "WAGTAIL_LMS_CACHE_CONTROL",
    {
        "text/html": "no-cache",
        "text/css": "max-age=86400",
        "application/javascript": "max-age=86400",
        "text/javascript": "max-age=86400",
        "image/*": "max-age=604800",
        "font/*": "max-age=604800",
        "default": "max-age=86400",
    },
)

WAGTAIL_LMS_REDIRECT_MEDIA = getattr(settings, "WAGTAIL_LMS_REDIRECT_MEDIA", False)
