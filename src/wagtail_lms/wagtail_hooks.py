from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks

from .viewsets import LMSViewSetGroup


@hooks.register("register_admin_viewset")
def register_lms_viewset():
    return LMSViewSetGroup()


# Add custom CSS/JS for SCORM player
@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html(
        '<link rel="stylesheet" href="{}">',
        static("wagtail_lms/css/scorm-admin.css"),
    )


@hooks.register("insert_global_admin_js")
def global_admin_js():
    return format_html(
        '<script src="{}"></script>', static("wagtail_lms/js/scorm-admin.js")
    )
