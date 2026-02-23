"""Django system checks for wagtail-lms."""

from django.core.checks import Warning, register


@register()
def check_coursepage_subclass_subpage_types(app_configs, **kwargs):
    """Warn when a CoursePage subclass omits lesson page types from subpage_types.

    When a downstream project subclasses CoursePage and overrides
    subpage_types without including the lesson page types, Wagtail will
    silently hide the "Add child page" option. Lessons become completely
    inaccessible with no error message.

    W001: H5PLessonPage missing from subpage_types
    W002: SCORMLessonPage missing from subpage_types

    This check fires at startup so the problem surfaces immediately rather
    than silently at edit time.
    """
    from django.apps import apps

    from .models import CoursePage

    errors = []
    for model in apps.get_models():
        if model is CoursePage:
            continue
        if not issubclass(model, CoursePage):
            continue
        subpage_types = model.__dict__.get("subpage_types")
        if subpage_types is None:
            continue
        if "wagtail_lms.H5PLessonPage" not in subpage_types:
            errors.append(
                Warning(
                    f"{model.__name__} subclasses CoursePage but its "
                    f"subpage_types does not include 'wagtail_lms.H5PLessonPage'. "
                    f"H5P lessons cannot be added to this page type.",
                    hint=(
                        "Add 'wagtail_lms.H5PLessonPage' to "
                        f"{model.__name__}.subpage_types to enable H5P lessons."
                    ),
                    obj=model,
                    id="wagtail_lms.W001",
                )
            )
        if "wagtail_lms.SCORMLessonPage" not in subpage_types:
            errors.append(
                Warning(
                    f"{model.__name__} subclasses CoursePage but its "
                    f"subpage_types does not include 'wagtail_lms.SCORMLessonPage'. "
                    f"SCORM lessons cannot be added to this page type.",
                    hint=(
                        "Add 'wagtail_lms.SCORMLessonPage' to "
                        f"{model.__name__}.subpage_types to enable SCORM lessons."
                    ),
                    obj=model,
                    id="wagtail_lms.W002",
                )
            )
    return errors
