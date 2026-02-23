"""Tests for wagtail-lms views."""

import json

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from wagtail_lms.models import CourseEnrollment, SCORMAttempt, SCORMData
from wagtail_lms.views import get_scorm_value, set_scorm_value


@pytest.mark.django_db
class TestSCORMPlayerView:
    """Tests for SCORM player view."""

    def test_scorm_player_requires_login(self, client, scorm_lesson_page):
        """Test that SCORM player requires authentication."""
        url = reverse("wagtail_lms:scorm_player", args=[scorm_lesson_page.id])
        response = client.get(url)
        # Should redirect to login
        assert response.status_code == 302
        assert "/admin/login/" in response.url or "/accounts/login/" in response.url

    def test_scorm_player_authenticated_enrolled(
        self, client, user, course_page, scorm_lesson_page
    ):
        """Test SCORM player with authenticated enrolled user."""
        CourseEnrollment.objects.create(user=user, course=course_page)
        client.force_login(user)
        url = reverse("wagtail_lms:scorm_player", args=[scorm_lesson_page.id])
        response = client.get(url)
        assert response.status_code == 200
        # The player displays the lesson title
        assert b"SCORM Lesson" in response.content

    def test_scorm_player_creates_enrollment_when_auto_enroll_enabled(
        self, client, user, course_page, scorm_lesson_page, monkeypatch
    ):
        """Test that auto-enroll creates enrollment when explicitly enabled."""
        from wagtail_lms import conf

        monkeypatch.setattr(conf, "WAGTAIL_LMS_AUTO_ENROLL", True)
        client.force_login(user)
        assert (
            CourseEnrollment.objects.filter(user=user, course=course_page).count() == 0
        )

        url = reverse("wagtail_lms:scorm_player", args=[scorm_lesson_page.id])
        client.get(url)

        assert (
            CourseEnrollment.objects.filter(user=user, course=course_page).count() == 1
        )

    def test_scorm_player_creates_attempt(
        self, client, user, course_page, scorm_package, scorm_lesson_page
    ):
        """Test that accessing player creates SCORM attempt."""
        CourseEnrollment.objects.create(user=user, course=course_page)
        client.force_login(user)
        assert (
            SCORMAttempt.objects.filter(user=user, scorm_package=scorm_package).count()
            == 0
        )

        url = reverse("wagtail_lms:scorm_player", args=[scorm_lesson_page.id])
        client.get(url)

        assert (
            SCORMAttempt.objects.filter(user=user, scorm_package=scorm_package).count()
            == 1
        )

    def test_scorm_player_without_package(self, client, user, home_page):
        """Test SCORM player for SCORMLessonPage without package."""
        from wagtail_lms.models import CoursePage, SCORMLessonPage

        course = CoursePage(title="No Package Course", slug="no-package")
        home_page.add_child(instance=course)
        course.save_revision().publish()

        lesson = SCORMLessonPage(title="Empty SCORM Lesson", slug="empty-scorm")
        course.add_child(instance=lesson)

        CourseEnrollment.objects.create(user=user, course=course)
        client.force_login(user)
        url = reverse("wagtail_lms:scorm_player", args=[lesson.id])
        response = client.get(url)

        # Should redirect with error message
        assert response.status_code == 302

    def test_scorm_player_default_redirects_unenrolled(
        self, client, user, course_page, scorm_lesson_page
    ):
        client.force_login(user)
        url = reverse("wagtail_lms:scorm_player", args=[scorm_lesson_page.id])
        response = client.get(url)
        assert response.status_code == 302
        assert (
            CourseEnrollment.objects.filter(user=user, course=course_page).count() == 0
        )

    def test_scorm_player_auto_enroll_false_allows_enrolled(
        self, client, user, course_page, scorm_lesson_page, monkeypatch
    ):
        from wagtail_lms import conf

        monkeypatch.setattr(conf, "WAGTAIL_LMS_AUTO_ENROLL", False)
        CourseEnrollment.objects.create(user=user, course=course_page)
        client.force_login(user)
        url = reverse("wagtail_lms:scorm_player", args=[scorm_lesson_page.id])
        response = client.get(url)
        assert response.status_code == 200

    def test_scorm_player_wagtail_editor_bypasses_enrollment(
        self, client, user, scorm_lesson_page
    ):
        """Wagtail editors can access the SCORM player without being enrolled,
        consistent with _lesson_serve behaviour for H5PLessonPage."""
        from django.contrib.auth.models import Permission

        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtailadmin", codename="access_admin"
            )
        )
        client.force_login(user)
        url = reverse("wagtail_lms:scorm_player", args=[scorm_lesson_page.id])
        response = client.get(url)
        assert response.status_code == 200
        assert not CourseEnrollment.objects.filter(user=user).exists()


