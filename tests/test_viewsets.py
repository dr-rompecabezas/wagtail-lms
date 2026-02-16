"""Tests for Wagtail admin viewsets."""

import pytest
from wagtail import hooks

from wagtail_lms.models import SCORMAttempt
from wagtail_lms.viewsets import (
    CourseEnrollmentViewSet,
    LMSViewSetGroup,
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
    """Verify enrollment management works in Wagtail admin."""

    def test_list_view(self, client, superuser):
        client.force_login(superuser)
        response = client.get("/admin/courseenrollment/")
        assert response.status_code == 200


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
        assert "Why not" not in content
        assert "/admin/scormattempt/new/" not in content
