from wagtail.admin.viewsets.model import ModelViewSet, ModelViewSetGroup
from wagtail.permission_policies import ModelPermissionPolicy

from .models import (
    CourseEnrollment,
    H5PActivity,
    H5PAttempt,
    SCORMAttempt,
    SCORMPackage,
)


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


class SCORMPackageViewSet(ModelViewSet):
    model = SCORMPackage
    icon = "upload"
    add_to_admin_menu = False
    menu_label = "SCORM Packages"
    menu_icon = "upload"
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


class LMSViewSetGroup(ModelViewSetGroup):
    menu_label = "LMS"
    menu_icon = "glasses"
    items = (
        SCORMPackageViewSet,
        H5PActivityViewSet,
        CourseEnrollmentViewSet,
        SCORMAttemptViewSet,
        H5PAttemptViewSet,
    )
