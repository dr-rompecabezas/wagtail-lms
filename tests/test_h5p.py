"""Tests for H5P support — H5PActivity, LessonPage, xAPI endpoint."""

import io
import json
import zipfile
from urllib.parse import quote

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from wagtail.models import Page, Site

from wagtail_lms import conf
from wagtail_lms.models import (
    CourseEnrollment,
    CoursePage,
    H5PActivity,
    H5PAttempt,
    H5PContentUserData,
    H5PXAPIStatement,
    LessonPage,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

H5P_JSON = {
    "title": "Test Activity",
    "language": "und",
    "mainLibrary": "H5P.MultiChoice",
    "embedTypes": ["div"],
    "license": "U",
    "preloadedDependencies": [
        {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16}
    ],
}

CONTENT_JSON = {"media": {"type": {"params": {}}, "disableImageZooming": False}}


@pytest.fixture
def h5p_zip_file():
    """In-memory .h5p ZIP with h5p.json and content/content.json."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("h5p.json", json.dumps(H5P_JSON))
        zf.writestr("content/content.json", json.dumps(CONTENT_JSON))
    buf.seek(0)
    return SimpleUploadedFile(
        "test_activity.h5p", buf.getvalue(), content_type="application/zip"
    )


@pytest.fixture
def h5p_activity(h5p_zip_file, settings, tmp_path, db):
    """Saved H5PActivity with extracted content."""
    media_root = tmp_path / "media"
    settings.MEDIA_ROOT = str(media_root)

    activity = H5PActivity(
        title="Test H5P Activity",
        description="A test activity",
        package_file=h5p_zip_file,
    )
    activity.save()

    yield activity

    if activity.pk:
        activity.delete()


@pytest.fixture
def root_page():
    return Page.objects.get(depth=1)


@pytest.fixture
def home_page(root_page):
    existing = Page.objects.filter(depth=2).first()
    if existing:
        return existing
    home = Page(
        title="Home", slug="home-h5p", content_type_id=root_page.content_type_id
    )
    root_page.add_child(instance=home)
    site = Site.objects.filter(is_default_site=True).first()
    if site:
        site.root_page = home
        site.save()
    else:
        Site.objects.create(
            hostname="localhost", port=80, root_page=home, is_default_site=True
        )
    return home


@pytest.fixture
def course_page_h5p(home_page):
    """CoursePage with no SCORM package — intended for H5P LessonPage children."""
    course = CoursePage(
        title="H5P Course",
        slug="h5p-course",
        description="<p>An H5P-powered course</p>",
    )
    home_page.add_child(instance=course)
    course.save_revision().publish()
    return course


@pytest.fixture
def lesson_page(course_page_h5p, h5p_activity):
    """LessonPage child of course_page_h5p containing one H5P activity block."""
    lesson = LessonPage(
        title="Lesson One",
        slug="lesson-one",
        intro="<p>Welcome to lesson one.</p>",
        body=json.dumps(
            [
                {
                    "type": "paragraph",
                    "value": "<p>Some introductory text.</p>",
                },
                {
                    "type": "h5p_activity",
                    "value": {"activity": h5p_activity.pk},
                },
            ]
        ),
    )
    course_page_h5p.add_child(instance=lesson)
    lesson.save_revision().publish()
    return lesson


@pytest.fixture
def enrolled_user(user, course_page_h5p):
    """Regular user enrolled in course_page_h5p."""
    CourseEnrollment.objects.get_or_create(user=user, course=course_page_h5p)
    return user


# ---------------------------------------------------------------------------
# H5PActivity model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestH5PActivity:
    def test_extraction_on_save(self, h5p_activity):
        """Saving an H5PActivity with a .h5p file extracts its contents."""
        assert h5p_activity.extracted_path
        assert h5p_activity.extracted_path.startswith("h5p_")

    def test_h5p_json_parsed(self, h5p_activity):
        """h5p.json metadata is stored after extraction."""
        assert h5p_activity.main_library == "H5P.MultiChoice"
        assert h5p_activity.h5p_json.get("title") == "Test Activity"

    def test_content_files_stored(self, h5p_activity):
        """Both h5p.json and content/content.json are written to storage."""
        base = conf.WAGTAIL_LMS_H5P_CONTENT_PATH.rstrip("/")
        assert default_storage.exists(f"{base}/{h5p_activity.extracted_path}/h5p.json")
        assert default_storage.exists(
            f"{base}/{h5p_activity.extracted_path}/content/content.json"
        )

    def test_get_content_base_url(self, h5p_activity):
        """get_content_base_url returns a URL based on reverse(), not a hardcoded prefix."""
        url = h5p_activity.get_content_base_url()
        expected = reverse(
            "wagtail_lms:serve_h5p_content", args=[h5p_activity.extracted_path]
        )
        assert url == expected

    def test_get_content_base_url_no_extracted_path(self, db):
        """get_content_base_url returns None when not yet extracted."""
        activity = H5PActivity(title="Empty", extracted_path="")
        assert activity.get_content_base_url() is None

    def test_path_traversal_skipped(self, settings, tmp_path, caplog, db):
        """Malicious ZIP members with path traversal are silently skipped."""
        import logging

        settings.MEDIA_ROOT = str(tmp_path / "media")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("h5p.json", json.dumps(H5P_JSON))
            zf.writestr("content/content.json", json.dumps(CONTENT_JSON))
            # Malicious entries
            zf.writestr("../../../etc/passwd", "root:x:0:0")
            zf.writestr("..\\..\\evil.txt", "evil")
        buf.seek(0)

        f = SimpleUploadedFile(
            "evil.h5p", buf.getvalue(), content_type="application/zip"
        )
        with caplog.at_level(logging.WARNING, logger="wagtail_lms.models"):
            activity = H5PActivity(title="Evil", package_file=f)
            activity.save()

        # Warnings must have been logged for the skipped members
        assert any("suspicious ZIP member" in r.message for r in caplog.records)

        # Only the safe files should exist inside h5p_content/
        base = conf.WAGTAIL_LMS_H5P_CONTENT_PATH.rstrip("/")
        assert default_storage.exists(f"{base}/{activity.extracted_path}/h5p.json")
        assert default_storage.exists(
            f"{base}/{activity.extracted_path}/content/content.json"
        )
        # Traversal targets must not have been written inside the content dir
        assert not default_storage.exists(
            f"{base}/{activity.extracted_path}/etc/passwd"
        )
        assert not default_storage.exists(f"{base}/{activity.extracted_path}/evil.txt")

    def test_storage_backend_agnostic(self, h5p_zip_file, mock_s3_storage, db):
        """Extraction works with InMemoryStorage (simulating S3)."""
        activity = H5PActivity(title="S3 Activity", package_file=h5p_zip_file)
        activity.save()
        assert activity.extracted_path
        assert activity.main_library == "H5P.MultiChoice"

    def test_objects_create_does_not_raise(self, h5p_zip_file, settings, tmp_path, db):
        """H5PActivity.objects.create() passes force_insert=True; the double-save
        must strip that kwarg before the second save() or it raises IntegrityError."""
        settings.MEDIA_ROOT = str(tmp_path / "media")
        # Should not raise IntegrityError
        activity = H5PActivity.objects.create(
            title="Created Activity", package_file=h5p_zip_file
        )
        assert activity.pk is not None
        assert activity.extracted_path

    def test_zip_member_normalizing_to_dot_is_skipped(
        self, settings, tmp_path, caplog, db
    ):
        """A ZIP member like 'a/..' normalises to '.' and must be rejected."""
        import logging

        settings.MEDIA_ROOT = str(tmp_path / "media")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("h5p.json", json.dumps(H5P_JSON))
            zf.writestr("content/content.json", json.dumps(CONTENT_JSON))
            # This member name normalises to "." after posixpath.normpath()
            zf.writestr("a/..", "sneaky content")
        buf.seek(0)

        f = SimpleUploadedFile(
            "dot.h5p", buf.getvalue(), content_type="application/zip"
        )
        with caplog.at_level(logging.WARNING, logger="wagtail_lms.models"):
            activity = H5PActivity(title="Dot ZIP", package_file=f)
            activity.save()

        assert any("suspicious ZIP member" in r.message for r in caplog.records)
        # Normal files must still be extracted
        base = conf.WAGTAIL_LMS_H5P_CONTENT_PATH.rstrip("/")
        assert default_storage.exists(f"{base}/{activity.extracted_path}/h5p.json")

    def test_package_replacement_re_extracts(
        self, h5p_activity, settings, tmp_path, db
    ):
        """Uploading a new .h5p file to an existing activity re-extracts the content
        and discards the stale extracted_path and metadata."""
        settings.MEDIA_ROOT = str(tmp_path / "media")

        old_extracted_path = h5p_activity.extracted_path
        old_main_library = h5p_activity.main_library
        assert old_extracted_path

        # Build a second .h5p with a different mainLibrary
        new_h5p_json = dict(H5P_JSON, mainLibrary="H5P.CoursePresentation")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("h5p.json", json.dumps(new_h5p_json))
            zf.writestr("content/content.json", json.dumps(CONTENT_JSON))
        buf.seek(0)
        new_file = SimpleUploadedFile(
            "updated_activity.h5p", buf.getvalue(), content_type="application/zip"
        )

        h5p_activity.package_file = new_file
        h5p_activity.save()

        assert h5p_activity.extracted_path != old_extracted_path
        assert h5p_activity.main_library == "H5P.CoursePresentation"
        assert h5p_activity.main_library != old_main_library

        # New content must be present at the new path
        base = conf.WAGTAIL_LMS_H5P_CONTENT_PATH.rstrip("/")
        assert default_storage.exists(f"{base}/{h5p_activity.extracted_path}/h5p.json")

    def test_clean_raises_on_corrupted_zip(self, settings, tmp_path, db):
        """clean() raises ValidationError when ZIP CRC check fails."""
        from django.core.exceptions import ValidationError

        settings.MEDIA_ROOT = str(tmp_path / "media")

        # Build a valid ZIP, then corrupt one file's data in-place
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("h5p.json", json.dumps(H5P_JSON))
            zf.writestr("content/content.json", json.dumps(CONTENT_JSON))
        raw = bytearray(buf.getvalue())
        # Flip some bytes in the middle to corrupt the CRC
        mid = len(raw) // 2
        raw[mid] ^= 0xFF
        raw[mid + 1] ^= 0xFF
        corrupted = SimpleUploadedFile(
            "corrupted.h5p", bytes(raw), content_type="application/zip"
        )

        activity = H5PActivity(title="Corrupt", package_file=corrupted)
        with pytest.raises(ValidationError) as exc_info:
            activity.clean()
        errors = exc_info.value.message_dict
        assert "package_file" in errors

    def test_clean_does_not_consume_uploaded_file(self, settings, tmp_path, db):
        """clean() leaves the UploadedFile readable so save() can commit it.

        Using FieldFile.open() in a ``with`` block would close (and on
        systems with delete=True NamedTemporaryFile, delete) the temp file
        before save() runs.  Accessing _file directly avoids this.
        """
        settings.MEDIA_ROOT = str(tmp_path / "media")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("h5p.json", json.dumps(H5P_JSON))
            zf.writestr("content/content.json", json.dumps(CONTENT_JSON))
        valid = SimpleUploadedFile(
            "valid.h5p", buf.getvalue(), content_type="application/zip"
        )

        activity = H5PActivity(title="Valid", package_file=valid)
        activity.clean()  # Must not consume/close the file

        # The file object must still be readable after clean().
        raw = activity.package_file._file
        raw.seek(0)
        assert raw.read(2) == b"PK"  # ZIP magic bytes

    def test_str(self, h5p_activity):
        assert str(h5p_activity) == "Test H5P Activity"


# ---------------------------------------------------------------------------
# LessonPage access control tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLessonPageAccess:
    def test_unauthenticated_redirects_to_login(self, client, lesson_page):
        """Unauthenticated users are redirected to login."""
        response = client.get(lesson_page.url)
        assert response.status_code == 302
        assert "login" in response.url.lower()

    def test_unenrolled_user_redirected_to_course(
        self, client, user, lesson_page, course_page_h5p
    ):
        """Authenticated but unenrolled users are redirected to the course page."""
        client.force_login(user)
        response = client.get(lesson_page.url)
        assert response.status_code == 302
        assert course_page_h5p.url in response.url

    def test_enrolled_user_can_access(self, client, enrolled_user, lesson_page):
        """Enrolled users can view the lesson."""
        client.force_login(enrolled_user)
        response = client.get(lesson_page.url)
        assert response.status_code == 200
        assert b"Lesson One" in response.content

    def test_admin_bypasses_enrollment(self, client, superuser, lesson_page):
        """Wagtail admin users can access lessons without being enrolled."""
        client.force_login(superuser)
        response = client.get(lesson_page.url)
        assert response.status_code == 200

    def test_lesson_body_rendered(self, client, enrolled_user, lesson_page):
        """StreamField content is rendered in the lesson."""
        client.force_login(enrolled_user)
        response = client.get(lesson_page.url)
        # The paragraph block text should appear
        assert b"introductory text" in response.content

    def test_page_hierarchy_enforced(self, home_page):
        """LessonPage cannot be created directly under a non-CoursePage parent."""
        assert "wagtail_lms.LessonPage" in CoursePage.subpage_types
        assert "wagtail_lms.CoursePage" in LessonPage.parent_page_types
        assert LessonPage.subpage_types == []


# ---------------------------------------------------------------------------
# H5P xAPI endpoint tests
# ---------------------------------------------------------------------------


def _xapi_statement(verb_id, verb_label="", score=None, object_iri=None):
    """Build a minimal xAPI statement dict."""
    stmt = {
        "actor": {"mbox": "mailto:learner@example.com", "name": "Learner"},
        "verb": {
            "id": verb_id,
            "display": {"en-US": verb_label},
        },
        "object": {
            "id": object_iri or "http://example.com/activity/1",
            "objectType": "Activity",
        },
    }
    if score is not None:
        stmt["result"] = {
            "score": {"raw": score, "min": 0, "max": 100, "scaled": score / 100},
            "completion": True,
        }
    return stmt


@pytest.mark.django_db
class TestH5PXAPIView:
    def _url(self, activity_id):
        return reverse("wagtail_lms:h5p_xapi", args=[activity_id])

    def test_requires_login(self, client, h5p_activity):
        url = self._url(h5p_activity.pk)
        response = client.post(
            url,
            data=json.dumps(
                _xapi_statement("http://adlnet.gov/expapi/verbs/experienced")
            ),
            content_type="application/json",
        )
        assert response.status_code == 302  # redirect to login

    def test_get_not_allowed(self, client, user, h5p_activity):
        client.force_login(user)
        response = client.get(self._url(h5p_activity.pk))
        assert response.status_code == 405

    def test_invalid_json_returns_400(self, client, user, h5p_activity):
        client.force_login(user)
        response = client.post(
            self._url(h5p_activity.pk), data="not-json", content_type="application/json"
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("payload", ["[]", '"a string"', "42", "true"])
    def test_non_object_json_returns_400(self, client, user, h5p_activity, payload):
        """Valid JSON that is not an object must return 400, not 500."""
        client.force_login(user)
        response = client.post(
            self._url(h5p_activity.pk), data=payload, content_type="application/json"
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "payload",
        [
            '{"verb": []}',
            '{"verb": "not-an-object"}',
            '{"verb": {"id": "http://adlnet.gov/expapi/verbs/completed"}, "result": []}',
            '{"verb": {"id": "http://adlnet.gov/expapi/verbs/scored"}, "result": "bad"}',
        ],
    )
    def test_malformed_nested_fields_return_400(
        self, client, user, h5p_activity, payload
    ):
        """Non-object verb or result fields return 400 instead of 500."""
        client.force_login(user)
        response = client.post(
            self._url(h5p_activity.pk), data=payload, content_type="application/json"
        )
        assert response.status_code == 400

    def test_null_verb_returns_400(self, client, user, h5p_activity):
        """'verb': null is not a valid xAPI object and must return 400."""
        client.force_login(user)
        response = client.post(
            self._url(h5p_activity.pk),
            data='{"verb": null}',
            content_type="application/json",
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "display_value",
        [
            '"a plain string"',
            "42",
            "[]",
        ],
    )
    def test_non_dict_verb_display_accepted(
        self, client, user, h5p_activity, display_value
    ):
        """verb.display that is not a dict must not crash (treated as empty)."""
        client.force_login(user)
        payload = json.dumps(
            {
                "verb": {
                    "id": "http://adlnet.gov/expapi/verbs/experienced",
                    "display": json.loads(display_value),
                }
            }
        )
        response = client.post(
            self._url(h5p_activity.pk), data=payload, content_type="application/json"
        )
        assert response.status_code == 200
        stmt_obj = H5PXAPIStatement.objects.get(
            attempt__user=user, attempt__activity=h5p_activity
        )
        assert stmt_obj.verb_display == ""

    def test_creates_attempt_and_statement(self, client, user, h5p_activity):
        """First xAPI POST lazily creates H5PAttempt and H5PXAPIStatement."""
        client.force_login(user)
        stmt = _xapi_statement(
            "http://adlnet.gov/expapi/verbs/experienced", "experienced"
        )
        response = client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        attempt = H5PAttempt.objects.get(user=user, activity=h5p_activity)
        assert attempt is not None
        assert H5PXAPIStatement.objects.filter(attempt=attempt).count() == 1

    def test_reuses_existing_attempt(self, client, user, h5p_activity):
        """Subsequent POSTs reuse the same H5PAttempt."""
        client.force_login(user)
        stmt = _xapi_statement("http://adlnet.gov/expapi/verbs/experienced")
        url = self._url(h5p_activity.pk)
        client.post(url, data=json.dumps(stmt), content_type="application/json")
        client.post(url, data=json.dumps(stmt), content_type="application/json")

        assert H5PAttempt.objects.filter(user=user, activity=h5p_activity).count() == 1
        assert (
            H5PXAPIStatement.objects.filter(
                attempt__user=user, attempt__activity=h5p_activity
            ).count()
            == 2
        )

    def test_attempt_unique_per_user_activity(self, user, h5p_activity):
        """DB-level unique constraint prevents duplicate H5PAttempt rows."""
        from django.db import IntegrityError, transaction

        H5PAttempt.objects.create(user=user, activity=h5p_activity)
        with pytest.raises(IntegrityError):
            with transaction.atomic():  # savepoint keeps outer transaction clean
                H5PAttempt.objects.create(user=user, activity=h5p_activity)

    def test_completed_verb_updates_status(self, client, user, h5p_activity):
        client.force_login(user)
        stmt = _xapi_statement("http://adlnet.gov/expapi/verbs/completed", "completed")
        client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        attempt = H5PAttempt.objects.get(user=user, activity=h5p_activity)
        assert attempt.completion_status == "completed"

    def test_passed_verb_updates_both_statuses(self, client, user, h5p_activity):
        client.force_login(user)
        stmt = _xapi_statement("http://adlnet.gov/expapi/verbs/passed", "passed")
        client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        attempt = H5PAttempt.objects.get(user=user, activity=h5p_activity)
        assert attempt.completion_status == "completed"
        assert attempt.success_status == "passed"

    def test_failed_verb_updates_success_status(self, client, user, h5p_activity):
        client.force_login(user)
        stmt = _xapi_statement("http://adlnet.gov/expapi/verbs/failed", "failed")
        client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        attempt = H5PAttempt.objects.get(user=user, activity=h5p_activity)
        assert attempt.success_status == "failed"

    def test_score_extracted_from_result(self, client, user, h5p_activity):
        client.force_login(user)
        stmt = _xapi_statement(
            "http://adlnet.gov/expapi/verbs/scored", "scored", score=75
        )
        client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        attempt = H5PAttempt.objects.get(user=user, activity=h5p_activity)
        assert attempt.score_raw == 75.0
        assert attempt.score_max == 100.0
        assert attempt.score_min == 0.0
        assert pytest.approx(attempt.score_scaled, abs=0.01) == 0.75

    def test_verb_display_stored(self, client, user, h5p_activity):
        client.force_login(user)
        stmt = _xapi_statement("http://adlnet.gov/expapi/verbs/answered", "answered")
        client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        statement_obj = H5PXAPIStatement.objects.get(
            attempt__user=user, attempt__activity=h5p_activity
        )
        assert statement_obj.verb_display == "answered"

    @pytest.mark.parametrize(
        "verb_iri,verb_display",
        [
            ("http://adlnet.gov/expapi/verbs/completed", "completed"),
            ("http://adlnet.gov/expapi/verbs/passed", "passed"),
        ],
    )
    def test_completion_verb_sets_enrollment_completed_at(
        self,
        client,
        enrolled_user,
        h5p_activity,
        lesson_page,
        course_page_h5p,
        verb_iri,
        verb_display,
    ):
        """completed/passed verbs propagate to CourseEnrollment.completed_at."""
        client.force_login(enrolled_user)
        stmt = _xapi_statement(verb_iri, verb_display)
        client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        enrollment = CourseEnrollment.objects.get(
            user=enrolled_user, course=course_page_h5p
        )
        assert enrollment.completed_at is not None

    def test_failed_verb_does_not_set_enrollment_completed_at(
        self, client, enrolled_user, h5p_activity, lesson_page, course_page_h5p
    ):
        """failed xAPI verb does not set CourseEnrollment.completed_at."""
        client.force_login(enrolled_user)
        stmt = _xapi_statement("http://adlnet.gov/expapi/verbs/failed", "failed")
        client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        enrollment = CourseEnrollment.objects.get(
            user=enrolled_user, course=course_page_h5p
        )
        assert enrollment.completed_at is None

    def test_completion_without_enrollment_does_not_error(
        self, client, user, h5p_activity, lesson_page, course_page_h5p
    ):
        """completed verb for a non-enrolled user silently matches zero rows — no error."""
        client.force_login(user)
        stmt = _xapi_statement("http://adlnet.gov/expapi/verbs/completed", "completed")
        response = client.post(
            self._url(h5p_activity.pk),
            data=json.dumps(stmt),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert not CourseEnrollment.objects.filter(
            user=user, course=course_page_h5p
        ).exists()

    def test_streamfield_body_format_matches_enrollment_lookup(
        self, lesson_page, h5p_activity
    ):
        """Verify that Wagtail stores H5PActivityBlock in a format that the
        _mark_h5p_enrollment_complete lookup string matches.

        If Wagtail changes its StreamField serialisation (spacing, key order,
        compression) this test will fail and alert us to update the lookup.
        """
        from django.db import connection

        # Read the raw body column value directly from the DB
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT body FROM wagtail_lms_lessonpage WHERE page_ptr_id = %s",
                [lesson_page.pk],
            )
            row = cursor.fetchone()
        assert row is not None, "LessonPage not found in DB"
        raw_body = row[0]
        # The lookup string used by _mark_h5p_enrollment_complete
        lookup = '"activity": ' + str(h5p_activity.pk) + "}"
        assert lookup in raw_body, (
            f"Lookup string {lookup!r} not found in raw StreamField body. "
            f"The body__icontains lookup in _mark_h5p_enrollment_complete "
            f"would silently fail. Raw body excerpt: {raw_body[:200]}"
        )


@pytest.mark.django_db
class TestH5PContentUserDataView:
    def _url(self, activity_id, data_type="state", sub_content_id=0):
        base = reverse("wagtail_lms:h5p_content_user_data", args=[activity_id])
        return (
            f"{base}?dataType={quote(data_type, safe='')}&subContentId={sub_content_id}"
        )

    def test_requires_login(self, client, h5p_activity):
        response = client.get(self._url(h5p_activity.pk))
        assert response.status_code == 302

    def test_get_empty_returns_success_false_data(self, client, user, h5p_activity):
        client.force_login(user)
        response = client.get(self._url(h5p_activity.pk))
        assert response.status_code == 200
        assert response.json() == {"success": True, "data": False}
        assert not H5PAttempt.objects.filter(user=user, activity=h5p_activity).exists()

    def test_post_then_get_round_trip(self, client, user, h5p_activity):
        client.force_login(user)
        url = self._url(h5p_activity.pk, data_type="state", sub_content_id=0)
        payload = json.dumps({"progress": 0.5, "answers": [1, 0, 1]})

        post_resp = client.post(url, data={"data": payload})
        assert post_resp.status_code == 200
        assert post_resp.json() == {"success": True}

        get_resp = client.get(url)
        assert get_resp.status_code == 200
        assert get_resp.json() == {"success": True, "data": payload}

        attempt = H5PAttempt.objects.get(user=user, activity=h5p_activity)
        row = H5PContentUserData.objects.get(
            attempt=attempt, data_type="state", sub_content_id=0
        )
        assert row.value == payload

    def test_post_data_zero_resets_value(self, client, user, h5p_activity):
        client.force_login(user)
        url = self._url(h5p_activity.pk)
        client.post(url, data={"data": '{"progress":1}'})
        attempt = H5PAttempt.objects.get(user=user, activity=h5p_activity)
        assert H5PContentUserData.objects.filter(attempt=attempt).count() == 1

        reset_resp = client.post(url, data={"data": "0"})
        assert reset_resp.status_code == 200
        assert reset_resp.json() == {"success": True}
        assert H5PContentUserData.objects.filter(attempt=attempt).count() == 0

    def test_post_lazily_creates_attempt(self, client, user, h5p_activity):
        client.force_login(user)
        assert not H5PAttempt.objects.filter(user=user, activity=h5p_activity).exists()
        response = client.post(self._url(h5p_activity.pk), data={"data": '{"x":1}'})
        assert response.status_code == 200
        assert H5PAttempt.objects.filter(user=user, activity=h5p_activity).count() == 1

    @pytest.mark.parametrize(
        "query,expected_message",
        [
            ("", "Missing dataType"),
            ("?dataType=state&subContentId=-1", "Invalid subContentId"),
            ("?dataType=state&subContentId=abc", "Invalid subContentId"),
        ],
    )
    def test_invalid_query_params_return_400(
        self, client, user, h5p_activity, query, expected_message
    ):
        client.force_login(user)
        base = reverse("wagtail_lms:h5p_content_user_data", args=[h5p_activity.pk])
        response = client.get(base + query)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["message"] == expected_message

    def test_missing_post_data_returns_400(self, client, user, h5p_activity):
        client.force_login(user)
        response = client.post(self._url(h5p_activity.pk), data={})
        assert response.status_code == 400
        assert response.json()["message"] == "Missing data"

    def test_oversized_post_data_returns_413(self, client, user, h5p_activity):
        client.force_login(user)
        oversized = "x" * (65_536 + 1)
        response = client.post(self._url(h5p_activity.pk), data={"data": oversized})
        assert response.status_code == 413
        assert response.json() == {"success": False, "message": "data too large"}

    def test_lesson_html_includes_user_data_endpoint(
        self, client, enrolled_user, lesson_page, h5p_activity
    ):
        client.force_login(enrolled_user)
        response = client.get(lesson_page.url)
        assert response.status_code == 200
        expected_path = reverse(
            "wagtail_lms:h5p_content_user_data", args=[h5p_activity.pk]
        )
        content = response.content.decode("utf-8")
        assert 'data-user-data-url="' in content
        assert expected_path in content
        assert "dataType=:dataType" in content
        assert "subContentId=:subContentId" in content


# ---------------------------------------------------------------------------
# System checks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_system_check_no_warnings_on_clean_setup():
    """No warnings emitted when no CoursePage subclasses override subpage_types."""
    from wagtail_lms.checks import check_coursepage_subclass_subpage_types

    errors = check_coursepage_subclass_subpage_types(app_configs=None)
    assert errors == []


# ---------------------------------------------------------------------------
# ServeH5PContentView tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestServeH5PContentView:
    def test_requires_login(self, client, h5p_activity):
        url = reverse(
            "wagtail_lms:serve_h5p_content",
            args=[f"{h5p_activity.extracted_path}/h5p.json"],
        )
        response = client.get(url)
        assert response.status_code == 302

    def test_serves_h5p_json(self, client, user, h5p_activity):
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_h5p_content",
            args=[f"{h5p_activity.extracted_path}/h5p.json"],
        )
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

    def test_serves_content_json(self, client, user, h5p_activity):
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_h5p_content",
            args=[f"{h5p_activity.extracted_path}/content/content.json"],
        )
        response = client.get(url)
        assert response.status_code == 200

    def test_path_traversal_rejected(self, client, user):
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_h5p_content",
            args=["../../../etc/passwd"],
        )
        response = client.get(url)
        assert response.status_code == 404

    def test_missing_file_returns_404(self, client, user, h5p_activity):
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_h5p_content",
            args=[f"{h5p_activity.extracted_path}/does_not_exist.js"],
        )
        response = client.get(url)
        assert response.status_code == 404

    def test_security_headers_set(self, client, user, h5p_activity):
        client.force_login(user)
        url = reverse(
            "wagtail_lms:serve_h5p_content",
            args=[f"{h5p_activity.extracted_path}/h5p.json"],
        )
        response = client.get(url)
        assert response["X-Frame-Options"] == "SAMEORIGIN"
        assert "frame-ancestors" in response["Content-Security-Policy"]
