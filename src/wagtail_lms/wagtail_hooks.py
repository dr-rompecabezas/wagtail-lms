from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.menu import MenuItem


@hooks.register("register_admin_menu_item")
def register_scorm_menu_item():
    return MenuItem(
        "SCORM Packages", "/lms/scorm-packages/", icon_name="doc-full", order=1000
    )


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
