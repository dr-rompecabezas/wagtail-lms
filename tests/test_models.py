"""Tests for wagtail-lms models."""

import io
import os

import pytest
from django.core.files.storage import default_storage
from django.db import IntegrityError

from wagtail_lms import conf
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

    def test_course_page_get_context_authenticated(self, course_page, user, rf):
        """Test get_context with authenticated user."""
        request = rf.get("/")
        request.user = user

        context = course_page.get_context(request)

        assert "enrollment" in context
        # User not enrolled yet, should be None
        assert context["enrollment"] is None

    def test_course_page_get_context_with_enrollment(self, course_page, user, rf):
        """Test get_context with enrolled user."""
        # Create enrollment
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)

        request = rf.get("/")
        request.user = user

        context = course_page.get_context(request)

        assert context["enrollment"] == enrollment

    def test_course_page_get_context_unauthenticated(self, course_page, rf):
        """Test get_context with anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        request = rf.get("/")
        request.user = AnonymousUser()

        context = course_page.get_context(request)

        assert context["enrollment"] is None

    def test_course_page_preview_no_pk(self, home_page, rf):
        """Test get_context for unsaved page (preview mode)."""
        from django.contrib.auth.models import AnonymousUser

        # Create unsaved page (no pk)
        course = CoursePage(
            title="Unsaved Course",
        )
        # Don't add to tree, keep pk as None

        request = rf.get("/")
        request.user = AnonymousUser()

        # Should not raise error even without pk
        context = course.get_context(request)
        assert context["enrollment"] is None

    def test_get_context_includes_lesson_pages(self, course_page, user, rf):
        """lesson_pages in context contains live H5PLessonPage children."""
        from wagtail_lms.models import H5PLessonPage

        lesson = H5PLessonPage(title="Lesson One", slug="lesson-one", intro="")
        course_page.add_child(instance=lesson)
        lesson.save_revision().publish()

        request = rf.get("/")
        request.user = user
        context = course_page.get_context(request)

        assert "lesson_pages" in context
        assert lesson.pk in [p.pk for p in context["lesson_pages"]]

    def test_get_context_excludes_draft_lesson_pages(self, course_page, user, rf):
        """Draft H5PLessonPage children are not included in lesson_pages."""
        from wagtail_lms.models import H5PLessonPage

        draft = H5PLessonPage(
            title="Draft Lesson", slug="draft-lesson", intro="", live=False
        )
        course_page.add_child(instance=draft)

        request = rf.get("/")
        request.user = user
        context = course_page.get_context(request)

        assert draft.pk not in [p.pk for p in context["lesson_pages"]]

    def test_get_context_lesson_pages_empty_in_preview(self, home_page, rf):
        """lesson_pages is empty (not an error) when the page has no pk."""
        from django.contrib.auth.models import AnonymousUser

        course = CoursePage(title="Preview Course")
        request = rf.get("/")
        request.user = AnonymousUser()

        context = course.get_context(request)

        assert "lesson_pages" in context
        assert len(list(context["lesson_pages"])) == 0


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
        from django.db import transaction

        CourseEnrollment.objects.create(user=user, course=course_page)

        # Trying to create duplicate should raise IntegrityError
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CourseEnrollment.objects.create(user=user, course=course_page)


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
        from django.db import transaction

        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        SCORMData.objects.create(
            attempt=attempt, key="cmi.core.lesson_status", value="incomplete"
        )

        # Trying to create duplicate should raise IntegrityError
        with pytest.raises(IntegrityError):
            with transaction.atomic():
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


@pytest.mark.django_db
class TestSCORMPackageStorageBackend:
    """Tests for SCORM extraction using Django's storage API."""

    def test_extract_uses_storage_api(self, scorm_package):
        """Verify extracted files are accessible via default_storage."""
        content_path = conf.WAGTAIL_LMS_SCORM_CONTENT_PATH.rstrip("/")
        storage_path = f"{content_path}/{scorm_package.extracted_path}/index.html"
        assert default_storage.exists(storage_path)

    def test_extract_with_in_memory_storage(self, mock_s3_storage, scorm_zip_file, db):
        """Confirm extraction works when .path is unavailable (simulates S3)."""
        package = SCORMPackage(
            title="S3 Test Package",
            package_file=scorm_zip_file,
        )
        package.save()

        assert package.extracted_path != ""
        content_path = conf.WAGTAIL_LMS_SCORM_CONTENT_PATH.rstrip("/")
        storage_path = f"{content_path}/{package.extracted_path}/index.html"
        assert default_storage.exists(storage_path)
        assert package.launch_url == "index.html"

    def test_extract_rejects_path_traversal(
        self, scorm_zip_with_traversal, settings, tmp_path, db
    ):
        """Verify malicious ZIP paths are skipped, safe files are extracted."""
        settings.MEDIA_ROOT = str(tmp_path / "media")
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        package = SCORMPackage(
            title="Traversal Test",
            package_file=scorm_zip_with_traversal,
        )
        package.save()

        # Safe files should be extracted
        content_path = conf.WAGTAIL_LMS_SCORM_CONTENT_PATH.rstrip("/")
        safe_path = f"{content_path}/{package.extracted_path}/index.html"
        assert default_storage.exists(safe_path)

        # Malicious entries should NOT have been written to the filesystem
        # (check at the tmp_path level where traversal paths would land)
        assert not os.path.exists(tmp_path / "etc" / "passwd")
        assert not os.path.exists(tmp_path / "etc" / "shadow")

    def test_parse_manifest_accepts_file_object(self):
        """parse_manifest() should accept a file-like object."""
        manifest_xml = b"""<?xml version="1.0"?>
<manifest identifier="test" version="1.0"
    xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2">
    <organizations default="org1">
        <organization identifier="org1">
            <title>File Object Test</title>
        </organization>
    </organizations>
    <resources>
        <resource identifier="r1" type="webcontent" href="start.html">
            <file href="start.html"/>
        </resource>
    </resources>
</manifest>"""

        package = SCORMPackage(title="Manifest Test")
        package.parse_manifest(io.BytesIO(manifest_xml))

        assert package.launch_url == "start.html"
        assert package.manifest_data["title"] == "File Object Test"

    def test_parse_manifest_still_accepts_file_path(self, scorm_12_manifest, tmp_path):
        """parse_manifest() should still accept a string file path."""
        manifest_file = tmp_path / "imsmanifest.xml"
        manifest_file.write_text(scorm_12_manifest)

        package = SCORMPackage(title="Path Test")
        package.parse_manifest(str(manifest_file))

        assert package.launch_url == "index.html"
        assert package.manifest_data["title"] == "Test SCORM Course"
