from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.module_loading import import_string
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from . import conf
from .models import H5PActivity
from .viewsets import LMSViewSetGroup


def _import_snippet_viewset_class(dotted_path, setting_name):
    try:
        viewset_class = import_string(dotted_path)
    except (ImportError, AttributeError) as exc:
        raise ImportError(
            f"Could not import '{dotted_path}' from {setting_name}"
        ) from exc

    if not issubclass(viewset_class, SnippetViewSet):
        raise TypeError(
            f"{setting_name} must reference a SnippetViewSet subclass; "
            f"got '{dotted_path}'"
        )
    return viewset_class


register_snippet(
    H5PActivity,
    viewset=_import_snippet_viewset_class(
        conf.WAGTAIL_LMS_H5P_SNIPPET_VIEWSET_CLASS,
        "WAGTAIL_LMS_H5P_SNIPPET_VIEWSET_CLASS",
    ),
)

# Backward-compatible alias for downstream projects that previously patched this
# object in AppConfig.ready() before v0.10.0 settings hooks were added.
lms_viewset_group = LMSViewSetGroup()


@hooks.register("register_admin_viewset")
def register_lms_viewset():
    return lms_viewset_group


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
