"""Tests for Wagtail admin viewsets."""

import pytest
from wagtail import hooks

from wagtail_lms.models import SCORMAttempt
from wagtail_lms.viewsets import (
    CourseEnrollmentViewSet,
    H5PAttemptViewSet,
    H5PLessonCompletionViewSet,
    LMSViewSetGroup,
    ReadOnlyPermissionPolicy,
    SCORMAttemptViewSet,
    SCORMPackageViewSet,
)


class TestViewSetRegistration:
    """Verify viewsets are properly registered with Wagtail."""

    def test_lms_viewset_group_is_registered(self):
        registered = hooks.get_hooks("register_admin_viewset")
        viewset_results = [hook() for hook in registered]
        assert any(isinstance(vs, LMSViewSetGroup) for vs in viewset_results), (
            "LMSViewSetGroup not found in registered admin viewsets"
        )

    def test_group_contains_all_three_viewsets(self):
        group = LMSViewSetGroup()
        item_classes = {type(item) for item in group.registerables}
        assert SCORMPackageViewSet in item_classes
        assert CourseEnrollmentViewSet in item_classes
        assert SCORMAttemptViewSet in item_classes


@pytest.mark.django_db
class TestSCORMPackageAdmin:
    """Verify SCORM package CRUD works in Wagtail admin."""

    def test_list_view(self, client, superuser):
        client.force_login(superuser)
        response = client.get("/admin/scormpackage/")
        assert response.status_code == 200

    def test_create_view(self, client, superuser):
        client.force_login(superuser)
        response = client.get("/admin/scormpackage/new/")
        assert response.status_code == 200

    def test_edit_view(self, client, superuser, scorm_package):
        client.force_login(superuser)
        response = client.get(f"/admin/scormpackage/edit/{scorm_package.pk}/")
        assert response.status_code == 200

    def test_requires_authentication(self, client):
        response = client.get("/admin/scormpackage/")
        assert response.status_code == 302


@pytest.mark.django_db
class TestCourseEnrollmentAdmin:
    """Verify enrollment management is edit-only (no add/delete)."""

    def test_list_view(self, client, superuser):
        client.force_login(superuser)
        response = client.get("/admin/courseenrollment/")
        assert response.status_code == 200

    def test_add_is_blocked(self, client, superuser):
        """Enrollments are created through the enrollment workflow."""
        client.force_login(superuser)
        response = client.get("/admin/courseenrollment/new/")
        assert response.status_code == 302

    def test_list_view_has_no_add_button(self, client, superuser):
        client.force_login(superuser)
        response = client.get("/admin/courseenrollment/")
        content = response.content.decode()
        assert "/admin/courseenrollment/new/" not in content


@pytest.mark.django_db
class TestSCORMAttemptAdmin:
    """Verify attempt viewset is inspect-only."""

    def test_list_view(self, client, superuser):
        client.force_login(superuser)
        response = client.get("/admin/scormattempt/")
        assert response.status_code == 200

    def test_inspect_view(self, client, superuser, user, scorm_package):
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        client.force_login(superuser)
        response = client.get(f"/admin/scormattempt/inspect/{attempt.pk}/")
        assert response.status_code == 200

    def test_add_is_blocked(self, client, superuser):
        """Attempts are auto-created by the SCORM player, not manually."""
        client.force_login(superuser)
        response = client.get("/admin/scormattempt/new/")
        assert response.status_code == 302

    def test_list_view_has_no_add_button(self, client, superuser):
        client.force_login(superuser)
        response = client.get("/admin/scormattempt/")
        content = response.content.decode()
        assert "/admin/scormattempt/new/" not in content


@pytest.mark.django_db
class TestReadOnlyPermissionPolicyMenuVisibility:
    """ReadOnlyPermissionPolicy must not hide menu items for users who can view.

    Wagtail's menu-visibility check calls user_has_any_permission with
    ['add', 'change', 'delete'].  Without the user_has_any_permission override,
    the policy returns False for all three actions (even for superusers), and
    Wagtail hides the menu item entirely.  Regression test for the bug where
    SCORM Attempts, H5P Attempts, and H5P Lesson Completions were invisible in
    the Wagtail admin sidebar.
    """

    def _superuser_sees_menu_item(self, viewset_class, superuser):
        policy = viewset_class.permission_policy
        return policy.user_has_any_permission(superuser, ["add", "change", "delete"])

    def test_scorm_attempts_visible_to_superuser(self, superuser):
        assert self._superuser_sees_menu_item(SCORMAttemptViewSet, superuser)

    def test_h5p_attempts_visible_to_superuser(self, superuser):
        assert self._superuser_sees_menu_item(H5PAttemptViewSet, superuser)

    def test_h5p_lesson_completions_visible_to_superuser(self, superuser):
        assert self._superuser_sees_menu_item(H5PLessonCompletionViewSet, superuser)

    def test_add_still_blocked_for_superuser(self, superuser):
        policy = ReadOnlyPermissionPolicy(SCORMAttempt)
        assert not policy.user_has_permission(superuser, "add")

    def test_change_still_blocked_for_superuser(self, superuser):
        policy = ReadOnlyPermissionPolicy(SCORMAttempt)
        assert not policy.user_has_permission(superuser, "change")

    def test_delete_still_blocked_for_superuser(self, superuser):
        policy = ReadOnlyPermissionPolicy(SCORMAttempt)
        assert not policy.user_has_permission(superuser, "delete")