@pytest.mark.django_db
class TestEnrollmentView:
    """Tests for enrollment view."""

    def test_enrollment_requires_login(self, client, course_page):
        """Test that enrollment requires authentication."""
        url = reverse("wagtail_lms:enroll_course", args=[course_page.id])
        response = client.get(url)
        # Should redirect to login
        assert response.status_code == 302

    def test_enrollment_creates_record(self, client, user, course_page):
        """Test that enrollment view creates enrollment record."""
        client.force_login(user)
        url = reverse("wagtail_lms:enroll_course", args=[course_page.id])
        response = client.get(url)

        # Should redirect to course page
        assert response.status_code == 302
        assert CourseEnrollment.objects.filter(user=user, course=course_page).exists()

    def test_enrollment_duplicate(self, client, user, course_page):
        """Test enrolling twice in same course."""
        client.force_login(user)
        CourseEnrollment.objects.create(user=user, course=course_page)

        url = reverse("wagtail_lms:enroll_course", args=[course_page.id])
        response = client.get(url)

        # Should still redirect successfully
        assert response.status_code == 302
        # Should only have one enrollment
        assert (
            CourseEnrollment.objects.filter(user=user, course=course_page).count() == 1
        )


@pytest.mark.django_db
class TestSCORMAPIEndpoint:
    """Tests for SCORM API endpoint."""

    def test_scorm_api_requires_login(self, client, user, scorm_package):
        """Test that SCORM API requires authentication."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url, json.dumps({"method": "Initialize"}), content_type="application/json"
        )
        # Should redirect to login
        assert response.status_code == 302

    def test_scorm_api_initialize(self, client, user, scorm_package):
        """Test SCORM Initialize method."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url,
            json.dumps({"method": "Initialize"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "true"
        assert data["errorCode"] == "0"

    def test_scorm_api_terminate(self, client, user, scorm_package):
        """Test SCORM Terminate method."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url,
            json.dumps({"method": "Terminate"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "true"
        assert data["errorCode"] == "0"

    def test_scorm_api_get_value(self, client, user, scorm_package):
        """Test SCORM GetValue method."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(
            user=user, scorm_package=scorm_package, completion_status="incomplete"
        )

        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url,
            json.dumps(
                {"method": "GetValue", "parameters": ["cmi.core.lesson_status"]}
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "incomplete"
        assert data["errorCode"] == "0"

    def test_scorm_api_set_value(self, client, user, scorm_package):
        """Test SCORM SetValue method."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url,
            json.dumps(
                {
                    "method": "SetValue",
                    "parameters": ["cmi.core.lesson_status", "completed"],
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "true"
        assert data["errorCode"] == "0"

        # Verify data was saved
        attempt.refresh_from_db()
        assert attempt.completion_status == "completed"

    def test_scorm_api_commit(self, client, user, scorm_package):
        """Test SCORM Commit method."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url,
            json.dumps({"method": "Commit"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "true"
        assert data["errorCode"] == "0"

    def test_scorm_api_get_last_error(self, client, user, scorm_package):
        """Test SCORM GetLastError method."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url,
            json.dumps({"method": "GetLastError"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "0"
        assert data["errorCode"] == "0"

    def test_scorm_api_invalid_method(self, client, user, scorm_package):
        """Test SCORM API with invalid method."""
        client.force_login(user)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url,
            json.dumps({"method": "InvalidMethod"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "false"
        assert data["errorCode"] == "201"

    def test_scorm_api_wrong_user(self, client, user, django_user_model, scorm_package):
        """Test SCORM API with different user."""
        other_user = django_user_model.objects.create_user(
            username="other", password="pass"
        )
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        client.force_login(other_user)
        url = reverse("wagtail_lms:scorm_api", args=[attempt.id])
        response = client.post(
            url,
            json.dumps({"method": "Initialize"}),
            content_type="application/json",
        )

        # Should return 404 since attempt doesn't belong to logged-in user
        assert response.status_code == 404


@pytest.mark.django_db
class TestSCORMDataHelpers:
    """Tests for SCORM data helper functions."""

    def test_get_scorm_value_default(self, user, scorm_package):
        """Test getting default SCORM values."""
        attempt = SCORMAttempt.objects.create(
            user=user, scorm_package=scorm_package, completion_status="incomplete"
        )
        value = get_scorm_value(attempt, "cmi.core.lesson_status")
        assert value == "incomplete"

    def test_get_scorm_value_student_id(self, user, scorm_package):
        """Test getting student ID."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        value = get_scorm_value(attempt, "cmi.core.student_id")
        assert value == str(user.id)

    def test_get_scorm_value_stored(self, user, scorm_package):
        """Test getting stored SCORM value."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        SCORMData.objects.create(
            attempt=attempt, key="cmi.suspend_data", value="bookmark:page5"
        )

        value = get_scorm_value(attempt, "cmi.suspend_data")
        assert value == "bookmark:page5"

    def test_set_scorm_value_lesson_status(self, user, scorm_package):
        """Test setting lesson status."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        set_scorm_value(attempt, "cmi.core.lesson_status", "completed")

        attempt.refresh_from_db()
        assert attempt.completion_status == "completed"

        # Should also be in SCORMData
        data = SCORMData.objects.get(attempt=attempt, key="cmi.core.lesson_status")
        assert data.value == "completed"

    def test_set_scorm_value_score(self, user, scorm_package):
        """Test setting score values."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        set_scorm_value(attempt, "cmi.core.score.raw", "85")
        set_scorm_value(attempt, "cmi.core.score.max", "100")
        set_scorm_value(attempt, "cmi.core.score.min", "0")

        attempt.refresh_from_db()
        assert attempt.score_raw == 85.0
        assert attempt.score_max == 100.0
        assert attempt.score_min == 0.0

    def test_set_scorm_value_location(self, user, scorm_package):
        """Test setting lesson location."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        set_scorm_value(attempt, "cmi.core.lesson_location", "page5")

        attempt.refresh_from_db()
        assert attempt.location == "page5"

    def test_set_scorm_value_suspend_data(self, user, scorm_package):
        """Test setting suspend data."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        set_scorm_value(attempt, "cmi.suspend_data", "progress:50%")

        attempt.refresh_from_db()
        assert attempt.suspend_data == "progress:50%"

    def test_set_scorm_value_custom(self, user, scorm_package):
        """Test setting custom SCORM data."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        set_scorm_value(attempt, "cmi.interactions.0.id", "question1")

        data = SCORMData.objects.get(attempt=attempt, key="cmi.interactions.0.id")
        assert data.value == "question1"

    def test_set_scorm_value_update(self, user, scorm_package):
        """Test updating existing SCORM value."""
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)

        # Set initial value
        set_scorm_value(attempt, "cmi.core.lesson_status", "incomplete")
        assert SCORMData.objects.filter(attempt=attempt).count() == 1

        # Update value
        set_scorm_value(attempt, "cmi.core.lesson_status", "completed")
        assert SCORMData.objects.filter(attempt=attempt).count() == 1

        data = SCORMData.objects.get(attempt=attempt, key="cmi.core.lesson_status")
        assert data.value == "completed"

    def test_set_lesson_status_completed_marks_enrollment(
        self, user, scorm_package, course_page, scorm_lesson_page
    ):
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        set_scorm_value(attempt, "cmi.core.lesson_status", "completed")
        enrollment.refresh_from_db()
        assert enrollment.completed_at is not None

    def test_set_lesson_status_passed_marks_enrollment(
        self, user, scorm_package, course_page, scorm_lesson_page
    ):
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        set_scorm_value(attempt, "cmi.core.lesson_status", "passed")
        enrollment.refresh_from_db()
        assert enrollment.completed_at is not None

    def test_set_lesson_status_incomplete_does_not_mark_enrollment(
        self, user, scorm_package, course_page, scorm_lesson_page
    ):
        enrollment = CourseEnrollment.objects.create(user=user, course=course_page)
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        set_scorm_value(attempt, "cmi.core.lesson_status", "incomplete")
        enrollment.refresh_from_db()
        assert enrollment.completed_at is None

    def test_set_lesson_status_completed_idempotent(
        self, user, scorm_package, course_page, scorm_lesson_page
    ):
        import datetime as dt

        original = timezone.now() - dt.timedelta(days=1)
        enrollment = CourseEnrollment.objects.create(
            user=user, course=course_page, completed_at=original
        )
        attempt = SCORMAttempt.objects.create(user=user, scorm_package=scorm_package)
        set_scorm_value(attempt, "cmi.core.lesson_status", "completed")
        enrollment.refresh_from_db()
        assert enrollment.completed_at == original  # not overwritten


@pytest.mark.django_db
class TestServeScormContent:
    """Tests for SCORM content serving view."""

    def test_serve_scorm_content_requires_login(self, client, scorm_package):
        """Test that content serving requires authentication."""
        url = reverse(
            "wagtail_lms:serve_scorm_content",
            args=[f"{scorm_package.extracted_path}/index.html"],
        )
        response = client.get(url)
        assert response.status_code == 302

    def test_serve_scorm_content_authenticated(self, client, user, scorm_package):
        """Test serving SCORM content to authenticated user."""
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_scorm_content",
            args=[f"{scorm_package.extracted_path}/index.html"],
        )
        response = client.get(url)

        assert response.status_code == 200
        assert response["X-Frame-Options"] == "SAMEORIGIN"
        # FileResponse uses streaming_content instead of content
        content = b"".join(response.streaming_content)
        assert b"Test Course" in content

    def test_serve_scorm_content_sets_cache_control(self, client, user, scorm_package):
        """Test default Cache-Control for HTML assets."""
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_scorm_content",
            args=[f"{scorm_package.extracted_path}/index.html"],
        )
        response = client.get(url)
        assert response.status_code == 200
        assert response["Cache-Control"] == "no-cache"

    def test_serve_scorm_content_wildcard_cache_control(
        self, client, user, scorm_package
    ):
        """Test wildcard MIME cache rules (image/*)."""
        from wagtail_lms import conf

        client.force_login(user)

        relative_path = f"{scorm_package.extracted_path}/logo.png"
        storage_path = (
            f"{conf.WAGTAIL_LMS_SCORM_CONTENT_PATH.rstrip('/')}/{relative_path}"
        )
        default_storage.save(storage_path, ContentFile(b"fake-image"))

        url = reverse("wagtail_lms:serve_scorm_content", args=[relative_path])
        response = client.get(url)
        assert response.status_code == 200
        assert response["Cache-Control"] == "max-age=604800"

    def test_serve_scorm_content_explicit_none_cache_rule(
        self, client, user, scorm_package, monkeypatch
    ):
        """Exact MIME None should disable header instead of falling back."""
        from wagtail_lms import conf

        client.force_login(user)
        monkeypatch.setattr(
            conf,
            "WAGTAIL_LMS_CACHE_CONTROL",
            {"text/html": None, "default": "max-age=86400"},
        )

        url = reverse(
            "wagtail_lms:serve_scorm_content",
            args=[f"{scorm_package.extracted_path}/index.html"],
        )
        response = client.get(url)

        assert response.status_code == 200
        assert "Cache-Control" not in response

    def test_serve_scorm_content_redirects_media_when_enabled(
        self, client, user, scorm_package, monkeypatch
    ):
        """Test opt-in redirect flow for media files."""
        from wagtail_lms import conf

        client.force_login(user)
        monkeypatch.setattr(conf, "WAGTAIL_LMS_REDIRECT_MEDIA", True)

        relative_path = f"{scorm_package.extracted_path}/lesson.mp4"
        storage_path = (
            f"{conf.WAGTAIL_LMS_SCORM_CONTENT_PATH.rstrip('/')}/{relative_path}"
        )
        default_storage.save(storage_path, ContentFile(b"fake-video"))

        url = reverse("wagtail_lms:serve_scorm_content", args=[relative_path])
        response = client.get(url)

        assert response.status_code == 302
        assert response["Location"] == default_storage.url(storage_path)

    def test_serve_scorm_content_redirect_url_error_returns_404(
        self, user, scorm_package, monkeypatch
    ):
        """Redirect path returns 404 when get_redirect_url() raises."""
        from wagtail_lms import conf
        from wagtail_lms.views import ServeScormContentView

        monkeypatch.setattr(conf, "WAGTAIL_LMS_REDIRECT_MEDIA", True)

        relative_path = f"{scorm_package.extracted_path}/lesson.mp4"

        class BrokenRedirectView(ServeScormContentView):
            def get_redirect_url(self, storage_path):
                raise RuntimeError("S3 credentials expired")

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user

        with pytest.raises(Http404):
            BrokenRedirectView.as_view()(request, content_path=relative_path)

    @pytest.mark.parametrize(
        "exc_class",
        [
            Http404,
            pytest.param(
                "PermissionDenied",
                id="PermissionDenied",
            ),
            pytest.param(
                "SuspiciousOperation",
                id="SuspiciousOperation",
            ),
        ],
    )
    def test_serve_scorm_content_redirect_preserves_django_exceptions(
        self, user, scorm_package, monkeypatch, exc_class
    ):
        """Intentional Django exceptions from get_redirect_url() propagate."""
        from django.core.exceptions import PermissionDenied, SuspiciousOperation

        from wagtail_lms import conf
        from wagtail_lms.views import ServeScormContentView

        exc_map = {
            "PermissionDenied": PermissionDenied,
            "SuspiciousOperation": SuspiciousOperation,
        }
        exc_class = exc_map.get(exc_class, exc_class)

        monkeypatch.setattr(conf, "WAGTAIL_LMS_REDIRECT_MEDIA", True)

        relative_path = f"{scorm_package.extracted_path}/lesson.mp4"

        class GuardedRedirectView(ServeScormContentView):
            def get_redirect_url(self, path):
                raise exc_class("denied")

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user

        with pytest.raises(exc_class):
            GuardedRedirectView.as_view()(request, content_path=relative_path)

    def test_serve_scorm_content_cbv_can_be_subclassed(self, user, scorm_package):
        """Test projects can override CBV hooks via subclassing."""
        from wagtail_lms.views import ServeScormContentView

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user

        class CustomCacheView(ServeScormContentView):
            def get_cache_control(self, content_type):
                return "max-age=42"

        response = CustomCacheView.as_view()(
            request, content_path=f"{scorm_package.extracted_path}/index.html"
        )

        assert response.status_code == 200
        assert response["Cache-Control"] == "max-age=42"

    def test_serve_scorm_content_not_found(self, client, user):
        """Test serving non-existent SCORM content."""
        client.force_login(user)
        url = reverse("wagtail_lms:serve_scorm_content", args=["nonexistent/file.html"])
        response = client.get(url)
        assert response.status_code == 404

    def test_serve_scorm_content_path_traversal(self, client, user):
        """Test path traversal protection."""
        client.force_login(user)
        url = reverse("wagtail_lms:serve_scorm_content", args=["../../etc/passwd"])
        response = client.get(url)
        assert response.status_code == 404

    def test_serve_via_storage_api(self, client, user, scorm_package):
        """Verify content is served through default_storage, not filesystem."""
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_scorm_content",
            args=[f"{scorm_package.extracted_path}/index.html"],
        )
        response = client.get(url)

        assert response.status_code == 200
        content = b"".join(response.streaming_content)
        assert b"Test Course" in content
        assert response["Content-Security-Policy"] == "frame-ancestors 'self'"

    def test_path_traversal_dotdot_segments(self, client, user):
        """Test .. in various path positions."""
        client.force_login(user)

        traversal_paths = [
            "../secret/file.html",
            "pkg/../../../etc/passwd",
            "pkg/sub/../../secret.html",
        ]
        for path in traversal_paths:
            url = reverse("wagtail_lms:serve_scorm_content", args=[path])
            response = client.get(url)
            assert response.status_code == 404, f"Path {path!r} should be blocked"

    def test_backslash_traversal_blocked(self, user):
        """Test Windows-style backslash traversal is rejected."""
        from wagtail_lms.views import ServeScormContentView

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        view = ServeScormContentView.as_view()

        backslash_paths = [
            "..\\..\\..\\etc\\passwd",
            "pkg\\..\\..\\secret.html",
            "pkg/sub\\..\\..\\secret.html",
        ]
        for path in backslash_paths:
            with pytest.raises(Http404):
                view(request, content_path=path)

    def test_absolute_path_blocked(self, user):
        """Test that leading / in content_path is rejected."""
        # Django's <path:> converter strips leading slashes, so we test
        # via the view function directly
        from wagtail_lms.views import ServeScormContentView

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        view = ServeScormContentView.as_view()

        with pytest.raises(Http404):
            view(request, content_path="/etc/passwd")

    def test_empty_and_dot_paths_blocked(self, user):
        """Empty and dot-normalized paths should return 404."""
        from wagtail_lms.views import ServeScormContentView

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        view = ServeScormContentView.as_view()

        with pytest.raises(Http404):
            view(request, content_path="")
        with pytest.raises(Http404):
            view(request, content_path=".")

    def test_directory_path_returns_404(self, client, user, scorm_package):
        """Directory-like path should not raise 500."""
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_scorm_content", args=[scorm_package.extracted_path]
        )
        response = client.get(url)
        assert response.status_code == 404
