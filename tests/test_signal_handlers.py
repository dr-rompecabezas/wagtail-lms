"""Tests for SCORM package file cleanup on deletion."""

import io
import os
import zipfile

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from wagtail_lms.models import SCORMPackage


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
        content_prefix = f"scorm_content/{extracted_path}"

        # Verify extracted files exist
        dirs, files = default_storage.listdir(content_prefix)
        assert len(files) > 0 or len(dirs) > 0

        package.delete()

        # Verify extracted files are gone (directory may still exist but be empty)
        try:
            dirs, files = default_storage.listdir(content_prefix)
            assert len(files) == 0 and len(dirs) == 0
        except FileNotFoundError:
            pass  # Directory gone entirely — also acceptable

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
        # Save without triggering extraction by pre-setting extracted_path to skip
        # We'll manually bypass by saving with update_fields after initial save
        package.save()
        # Clear extracted_path to simulate no extraction
        SCORMPackage.objects.filter(pk=package.pk).update(extracted_path="")
        package.refresh_from_db()

        assert package.extracted_path == ""
        # Should not raise
        package.delete()

    def test_delete_without_package_file(self, settings, tmp_path, db):
        """Package with no file at all."""
        media_root = tmp_path / "media"
        settings.MEDIA_ROOT = str(media_root)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        package = SCORMPackage(title="No file")
        # Use super().save() to skip extraction logic
        SCORMPackage.save(package)
        # Clear the package_file
        SCORMPackage.objects.filter(pk=package.pk).update(package_file="")
        package.refresh_from_db()

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
            try:
                dirs, files = default_storage.listdir(f"scorm_content/{ep}")
                assert len(files) == 0 and len(dirs) == 0
            except FileNotFoundError:
                pass  # Directory gone entirely — also acceptable
