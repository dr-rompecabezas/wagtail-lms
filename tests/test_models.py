"""Tests for wagtail-lms models."""

import os

import pytest
from django.db import IntegrityError

from wagtail_lms.models import (
    CourseEnrollment,
    CoursePage,
    SCORMAttempt,
    SCORMData,
    SCORMPackage,
)


@pytest.mark.django_db
class TestSCORMPackage:
    """Tests for SCORMPackage model."""

    def test_create_scorm_package(self):
        """Test basic SCORM package creation."""
        package = SCORMPackage.objects.create(
            title="Test Package",
            description="Test Description",
            version="1.2",
        )
        assert package.title == "Test Package"
        assert package.description == "Test Description"
        assert package.version == "1.2"
        assert str(package) == "Test Package"

    def test_scorm_package_with_file(self, scorm_package):
        """Test SCORM package with uploaded file and extraction."""
        assert scorm_package.title == "Test SCORM Package"
        assert scorm_package.package_file is not None
        # After save, package should be extracted
        assert scorm_package.extracted_path != ""

    def test_scorm_package_extraction(self, scorm_package, settings):
        """Test that SCORM package extraction creates files."""
        # Check that extracted path is set
        assert scorm_package.extracted_path
        # Check that manifest was parsed
        assert scorm_package.launch_url == "index.html"

    def test_scorm_package_launch_url(self, scorm_package):
        """Test get_launch_url method."""
        launch_url = scorm_package.get_launch_url()
        assert launch_url is not None
        assert "/lms/scorm-content/" in launch_url
        assert scorm_package.extracted_path in launch_url
        assert scorm_package.launch_url in launch_url

    def test_scorm_package_manifest_parsing(self, scorm_package):
        """Test manifest data parsing."""
        assert scorm_package.manifest_data is not None
        assert "launch_url" in scorm_package.manifest_data
        assert scorm_package.manifest_data["launch_url"] == "index.html"

    def test_scorm_version_detection_12(self, scorm_package):
        """Test SCORM 1.2 version detection."""
        assert scorm_package.version == "1.2"

    def test_scorm_version_detection_2004(
        self, scorm_2004_zip_file, settings, tmp_path
    ):
        """Test SCORM 2004 version detection."""
        settings.MEDIA_ROOT = str(tmp_path / "media")
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        package = SCORMPackage(
            title="Test SCORM 2004",
            package_file=scorm_2004_zip_file,
        )
        package.save()
        # Version should be detected from manifest
        assert "2004" in package.manifest_data.get("version", "")


