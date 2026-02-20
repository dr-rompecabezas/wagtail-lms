"""Tests for SCORM package file cleanup on deletion."""

import io
import os
import zipfile
from unittest.mock import patch

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models

from wagtail_lms import conf
from wagtail_lms.models import H5PActivity, SCORMPackage
from wagtail_lms.signal_handlers import _delete_extracted_content


def _make_scorm_zip(manifest_xml, content_filename="index.html"):
    """Helper to create a SCORM ZIP file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest_xml)
        zf.writestr(content_filename, "<html><body>Test</body></html>")
    buf.seek(0)
    return SimpleUploadedFile(
        "test.zip", buf.getvalue(), content_type="application/zip"
    )


def _content_prefix(extracted_path):
    """Build the storage prefix for extracted content using the configured path."""
    return conf.WAGTAIL_LMS_CONTENT_PATH.rstrip("/") + "/" + extracted_path


def _make_h5p_zip():
    """Helper to create a minimal H5P ZIP file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "h5p.json",
            (
                '{"title":"Signal Handler Test","mainLibrary":"H5P.MultiChoice",'
                '"embedTypes":["div"],"license":"U"}'
            ),
        )
        zf.writestr("content/content.json", '{"foo":"bar"}')
    buf.seek(0)
    return SimpleUploadedFile(
        "test.h5p", buf.getvalue(), content_type="application/zip"
    )


@pytest.mark.django_db(transaction=True)
class TestSCORMPackageDeletion:
    def _create_package(self, settings, tmp_path, scorm_12_manifest):
        media_root = tmp_path / "media"
        settings.MEDIA_ROOT = str(media_root)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        package = SCORMPackage(
            title="Cleanup Test",
            package_file=_make_scorm_zip(scorm_12_manifest),
            version="1.2",
        )
        package.save()
        return package

    def test_delete_removes_zip_file(self, settings, tmp_path, scorm_12_manifest):
        package = self._create_package(settings, tmp_path, scorm_12_manifest)
        zip_name = package.package_file.name

        assert default_storage.exists(zip_name)
        package.delete()
        assert not default_storage.exists(zip_name)

    def test_delete_removes_extracted_content(
        self, settings, tmp_path, scorm_12_manifest
    ):
        package = self._create_package(settings, tmp_path, scorm_12_manifest)
        extracted_path = package.extracted_path
        prefix = _content_prefix(extracted_path)

        # Verify extracted files exist
        dirs, files = default_storage.listdir(prefix)
        assert len(files) > 0 or len(dirs) > 0

        package.delete()

        # Verify extracted files and directory are gone
        with pytest.raises(FileNotFoundError):
            default_storage.listdir(prefix)

    def test_delete_without_extracted_path(self, settings, tmp_path, scorm_12_manifest):
        """Package saved but extraction didn't happen (e.g., invalid ZIP)."""
        media_root = tmp_path / "media"
        settings.MEDIA_ROOT = str(media_root)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        package = SCORMPackage(
            title="No extraction",
            package_file=_make_scorm_zip(scorm_12_manifest),
            version="1.2",
        )
        # Save via base Model.save() to bypass extraction logic
        models.Model.save(package)

        assert package.extracted_path == ""
        # Should not raise
        package.delete()

    def test_delete_without_package_file(self, settings, tmp_path, db):
        """Package with no file at all."""
        media_root = tmp_path / "media"
        settings.MEDIA_ROOT = str(media_root)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        package = SCORMPackage(title="No file")
        # Save via base Model.save() to bypass extraction logic
        models.Model.save(package)

        assert not package.package_file
        # Should not raise
        package.delete()

    def test_bulk_delete_cleans_up(self, settings, tmp_path, scorm_12_manifest):
        """queryset.delete() should trigger cleanup for each package."""
        media_root = tmp_path / "media"
        settings.MEDIA_ROOT = str(media_root)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        packages = []
        for i in range(3):
            pkg = SCORMPackage(
                title=f"Bulk {i}",
                package_file=_make_scorm_zip(scorm_12_manifest),
                version="1.2",
            )
            pkg.save()
            packages.append(pkg)

        zip_names = [p.package_file.name for p in packages]
        extracted_paths = [p.extracted_path for p in packages]

        # Verify files exist
        for name in zip_names:
            assert default_storage.exists(name)

        SCORMPackage.objects.filter(pk__in=[p.pk for p in packages]).delete()

        # Verify all cleaned up
        for name in zip_names:
            assert not default_storage.exists(name)
        for ep in extracted_paths:
            with pytest.raises(FileNotFoundError):
                default_storage.listdir(_content_prefix(ep))

    def test_delete_with_mock_s3_storage(self, mock_s3_storage, scorm_12_manifest, db):
        """Cleanup works on remote backends where .path() is unavailable."""
        package = SCORMPackage(
            title="S3 Cleanup Test",
            package_file=_make_scorm_zip(scorm_12_manifest),
            version="1.2",
        )
        package.save()

        zip_name = package.package_file.name
        prefix = _content_prefix(package.extracted_path)

        assert default_storage.exists(zip_name)
        dirs, files = default_storage.listdir(prefix)
        assert len(files) > 0 or len(dirs) > 0

        package.delete()

        assert not default_storage.exists(zip_name)
        # InMemoryStorage keeps empty "directories" as keys, so just check files
        dirs, files = default_storage.listdir(prefix)
        assert len(files) == 0

    @pytest.mark.parametrize(
        "bad_path",
        [
            "../../etc",  # classic traversal
            "a/..",  # normalizes to "." — would target the base dir
            ".",  # explicit dot
            "",  # empty string
            "foo/bar",  # nested path (only top-level dirs expected)
            "/etc",  # absolute path
        ],
    )
    def test_path_traversal_rejected(self, bad_path):
        """Suspicious extracted_path values are refused without touching storage."""
        with patch("wagtail_lms.signal_handlers.default_storage") as mock_storage:
            _delete_extracted_content(bad_path, conf.WAGTAIL_LMS_CONTENT_PATH)
            mock_storage.listdir.assert_not_called()
            mock_storage.delete.assert_not_called()

    def test_file_delete_error_logged(
        self, settings, tmp_path, scorm_12_manifest, caplog
    ):
        """Errors during file deletion are logged, not raised."""
        package = self._create_package(settings, tmp_path, scorm_12_manifest)
        zip_name = package.package_file.name

        with patch(
            "wagtail_lms.signal_handlers.default_storage.delete",
            side_effect=OSError("disk error"),
        ):
            package.delete()

        assert "Failed to delete package file" in caplog.text
        assert zip_name in caplog.text


