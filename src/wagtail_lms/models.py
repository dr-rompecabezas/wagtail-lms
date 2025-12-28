import os
import xml.etree.ElementTree as ET
import zipfile

from django.conf import settings
from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class SCORMPackage(models.Model):
    """Model to store SCORM package information"""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    package_file = models.FileField(upload_to="scorm_packages/")
    extracted_path = models.CharField(max_length=500, blank=True)
    launch_url = models.CharField(max_length=500, blank=True)
    version = models.CharField(max_length=10, default="1.2")  # SCORM version
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata from manifest
    manifest_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "SCORM Package"
        verbose_name_plural = "SCORM Packages"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Save first to ensure file is properly stored
        super().save(*args, **kwargs)

        # Then extract if we have a package file but no extracted path
        if self.package_file and not self.extracted_path:
            self.extract_package()
            # Save again to store the extracted_path and other metadata
            super().save(*args, **kwargs)

    def extract_package(self):
        """Extract SCORM package and parse manifest"""
        if not self.package_file:
            return

        # Create extraction directory with unique path using package ID
        package_name = os.path.splitext(os.path.basename(self.package_file.name))[0]
        unique_dir = f"package_{self.id}_{package_name}"
        extract_dir = f"scorm_content/{unique_dir}"
        full_extract_path = os.path.join(settings.MEDIA_ROOT, extract_dir)

        # Extract ZIP file
        with zipfile.ZipFile(self.package_file.path, "r") as zip_ref:
            zip_ref.extractall(full_extract_path)

        self.extracted_path = unique_dir  # Unique directory name

        # Parse manifest
        manifest_path = os.path.join(full_extract_path, "imsmanifest.xml")
        if os.path.exists(manifest_path):
            self.parse_manifest(manifest_path)

    def parse_manifest(self, manifest_path):
        """Parse SCORM manifest file"""
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()

            # Find the launch URL
            resources = root.find(
                ".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}resources"
            )
            if resources is not None:
                resource = resources.find(
                    './/{http://www.imsproject.org/xsd/imscp_rootv1p1p2}resource[@type="webcontent"]'
                )
                if resource is not None:
                    self.launch_url = resource.get("href", "")

            # Store manifest metadata
            self.manifest_data = {
                "title": self.get_manifest_title(root),
                "version": self.get_scorm_version(root),
                "launch_url": self.launch_url,
            }

            # Update title if not set
            if not self.title and self.manifest_data.get("title"):
                self.title = self.manifest_data["title"]

        except Exception as e:
            print(f"Error parsing manifest: {e}")

    def get_manifest_title(self, root):
        """Extract title from manifest"""
        title_elem = root.find(
            ".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}title"
        )
        return title_elem.text if title_elem is not None else ""

    def get_scorm_version(self, root):
        """Determine SCORM version from manifest.

        Uses a flexible search for schemaversion element that works with
        both namespaced and non-namespaced XML using ElementTree.
        """
        # Known SCORM 2004 schemaversion values
        scorm_2004_versions = [
            "2004 3rd Edition",
            "2004 4th Edition",
            "CAM 1.3",
            "2004",
        ]

        # Search for schemaversion element - works with any namespace
        for element in root.iter():
            # Match either namespaced or non-namespaced schemaversion tags
            if element.tag.endswith("schemaversion") or element.tag == "schemaversion":
                if element.text:
                    text = element.text.strip()
                    # Check against known SCORM 2004 version strings
                    for version in scorm_2004_versions:
                        if text.startswith(version):
                            return "2004"

        return "1.2"

    def get_launch_url(self):
        """Get full URL to launch SCORM content"""
        if self.extracted_path and self.launch_url:
            # Use custom SCORM content serving URL to avoid iframe restrictions
            return f"/lms/scorm-content/{self.extracted_path}/{self.launch_url}"
        return None


class CoursePage(Page):
    """Wagtail page for courses"""

    description = RichTextField(blank=True)
    scorm_package = models.ForeignKey(
        SCORMPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select a SCORM package for this course",
    )

    content_panels = [
        *Page.content_panels,
        FieldPanel("description"),
        FieldPanel("scorm_package"),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        # Add enrollment and progress data if user is authenticated
        # Only query if page is saved (has a pk) to avoid preview errors
        if request.user.is_authenticated and self.pk:
            try:
                enrollment = CourseEnrollment.objects.get(
                    user=request.user, course=self
                )
                context["enrollment"] = enrollment
                context["progress"] = enrollment.get_progress()
            except CourseEnrollment.DoesNotExist:
                context["enrollment"] = None
                context["progress"] = None
        else:
            # In preview mode or not authenticated
            context["enrollment"] = None
            context["progress"] = None

        return context


class CourseEnrollment(models.Model):
    """Track user enrollment in courses"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(CoursePage, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "course")
        verbose_name = "Course Enrollment"
        verbose_name_plural = "Course Enrollments"

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

    def get_progress(self):
        """Get user's progress in this course"""
        if not self.course.scorm_package:
            return None

        try:
            attempt = SCORMAttempt.objects.filter(
                user=self.user, scorm_package=self.course.scorm_package
            ).latest("started_at")
        except SCORMAttempt.DoesNotExist:
            return None
        else:
            return attempt


class SCORMAttempt(models.Model):
    """Track individual SCORM learning attempts"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scorm_package = models.ForeignKey(SCORMPackage, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)

    # SCORM tracking fields
    completion_status = models.CharField(
        max_length=20,
        choices=[
            ("incomplete", "Incomplete"),
            ("completed", "Completed"),
            ("not_attempted", "Not Attempted"),
            ("unknown", "Unknown"),
        ],
        default="not_attempted",
    )

    success_status = models.CharField(
        max_length=20,
        choices=[
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
    )

    score_raw = models.FloatField(null=True, blank=True)
    score_min = models.FloatField(null=True, blank=True)
    score_max = models.FloatField(null=True, blank=True)
    score_scaled = models.FloatField(null=True, blank=True)

    total_time = models.DurationField(null=True, blank=True)
    location = models.CharField(max_length=1000, blank=True)
    suspend_data = models.TextField(blank=True)

    class Meta:
        verbose_name = "SCORM Attempt"
        verbose_name_plural = "SCORM Attempts"

    def __str__(self):
        return f"{self.user.username} - {self.scorm_package.title} ({self.completion_status})"


class SCORMData(models.Model):
    """Store SCORM runtime data (cmi data model)"""

    attempt = models.ForeignKey(
        SCORMAttempt, on_delete=models.CASCADE, related_name="scorm_data"
    )
    key = models.CharField(max_length=255)  # e.g., 'cmi.core.lesson_status'
    value = models.TextField()
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("attempt", "key")
        verbose_name = "SCORM Data"
        verbose_name_plural = "SCORM Data"

    def __str__(self):
        return f"{self.attempt} - {self.key}: {self.value[:50]}"
