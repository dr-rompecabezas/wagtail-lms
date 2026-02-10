"""Pytest fixtures for wagtail-lms tests."""

import io
import os
import sys
import zipfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.functional import empty
from wagtail.models import Page, Site

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wagtail_lms.models import CoursePage, SCORMPackage

# Register pytest fixtures
pytest_plugins = ["pytest_django"]


@pytest.fixture
def user(django_user_model):
    """Create a test user."""
    return django_user_model.objects.create_user(
        username="testuser", password="testpass123", email="test@example.com"
    )


@pytest.fixture
def superuser(django_user_model):
    """Create a test superuser."""
    return django_user_model.objects.create_superuser(
        username="admin", password="adminpass123", email="admin@example.com"
    )


@pytest.fixture
def scorm_12_manifest():
    """Create a SCORM 1.2 manifest XML."""
    return """<?xml version="1.0"?>
<manifest identifier="test_course" version="1.0"
    xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
    xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
    <metadata>
        <schema>ADL SCORM</schema>
        <schemaversion>1.2</schemaversion>
    </metadata>
    <organizations default="test_org">
        <organization identifier="test_org">
            <title>Test SCORM Course</title>
            <item identifier="item1" identifierref="resource1">
                <title>Lesson 1</title>
            </item>
        </organization>
    </organizations>
    <resources>
        <resource identifier="resource1" type="webcontent" adlcp:scormtype="sco" href="index.html">
            <file href="index.html"/>
        </resource>
    </resources>
</manifest>"""


@pytest.fixture
def scorm_2004_manifest():
    """Create a SCORM 2004 manifest XML."""
    return """<?xml version="1.0"?>
<manifest identifier="test_course_2004" version="1.0"
    xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
    xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3">
    <metadata>
        <schema>ADL SCORM</schema>
        <schemaversion>2004 3rd Edition</schemaversion>
    </metadata>
    <organizations default="test_org">
        <organization identifier="test_org">
            <title>Test SCORM 2004 Course</title>
            <item identifier="item1" identifierref="resource1">
                <title>Lesson 1</title>
            </item>
        </organization>
    </organizations>
    <resources>
        <resource identifier="resource1" type="webcontent" adlcp:scormtype="sco" href="lesson.html">
            <file href="lesson.html"/>
        </resource>
    </resources>
</manifest>"""


@pytest.fixture
def scorm_zip_file(scorm_12_manifest, tmp_path):
    """Create a test SCORM package ZIP file."""
    # Create a temporary ZIP file
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Add manifest
        zip_file.writestr("imsmanifest.xml", scorm_12_manifest)
        # Add HTML file
        zip_file.writestr("index.html", "<html><body>Test Course</body></html>")

    zip_buffer.seek(0)
    return SimpleUploadedFile(
        "test_scorm.zip", zip_buffer.getvalue(), content_type="application/zip"
    )


@pytest.fixture
def scorm_2004_zip_file(scorm_2004_manifest):
    """Create a test SCORM 2004 package ZIP file."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Add manifest
        zip_file.writestr("imsmanifest.xml", scorm_2004_manifest)
        # Add HTML file
        zip_file.writestr("lesson.html", "<html><body>SCORM 2004 Course</body></html>")

    zip_buffer.seek(0)
    return SimpleUploadedFile(
        "test_scorm_2004.zip", zip_buffer.getvalue(), content_type="application/zip"
    )


@pytest.fixture
def scorm_package(scorm_zip_file, settings, tmp_path, db):
    """Create a test SCORM package with extracted content."""
    # Use tmp_path for media root in tests
    media_root = tmp_path / "media"
    settings.MEDIA_ROOT = str(media_root)
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    # Create package without specifying ID (let Django auto-assign)
    package = SCORMPackage(
        title="Test SCORM Package",
        description="Test Description",
        package_file=scorm_zip_file,
        version="1.2",
    )
    package.save()

    yield package

    # Cleanup: delete the package and its files
    if package.pk:
        package.delete()


@pytest.fixture
def root_page():
    """Get or create the root page."""
    return Page.objects.get(depth=1)


@pytest.fixture
def home_page(root_page):
    """Create a simple home page for testing."""
    # Check if we already have a home page
    existing = Page.objects.filter(depth=2).first()
    if existing:
        return existing

    # Create a basic Page as home
    home = Page(
        title="Home",
        slug="home",
        content_type_id=Page.objects.get(depth=1).content_type_id,
    )
    root_page.add_child(instance=home)

    # Ensure we have a site pointing to it
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
def course_page(home_page, scorm_package):
    """Create a test course page."""
    course = CoursePage(
        title="Test Course",
        slug="test-course",
        description="<p>Test course description</p>",
        scorm_package=scorm_package,
    )
    home_page.add_child(instance=course)
    course.save_revision().publish()
    return course


@pytest.fixture
def mock_s3_storage(settings):
    """Simulate a non-local storage backend (like S3) using InMemoryStorage.

    InMemoryStorage does not support .path, just like S3Boto3Storage,
    so this fixture verifies that code never relies on the filesystem.
    Available since Django 4.2.
    """
    from django.core.files.storage import default_storage, storages

    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    # Clear cached storage instances so default_storage picks up the new backend
    storages._storages = {}
    default_storage._wrapped = empty


@pytest.fixture
def scorm_zip_with_traversal(scorm_12_manifest):
    """Create a SCORM ZIP containing a path-traversal attack alongside valid files."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("imsmanifest.xml", scorm_12_manifest)
        zip_file.writestr("index.html", "<html><body>Safe Content</body></html>")
        # Malicious entry — should be skipped during extraction
        zip_file.writestr("../../../etc/passwd", "root:x:0:0:root:/root:/bin/bash")

    zip_buffer.seek(0)
    return SimpleUploadedFile(
        "malicious_scorm.zip", zip_buffer.getvalue(), content_type="application/zip"
    )
