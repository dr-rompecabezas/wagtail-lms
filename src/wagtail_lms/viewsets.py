from django.utils.module_loading import import_string
from wagtail.admin.views.generic.models import IndexView, InspectView
from wagtail.admin.viewsets.model import ModelViewSet, ModelViewSetGroup
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.snippets.views.snippets import SnippetViewSet

from . import conf
from .models import (
    CourseEnrollment,
    H5PActivity,
    H5PAttempt,
    LessonCompletion,
    SCORMAttempt,
    SCORMPackage,
)


def _import_viewset_class(dotted_path):
    viewset_class = import_string(dotted_path)
    if not issubclass(viewset_class, ModelViewSet):
        raise TypeError(f"{dotted_path} is not a ModelViewSet subclass")
    return viewset_class


class ReadOnlyPermissionPolicy(ModelPermissionPolicy):
    """Permission policy that only allows view access."""

    def user_has_permission(self, user, action):
        if action in ("add", "change", "delete"):
            return False
        return super().user_has_permission(user, action)


class EditOnlyPermissionPolicy(ModelPermissionPolicy):
    """Permission policy that allows view and change but denies add and delete."""

    def user_has_permission(self, user, action):
        if action in ("add", "delete"):
            return False
        return super().user_has_permission(user, action)


class ViewPermissionIndexView(IndexView):
    any_permission_required = ["view"]


class ViewPermissionInspectView(InspectView):
    any_permission_required = ["view"]


class SCORMPackageViewSet(ModelViewSet):
    model = SCORMPackage
    icon = "media"
    add_to_admin_menu = False
    menu_label = "SCORM Packages"
    menu_icon = "media"
    list_display = ["title", "version", "created_at", "launch_url"]
    list_filter = ["version", "created_at"]
    search_fields = ["title", "description"]


class H5PActivityViewSet(ModelViewSet):
    model = H5PActivity
    icon = "media"
    add_to_admin_menu = False
    menu_label = "H5P Activities"
    menu_icon = "media"
    list_display = ["title", "main_library", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["title", "description", "main_library"]


class H5PActivitySnippetViewSet(SnippetViewSet):
    model = H5PActivity
    icon = "media"
    menu_label = "H5P Activities"
    menu_icon = "media"
    # Keep snippet chooser support but avoid a second admin menu path.
    add_to_admin_menu = False
    menu_item_is_registered = True
    list_display = ["title", "main_library", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["title", "description", "main_library"]


class CourseEnrollmentViewSet(ModelViewSet):
    model = CourseEnrollment
    icon = "group"
    add_to_admin_menu = False
    menu_label = "Enrollments"
    menu_icon = "group"
    list_display = ["user", "course", "enrolled_at", "completed_at"]
    list_filter = ["enrolled_at", "completed_at"]
    search_fields = ["user__username", "course__title"]
    permission_policy = EditOnlyPermissionPolicy(CourseEnrollment)


class SCORMAttemptViewSet(ModelViewSet):
    model = SCORMAttempt
    icon = "time"
    add_to_admin_menu = False
    menu_label = "SCORM Attempts"
    menu_icon = "time"
    index_view_class = ViewPermissionIndexView
    inspect_view_class = ViewPermissionInspectView
    inspect_view_enabled = True
    list_display = [
        "user",
        "scorm_package",
        "completion_status",
        "success_status",
        "started_at",
        "last_accessed",
    ]
    list_filter = ["completion_status", "success_status", "started_at"]
    search_fields = ["user__username", "scorm_package__title"]
    permission_policy = ReadOnlyPermissionPolicy(SCORMAttempt)


class H5PAttemptViewSet(ModelViewSet):
    model = H5PAttempt
    icon = "time"
    add_to_admin_menu = False
    menu_label = "H5P Attempts"
    menu_icon = "time"
    index_view_class = ViewPermissionIndexView
    inspect_view_class = ViewPermissionInspectView
    inspect_view_enabled = True
    list_display = [
        "user",
        "activity",
        "completion_status",
        "success_status",
        "started_at",
        "last_accessed",
    ]
    list_filter = ["completion_status", "success_status", "started_at"]
    search_fields = ["user__username", "activity__title"]
    permission_policy = ReadOnlyPermissionPolicy(H5PAttempt)


class LessonCompletionViewSet(ModelViewSet):
    model = LessonCompletion
    icon = "tick-inverse"
    add_to_admin_menu = False
    menu_label = "Lesson Completions"
    menu_icon = "tick-inverse"
    index_view_class = ViewPermissionIndexView
    list_display = ["user", "lesson", "completed_at"]
    list_filter = ["completed_at"]
    search_fields = ["user__username", "lesson__title"]
    permission_policy = ReadOnlyPermissionPolicy(LessonCompletion)


class LMSViewSetGroup(ModelViewSetGroup):
    menu_label = "LMS"
    menu_icon = "glasses"

    @property
    def items(self):
        return (
            _import_viewset_class(conf.WAGTAIL_LMS_SCORM_PACKAGE_VIEWSET_CLASS),
            _import_viewset_class(conf.WAGTAIL_LMS_H5P_ACTIVITY_VIEWSET_CLASS),
            CourseEnrollmentViewSet,
            SCORMAttemptViewSet,
            H5PAttemptViewSet,
            LessonCompletionViewSet,
        )
