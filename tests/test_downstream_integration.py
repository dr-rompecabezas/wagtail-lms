"""Tests for downstream integration extension points."""

import pytest
from django.contrib import admin
from django.contrib.admin import AdminSite
from wagtail.snippets.models import get_snippet_models

from wagtail_lms import admin as wagtail_lms_admin
from wagtail_lms import conf
from wagtail_lms import models as wagtail_lms_models
from wagtail_lms.models import CourseEnrollment, H5PActivity, LessonPage, SCORMPackage
from wagtail_lms.viewsets import (
    H5PActivityViewSet,
    LMSViewSetGroup,
    SCORMPackageViewSet,
)

ACCESS_CHECK_CALLS = []


def allow_all_lesson_access(request, lesson_page, course_page):
    """Test access hook that allows access and records calls."""
    ACCESS_CHECK_CALLS.append((request.user.pk, lesson_page.pk, course_page.pk))
    return True


class CustomSCORMPackageViewSet(SCORMPackageViewSet):
    pass


class CustomH5PActivityViewSet(H5PActivityViewSet):
    pass


class CustomSCORMPackageAdmin(admin.ModelAdmin):
    pass


class CustomH5PActivityAdmin(admin.ModelAdmin):
    pass


@pytest.fixture
def lesson_page_for_access(course_page):
    lesson = LessonPage(
        title="Hooked Lesson",
        slug="hooked-lesson",
        intro="<p>Access hook test.</p>",
    )
    course_page.add_child(instance=lesson)
    lesson.save_revision().publish()
    return lesson


@pytest.mark.django_db
def test_lesson_parent_page_types_is_unrestricted():
    assert LessonPage.parent_page_types is None


@pytest.mark.django_db
def test_custom_lesson_access_hook_is_used(
    client, user, lesson_page_for_access, monkeypatch
):
    ACCESS_CHECK_CALLS.clear()
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_CHECK_LESSON_ACCESS",
        "tests.test_downstream_integration.allow_all_lesson_access",
    )

    client.force_login(user)
    response = client.get(lesson_page_for_access.url)

    assert response.status_code == 200
    assert ACCESS_CHECK_CALLS


@pytest.mark.django_db
def test_default_lesson_access_path_skips_import_string(
    client, user, lesson_page_for_access, course_page, monkeypatch
):
    CourseEnrollment.objects.create(user=user, course=course_page)
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_CHECK_LESSON_ACCESS",
        "wagtail_lms.access.default_lesson_access_check",
    )

    def _should_not_import(_dotted_path):
        raise AssertionError("import_string should not be called on default path")

    monkeypatch.setattr(wagtail_lms_models, "import_string", _should_not_import)
    client.force_login(user)
    response = client.get(lesson_page_for_access.url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_custom_lesson_access_callable_import_is_cached(
    client, user, lesson_page_for_access, monkeypatch
):
    ACCESS_CHECK_CALLS.clear()
    wagtail_lms_models._get_lesson_access_check.cache_clear()
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_CHECK_LESSON_ACCESS",
        "tests.test_downstream_integration.allow_all_lesson_access",
    )
    import_count = 0

    def _counting_import(_dotted_path):
        nonlocal import_count
        import_count += 1
        return allow_all_lesson_access

    monkeypatch.setattr(wagtail_lms_models, "import_string", _counting_import)
    client.force_login(user)
    first = client.get(lesson_page_for_access.url)
    second = client.get(lesson_page_for_access.url)

    assert first.status_code == 200
    assert second.status_code == 200
    assert import_count == 1
    wagtail_lms_models._get_lesson_access_check.cache_clear()


def test_lms_viewset_group_uses_configurable_viewset_classes(monkeypatch):
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_SCORM_PACKAGE_VIEWSET_CLASS",
        "tests.test_downstream_integration.CustomSCORMPackageViewSet",
    )
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_H5P_ACTIVITY_VIEWSET_CLASS",
        "tests.test_downstream_integration.CustomH5PActivityViewSet",
    )

    group = LMSViewSetGroup()

    assert isinstance(group.registerables[0], CustomSCORMPackageViewSet)
    assert isinstance(group.registerables[1], CustomH5PActivityViewSet)


def test_lms_viewset_group_invalid_dotted_path_includes_setting_name(monkeypatch):
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_SCORM_PACKAGE_VIEWSET_CLASS",
        "tests.missing.DoesNotExist",
    )
    with pytest.raises(ImportError, match="WAGTAIL_LMS_SCORM_PACKAGE_VIEWSET_CLASS"):
        LMSViewSetGroup()


def test_h5p_snippet_registration_uses_hidden_snippet_viewset():
    assert H5PActivity in get_snippet_models()
    assert H5PActivity.snippet_viewset.add_to_admin_menu is False
    assert H5PActivity.snippet_viewset.get_menu_item_is_registered() is True


def test_register_django_admin_can_be_disabled(monkeypatch):
    test_admin_site = AdminSite(name="test-admin")
    monkeypatch.setattr(wagtail_lms_admin.admin, "site", test_admin_site)
    monkeypatch.setattr(conf, "WAGTAIL_LMS_REGISTER_DJANGO_ADMIN", False)

    wagtail_lms_admin._register_django_admin()

    assert test_admin_site._registry == {}


def test_register_django_admin_uses_configured_classes(monkeypatch):
    test_admin_site = AdminSite(name="test-admin")
    monkeypatch.setattr(wagtail_lms_admin.admin, "site", test_admin_site)
    monkeypatch.setattr(conf, "WAGTAIL_LMS_REGISTER_DJANGO_ADMIN", True)
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_SCORM_ADMIN_CLASS",
        "tests.test_downstream_integration.CustomSCORMPackageAdmin",
    )
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_H5P_ADMIN_CLASS",
        "tests.test_downstream_integration.CustomH5PActivityAdmin",
    )

    wagtail_lms_admin._register_django_admin()

    assert isinstance(test_admin_site._registry[SCORMPackage], CustomSCORMPackageAdmin)
    assert isinstance(test_admin_site._registry[H5PActivity], CustomH5PActivityAdmin)


def test_register_django_admin_invalid_dotted_path_includes_setting_name(monkeypatch):
    test_admin_site = AdminSite(name="test-admin")
    monkeypatch.setattr(wagtail_lms_admin.admin, "site", test_admin_site)
    monkeypatch.setattr(conf, "WAGTAIL_LMS_REGISTER_DJANGO_ADMIN", True)
    monkeypatch.setattr(
        conf, "WAGTAIL_LMS_SCORM_ADMIN_CLASS", "tests.missing.DoesNotExist"
    )
    monkeypatch.setattr(
        conf,
        "WAGTAIL_LMS_H5P_ADMIN_CLASS",
        "wagtail_lms.admin.H5PActivityAdmin",
    )

    with pytest.raises(ImportError, match="WAGTAIL_LMS_SCORM_ADMIN_CLASS"):
        wagtail_lms_admin._register_django_admin()