@pytest.mark.django_db(transaction=True)
class TestH5PActivityDeletion:
    def _create_activity(self, settings, tmp_path):
        media_root = tmp_path / "media"
        settings.MEDIA_ROOT = str(media_root)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        activity = H5PActivity(
            title="Cleanup Test",
            package_file=_make_h5p_zip(),
        )
        activity.save()
        return activity

    def test_delete_passes_h5p_content_base_path(self, settings, tmp_path):
        activity = self._create_activity(settings, tmp_path)
        extracted_path = activity.extracted_path

        with patch(
            "wagtail_lms.signal_handlers._delete_extracted_content"
        ) as mock_delete_extracted:
            activity.delete()

        mock_delete_extracted.assert_called_once_with(
            extracted_path, conf.WAGTAIL_LMS_H5P_CONTENT_PATH
        )

    def test_file_delete_error_logged(self, settings, tmp_path, caplog):
        """Errors during H5P package deletion are logged, not raised."""
        activity = self._create_activity(settings, tmp_path)
        pkg_name = activity.package_file.name

        with (
            patch(
                "wagtail_lms.signal_handlers.default_storage.delete",
                side_effect=OSError("disk error"),
            ),
            patch("wagtail_lms.signal_handlers._delete_extracted_content"),
        ):
            activity.delete()

        assert "Failed to delete H5P package file" in caplog.text
        assert pkg_name in caplog.text

    def test_extracted_content_delete_error_logged(self, settings, tmp_path, caplog):
        """Errors during extracted H5P cleanup are logged, not raised."""
        activity = self._create_activity(settings, tmp_path)
        extracted_path = activity.extracted_path

        with patch(
            "wagtail_lms.signal_handlers._delete_extracted_content",
            side_effect=OSError("disk error"),
        ):
            activity.delete()

        assert "Failed to delete extracted H5P content" in caplog.text
        assert extracted_path in caplog.text