@pytest.mark.django_db
class TestCoursePage:
    """Tests for CoursePage model."""

    def test_course_page_creation(self, course_page):
        """Test basic course page creation."""
        assert course_page.title == "Test Course"
        assert course_page.scorm_package is not None

    def test_course_page_get_context_authenticated(self, course_page, user, rf):
        """Test get_context with authenticated user."""
        request = rf.get("/")
        request.user = user

        context = course_page.get_context(request)

        assert "enrollment" in context
        assert "progress" in context
        # User not enrolled yet, should be None
        assert context["enrollment"] is None
        assert context["progress"] is None

    def test_course_page_get_context_with_enrollment(self, course_page, user, rf):
        """Test get_context with enrolled user."""
        # Create enrollment
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)

        request = rf.get("/")
        request.user = user

        context = course_page.get_context(request)

        assert context["enrollment"] == enrollment
        assert context["progress"] is None  # No SCORM attempt yet

    def test_course_page_get_context_unauthenticated(self, course_page, rf):
        """Test get_context with anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        request = rf.get("/")
        request.user = AnonymousUser()

        context = course_page.get_context(request)

        assert context["enrollment"] is None
        assert context["progress"] is None

    def test_course_page_preview_no_pk(self, home_page, scorm_package, rf):
        """Test get_context for unsaved page (preview mode)."""
        from django.contrib.auth.models import AnonymousUser

        # Create unsaved page (no pk)
        course = CoursePage(
            title="Unsaved Course",
            scorm_package=scorm_package,
        )
        # Don't add to tree, keep pk as None

        request = rf.get("/")
        request.user = AnonymousUser()

        # Should not raise error even without pk
        context = course.get_context(request)
        assert context["enrollment"] is None
        assert context["progress"] is None


@pytest.mark.django_db
class TestCourseEnrollment:
    """Tests for CourseEnrollment model."""

    def test_enrollment_creation(self, user, course_page):
        """Test basic enrollment creation."""
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)
        assert enrollment.user == user
        assert enrollment.course == course_page
        assert enrollment.enrolled_at is not None
        assert enrollment.completed_at is None
        assert str(enrollment) == f"{user.username} - {course_page.title}"

    def test_enrollment_unique_constraint(self, user, course_page):
        """Test that user can only enroll once per course."""
        CourseEnrollment.objects.create(user=user, course=course_page)

        # Trying to create duplicate should raise IntegrityError
        with pytest.raises(IntegrityError):
            CourseEnrollment.objects.create(user=user, course=course_page)

    def test_enrollment_get_progress_no_attempt(self, user, course_page):
        """Test get_progress with no SCORM attempt."""
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)
        progress = enrollment.get_progress()
        assert progress is None

    def test_enrollment_get_progress_with_attempt(
        self, user, course_page, scorm_package
    ):
        """Test get_progress with SCORM attempt."""
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)
        attempt = SCORMAttempt.objects.create(
            user=user,
            scorm_package=scorm_package,
            completion_status="incomplete",
        )
        progress = enrollment.get_progress()
        assert progress == attempt

    def test_enrollment_get_progress_no_package(self, user, home_page):
        """Test get_progress when course has no SCORM package."""
        course = CoursePage(
            title="Course Without Package",
            slug="no-package",
        )
        home_page.add_child(instance=course)

        enrollment = CourseEnrollment.objects.create(user=user, course=course)
        progress = enrollment.get_progress()
        assert progress is None


@pytest.mark.django_db
class TestSCORMAttempt:
    """Tests for SCORMAttempt model."""

    def test_attempt_creation(self, user, scorm_package):
        """Test basic SCORM attempt creation."""
        attempt = SCORMAttempt.objects.create(
            user=user,
            scorm_package=scorm_package,
            completion_status="incomplete",
        )
        assert attempt.user == user
        assert attempt.scorm_package == scorm_package
        assert attempt.completion_status == "incomplete"
        assert attempt.success_status == "unknown"
        assert attempt.started_at is not None
        assert str(attempt) == f"{user.username} - {scorm_package.title} (incomplete)"

    def test_attempt_score_fields(self, user, scorm_package):
        """Test SCORM attempt score tracking."""
        attempt = SCORMAttempt.objects.create(
            user=user,
            scorm_package=scorm_package,
            score_raw=85.0,
            score_min=0.0,
            score_max=100.0,
            score_scaled=0.85,
        )
        assert attempt.score_raw == 85.0
        assert attempt.score_min == 0.0
        assert attempt.score_max == 100.0
        assert attempt.score_scaled == 0.85

    def test_attempt_completion_statuses(self, user, scorm_package):
        """Test different completion statuses."""
        statuses = ["incomplete", "completed", "not_attempted", "unknown"]
        for status in statuses:
            attempt = SCORMAttempt.objects.create(
                user=user, scorm_package=scorm_package, completion_status=status
            )
            assert attempt.completion_status == status

    def test_attempt_success_statuses(self, user, scorm_package):
        """Test different success statuses."""
        statuses = ["passed", "failed", "unknown"]
        for status in statuses:
            attempt = SCORMAttempt.objects.create(
                user=user, scorm_package=scorm_package, success_status=status
            )
            assert attempt.success_status == status

    def test_attempt_suspend_data(self, user, scorm_package):
        """Test suspend data storage."""
        attempt = SCORMAttempt.objects.create(
            user=user,
            scorm_package=scorm_package,
            suspend_data="bookmark:page5",
        )
        assert attempt.suspend_data == "bookmark:page5"


@pytest.mark.django_db
class TestSCORMData:
    """Tests for SCORMData model."""

    def test_scorm_data_creation(self, user, scorm_package):
        """Test basic SCORM data creation."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        data = SCORMData.objects.create(
            attempt=attempt, key="cmi.core.lesson_status", value="incomplete"
        )
        assert data.attempt == attempt
        assert data.key == "cmi.core.lesson_status"
        assert data.value == "incomplete"
        assert data.timestamp is not None

    def test_scorm_data_unique_constraint(self, user, scorm_package):
        """Test unique constraint on attempt+key."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        SCORMData.objects.create(
            attempt=attempt, key="cmi.core.lesson_status", value="incomplete"
        )

        # Trying to create duplicate should raise IntegrityError
        with pytest.raises(IntegrityError):
            SCORMData.objects.create(
                attempt=attempt, key="cmi.core.lesson_status", value="completed"
            )

    def test_scorm_data_update_or_create(self, user, scorm_package):
        """Test updating existing SCORM data."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        # Create initial data
        data, created = SCORMData.objects.update_or_create(
            attempt=attempt,
            key="cmi.core.lesson_status",
            defaults={"value": "incomplete"},
        )
        assert created
        assert data.value == "incomplete"

        # Update existing data
        data, created = SCORMData.objects.update_or_create(
            attempt=attempt,
            key="cmi.core.lesson_status",
            defaults={"value": "completed"},
        )
        assert not created
        assert data.value == "completed"

    def test_scorm_data_string_representation(self, user, scorm_package):
        """Test SCORM data string representation."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        data = SCORMData.objects.create(
            attempt=attempt,
            key="cmi.suspend_data",
            value="x" * 100,  # Long value
        )
        # Should truncate to 50 characters
        assert len(str(data)) < 150  # Some extra for attempt info
        assert "cmi.suspend_data" in str(data)
