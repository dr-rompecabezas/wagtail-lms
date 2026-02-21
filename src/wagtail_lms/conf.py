"""Default settings for wagtail-lms"""

import warnings

from django.conf import settings

WAGTAIL_LMS_AUTO_ENROLL = getattr(settings, "WAGTAIL_LMS_AUTO_ENROLL", False)

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

WAGTAIL_LMS_SCORM_UPLOAD_PATH = getattr(
    settings, "WAGTAIL_LMS_SCORM_UPLOAD_PATH", "scorm_packages/"
)

_old_scorm_content_path = getattr(settings, "WAGTAIL_LMS_CONTENT_PATH", None)
_new_scorm_content_path = getattr(settings, "WAGTAIL_LMS_SCORM_CONTENT_PATH", None)

if _old_scorm_content_path is not None and _new_scorm_content_path is None:
    warnings.warn(
        "WAGTAIL_LMS_CONTENT_PATH is deprecated and will be removed in a future version. "
        "Rename it to WAGTAIL_LMS_SCORM_CONTENT_PATH in your Django settings.",
        DeprecationWarning,
        stacklevel=2,
    )

WAGTAIL_LMS_SCORM_CONTENT_PATH = (
    _new_scorm_content_path
    if _new_scorm_content_path is not None
    else (
        _old_scorm_content_path
        if _old_scorm_content_path is not None
        else "scorm_content/"
    )
)

# Keep the old name accessible for any downstream code that imports it from conf directly.
WAGTAIL_LMS_CONTENT_PATH = WAGTAIL_LMS_SCORM_CONTENT_PATH

WAGTAIL_LMS_H5P_UPLOAD_PATH = getattr(
    settings, "WAGTAIL_LMS_H5P_UPLOAD_PATH", "h5p_packages/"
)

WAGTAIL_LMS_H5P_CONTENT_PATH = getattr(
    settings, "WAGTAIL_LMS_H5P_CONTENT_PATH", "h5p_content/"
)
