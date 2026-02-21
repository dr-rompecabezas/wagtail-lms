import io
import json
import logging
import os
import posixpath
import xml.etree.ElementTree as ET
import zipfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.db import models, transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.module_loading import import_string
from wagtail.admin.panels import FieldPanel, TitleFieldPanel
from wagtail.blocks import RichTextBlock, StructBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.snippets.models import register_snippet

from . import conf

logger = logging.getLogger(__name__)


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

    panels = [
        TitleFieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("package_file"),
        FieldPanel("version"),
        FieldPanel("extracted_path", read_only=True),
        FieldPanel("launch_url", read_only=True),
    ]

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
        """Extract SCORM package and parse manifest.

        Uses Django's default_storage API so extraction works with any
        storage backend (local filesystem, S3, etc.).
        """
        if not self.package_file:
            return

        # Create extraction directory with unique path using package ID
        package_name = os.path.splitext(os.path.basename(self.package_file.name))[0]
        unique_dir = f"package_{self.id}_{package_name}"
        content_path = conf.WAGTAIL_LMS_SCORM_CONTENT_PATH.rstrip("/")

        manifest_content = None

        # Open file via storage API (works with any backend — no .path needed)
        with self.package_file.open("rb") as package_fh:
            with zipfile.ZipFile(package_fh, "r") as zip_ref:
                for member in zip_ref.infolist():
                    # Skip directories
                    if member.is_dir():
                        continue

                    # Path traversal security: normalize separators, then
                    # reject members with ".." segments, absolute paths, or
                    # names that collapse to "." (e.g. "a/..").
                    # Backslashes are normalized to forward slashes to catch
                    # Windows-style traversal in crafted ZIPs.
                    normalized = member.filename.replace("\\", "/")
                    normalized = posixpath.normpath(normalized)
                    if (
                        normalized == "."
                        or normalized.startswith("/")
                        or normalized.startswith("..")
                        or "/../" in normalized
                    ):
                        logger.warning(
                            "Skipping suspicious ZIP member: %s", member.filename
                        )
                        continue

                    file_data = zip_ref.read(member.filename)

                    # Capture manifest in-memory to avoid an extra storage
                    # round-trip
                    if member.filename == "imsmanifest.xml":
                        manifest_content = file_data

                    storage_path = posixpath.join(
                        content_path, unique_dir, member.filename
                    )
                    default_storage.save(storage_path, ContentFile(file_data))

        self.extracted_path = unique_dir

        # Parse manifest
        if manifest_content is not None:
            self.parse_manifest(io.BytesIO(manifest_content))

    def parse_manifest(self, manifest_source):
        """Parse SCORM manifest file.

        Args:
            manifest_source: A file path (str) or a file-like object
                (e.g. io.BytesIO). ET.parse() accepts both.
        """
        try:
            tree = ET.parse(manifest_source)
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


def _h5p_package_upload_path(instance, filename):
    return f"{conf.WAGTAIL_LMS_H5P_UPLOAD_PATH}{filename}"


@register_snippet
class H5PActivity(models.Model):
    """Reusable H5P interactive activity, managed as a Wagtail snippet.

    Authors upload a .h5p file here. The package is extracted on save and
    the activity can then be embedded in any LessonPage via H5PActivityBlock.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    package_file = models.FileField(upload_to=_h5p_package_upload_path)
    extracted_path = models.CharField(max_length=500, blank=True)
    main_library = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata from h5p.json
    h5p_json = models.JSONField(default=dict, blank=True)

    panels = [
        TitleFieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("package_file"),
        FieldPanel("extracted_path", read_only=True),
        FieldPanel("main_library", read_only=True),
    ]

    class Meta:
        verbose_name = "H5P Activity"
        verbose_name_plural = "H5P Activities"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Detect package file replacement on an existing record so we can
        # re-extract and schedule cleanup of the superseded content.
        old_package_name, old_extracted_path = self._get_previous_package_state()
        package_replaced = self._is_package_replaced(old_package_name)
        should_extract = bool(
            self.package_file and (package_replaced or not self.extracted_path)
        )

        # Save first to ensure the new file is properly stored.
        super().save(*args, **kwargs)

        # Extract when creating for the first time or when replacing package file.
        # This covers both first-time creation and package replacement.
        if should_extract:
            if package_replaced:
                # Reset derived fields only in memory so failed extraction does
                # not persist blank metadata/extraction path.
                self.extracted_path = ""
                self.main_library = ""
                self.h5p_json = {}

            same_path_existing_files = (
                self._get_same_path_replacement_existing_files(old_extracted_path)
                if package_replaced
                else None
            )

            extracted_file_paths = self.extract_package()
            # Strip force_insert / force_update: the row already exists after
            # the first save, so reusing force_insert=True (passed by
            # objects.create()) would attempt a duplicate INSERT and raise
            # IntegrityError.
            post_extract_kwargs = self._get_post_extract_save_kwargs(kwargs)
            super().save(*args, **post_extract_kwargs)

            if same_path_existing_files is not None:
                self._cleanup_stale_same_path_files_after_reextract(
                    same_path_existing_files, extracted_file_paths
                )

            if package_replaced:
                self._schedule_replaced_content_cleanup(
                    old_package_name,
                    old_extracted_path,
                    self.package_file.name,
                    self.extracted_path,
                )

    def _get_previous_package_state(self):
        """Return previous package file name and extracted path for this record."""
        if not self.pk:
            return None, None

        try:
            prev = H5PActivity.objects.only("package_file", "extracted_path").get(
                pk=self.pk
            )
        except H5PActivity.DoesNotExist:
            return None, None

        old_package_name = prev.package_file.name if prev.package_file else None
        return old_package_name, prev.extracted_path

    def _is_package_replaced(self, old_package_name):
        """Return True when a new package upload replaces an existing one."""
        if old_package_name is None or not self.package_file:
            return False

        # FieldFile._committed=False means a new upload was assigned, including
        # overwrite-style storages that keep the same key/name.
        if not getattr(self.package_file, "_committed", True):
            return True

        new_package_name = self.package_file.name
        return new_package_name is not None and new_package_name != old_package_name

    def _get_same_path_replacement_existing_files(self, old_extracted_path):
        """Return existing extracted files for same-path replacement cleanup."""
        if not old_extracted_path:
            return None

        new_extracted_path = self._get_extraction_dir_name()
        if not new_extracted_path or new_extracted_path != old_extracted_path:
            return None

        content_path = conf.WAGTAIL_LMS_H5P_CONTENT_PATH.rstrip("/")
        extraction_root = posixpath.join(content_path, old_extracted_path)
        existing_files = self._list_storage_files(extraction_root)
        if existing_files is None:
            logger.warning(
                "Failed to list old H5P extracted content before re-extracting "
                "replacement: %s",
                old_extracted_path,
            )
        return existing_files

    def _list_storage_files(self, storage_path):
        """Return recursive file paths under storage_path, or None on failure."""
        try:
            dirs, files = default_storage.listdir(storage_path)
        except FileNotFoundError:
            return set()
        except Exception:
            return None

        collected = {posixpath.join(storage_path, filename) for filename in files}
        for dirname in dirs:
            nested = self._list_storage_files(posixpath.join(storage_path, dirname))
            if nested is None:
                return None
            collected.update(nested)
        return collected

    def _cleanup_stale_same_path_files_after_reextract(
        self, old_file_paths, extracted_file_paths
    ):
        """Delete files that existed before replacement but not in the new package."""
        if not old_file_paths:
            return

        stale_paths = old_file_paths - (extracted_file_paths or set())
        for stale_path in stale_paths:
            try:
                default_storage.delete(stale_path)
            except Exception:
                logger.warning(
                    "Failed to delete stale H5P extracted file after replacement: %s",
                    stale_path,
                )

    def _get_post_extract_save_kwargs(self, kwargs):
        """Return save kwargs for persisting extracted metadata fields."""
        post_extract_kwargs = kwargs.copy()
        post_extract_kwargs.pop("force_insert", None)
        post_extract_kwargs.pop("force_update", None)

        update_fields = post_extract_kwargs.get("update_fields")
        if update_fields is not None:
            persisted_fields = set(update_fields)
            persisted_fields.update(
                {"extracted_path", "main_library", "h5p_json", "title"}
            )
            post_extract_kwargs["update_fields"] = list(persisted_fields)

        return post_extract_kwargs

    def _get_extraction_dir_name(self):
        """Return the deterministic extracted directory name for this package."""
        if not self.package_file or not self.pk:
            return ""

        package_name = os.path.splitext(os.path.basename(self.package_file.name))[0]
        return f"h5p_{self.pk}_{package_name}"

    def _schedule_replaced_content_cleanup(
        self,
        old_package_name,
        old_extracted_path,
        new_package_name,
        new_extracted_path,
    ):
        """Schedule deletion of superseded package file and extracted content.

        Called after a successful package replacement save. Runs on transaction
        commit so a rollback cannot discard the originals prematurely.

        Paths that coincide with the newly saved files are skipped — this
        guards against storage backends that reuse the same key (e.g. S3 with
        overwrite enabled, or custom upload_to functions that produce the same
        basename for different uploads).
        """
        from .signal_handlers import _delete_extracted_content

        _old_pkg = old_package_name if old_package_name != new_package_name else None
        _old_ext = (
            old_extracted_path if old_extracted_path != new_extracted_path else None
        )

        def _cleanup():
            if _old_pkg:
                try:
                    default_storage.delete(_old_pkg)
                except Exception:
                    logger.warning(
                        "Failed to delete replaced H5P package file: %s", _old_pkg
                    )
            if _old_ext:
                try:
                    _delete_extracted_content(
                        _old_ext, conf.WAGTAIL_LMS_H5P_CONTENT_PATH
                    )
                except Exception:
                    logger.warning(
                        "Failed to delete replaced H5P extracted content: %s", _old_ext
                    )

        transaction.on_commit(_cleanup)

    def clean(self):
        """Validate the uploaded .h5p package before saving.

        Checks ZIP integrity (CRC) so a corrupted upload surfaces as a
        user-visible form validation error rather than an unhandled 500.

        Accesses the underlying UploadedFile directly rather than via
        FieldFile.open(), because FieldFile.open() used in a ``with``
        block closes (and on macOS/Linux deletes) the TemporaryUploadedFile
        before save() can commit it to storage.
        """
        # Only validate freshly uploaded files. For existing saved files
        # (editing without changing the package) there is nothing to check.
        raw_file = getattr(self.package_file, "_file", None)
        if not isinstance(raw_file, UploadedFile):
            return

        try:
            raw_file.seek(0)
            with zipfile.ZipFile(raw_file) as zf:
                bad_file = zf.testzip()
            raw_file.seek(0)  # Reset so save() can read the file.
        except zipfile.BadZipFile as exc:
            raise ValidationError(
                {
                    "package_file": (
                        f"The uploaded file is not a valid ZIP archive: {exc}"
                    )
                }
            ) from exc

        if bad_file is not None:
            raise ValidationError(
                {
                    "package_file": (
                        f"The uploaded file is corrupted "
                        f"(CRC error in '{bad_file}'). "
                        "Please re-download and try again."
                    )
                }
            )

    def extract_package(self):
        """Extract H5P package and parse h5p.json.

        Uses Django's default_storage API so extraction works with any
        storage backend (local filesystem, S3, etc.).
        """
        if not self.package_file:
            return set()

        # Create extraction directory with a deterministic path using package ID
        unique_dir = self._get_extraction_dir_name()
        content_path = conf.WAGTAIL_LMS_H5P_CONTENT_PATH.rstrip("/")

        h5p_json_content = None
        has_library_files = False
        extracted_file_paths = set()

        # Open file via storage API (works with any backend — no .path needed)
        with self.package_file.open("rb") as package_fh:
            with zipfile.ZipFile(package_fh, "r") as zip_ref:
                for member in zip_ref.infolist():
                    # Skip directories
                    if member.is_dir():
                        continue

                    # Path traversal security: normalize separators, then
                    # reject members with ".." segments, absolute paths, or
                    # names that collapse to "." (e.g. "a/..").
                    # Backslashes are normalized to forward slashes to catch
                    # Windows-style traversal in crafted ZIPs.
                    normalized = member.filename.replace("\\", "/")
                    normalized = posixpath.normpath(normalized)
                    if (
                        normalized == "."
                        or normalized.startswith("/")
                        or normalized.startswith("..")
                        or "/../" in normalized
                    ):
                        logger.warning(
                            "Skipping suspicious ZIP member: %s", member.filename
                        )
                        continue

                    try:
                        file_data = zip_ref.read(member.filename)
                    except zipfile.BadZipFile:
                        logger.exception(
                            "CRC error reading '%s' from H5P package '%s'. "
                            "Upload a valid .h5p file.",
                            member.filename,
                            self.package_file.name,
                        )
                        raise

                    # Capture h5p.json in-memory for immediate parsing
                    if member.filename == "h5p.json":
                        h5p_json_content = file_data

                    # Detect library directories (e.g. H5P.InteractiveVideo-1.27/)
                    if "/" in normalized and not normalized.startswith("content/"):
                        has_library_files = True

                    storage_path = posixpath.join(
                        content_path, unique_dir, member.filename
                    )
                    # Replacements can re-use the same extracted path. Delete first
                    # so storages that auto-rename on collisions keep canonical names.
                    default_storage.delete(storage_path)
                    default_storage.save(storage_path, ContentFile(file_data))
                    extracted_file_paths.add(storage_path)

        self.extracted_path = unique_dir

        if not has_library_files:
            logger.warning(
                "H5P package '%s' contains no library files. "
                "h5p-standalone requires a self-contained package that includes "
                "library JS files (e.g. H5P.InteractiveVideo-1.27/). "
                "Download the .h5p from an H5P editor (H5P.org editor, Moodle, "
                "WordPress) rather than using an H5P.org 'Reuse' export.",
                self.package_file.name,
            )

        # Parse h5p.json metadata
        if h5p_json_content is not None:
            self.parse_h5p_json(h5p_json_content)

        return extracted_file_paths

    def parse_h5p_json(self, content):
        """Parse h5p.json to extract package metadata.

        Args:
            content: Raw bytes of h5p.json file content.
        """
        try:
            data = json.loads(content)
            self.h5p_json = data
            self.main_library = data.get("mainLibrary", "")
            # Update title from h5p.json if not already set
            if not self.title and data.get("title"):
                self.title = data["title"]
        except Exception as e:
            logger.warning("Error parsing h5p.json: %s", e)

    def get_content_base_url(self):
        """Get the base URL path for h5p-standalone player initialization.

        The player appends /h5p.json, /content/content.json, etc. to this URL.
        Uses URL reversal so the path respects whatever mount point the project
        uses for wagtail_lms.urls (e.g. /lms/, /courses/, /).
        """
        if self.extracted_path:
            return reverse("wagtail_lms:serve_h5p_content", args=[self.extracted_path])
        return None


class H5PActivityBlock(StructBlock):
    """StreamField block for embedding an H5P activity inline in a lesson."""

    activity = SnippetChooserBlock(H5PActivity)

    class Meta:
        icon = "media"
        label = "H5P Activity"
        template = "wagtail_lms/blocks/h5p_activity_block.html"


class CoursePage(Page):
    """Wagtail page for courses.

    Can contain SCORM content (via scorm_package) or H5P-powered lessons
    (as LessonPage children). These are two distinct delivery modes.
    """

    subpage_types = ["wagtail_lms.LessonPage"]

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

        # Live LessonPage children, ordered by page tree position
        context["lesson_pages"] = (
            self.get_children().live().type(LessonPage).order_by("path")
            if self.pk
            else self.__class__.objects.none()
        )

        # Per-lesson completion set for H5P courses (empty for SCORM / preview)
        if request.user.is_authenticated and self.pk and context["lesson_pages"]:
            context["completed_lesson_ids"] = set(
                LessonCompletion.objects.filter(
                    user=request.user,
                    lesson_id__in=context["lesson_pages"].values_list("pk", flat=True),
                ).values_list("lesson_id", flat=True)
            )
        else:
            context["completed_lesson_ids"] = set()

        return context


class LessonPage(Page):
    """A long-scroll lesson page, child of CoursePage.

    Composes rich text and H5P activities into a single scrollable page.
    Access is gated to users enrolled in the parent CoursePage.
    """

    parent_page_types = None
    subpage_types = []

    intro = RichTextField(blank=True)
    body = StreamField(
        [
            ("paragraph", RichTextBlock()),
            ("h5p_activity", H5PActivityBlock()),
        ],
        blank=True,
    )

    content_panels = [
        *Page.content_panels,
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    @property
    def has_h5p_activity_blocks(self):
        return any(block.block_type == "h5p_activity" for block in self.body)

    def serve(self, request):
        """Gate lesson access to authenticated, enrolled users.

        Wagtail admin users can always access lessons for editing/preview.
        Regular users must be enrolled in the parent CoursePage.
        """
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        # Wagtail editors can access without enrollment
        if request.user.has_perm("wagtailadmin.access_admin"):
            return super().serve(request)

        # Check lesson access via configurable callable.
        parent_page = self.get_parent()
        course_page = parent_page.specific
        check_access = import_string(conf.WAGTAIL_LMS_CHECK_LESSON_ACCESS)

        if not check_access(request, self, course_page):
            messages.error(
                request,
                "You must be enrolled in this course to access this lesson.",
            )
            return redirect(course_page.url)

        return super().serve(request)


class CourseEnrollment(models.Model):
    """Track user enrollment in courses"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(CoursePage, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    panels = [
        FieldPanel("user"),
        FieldPanel("course"),
        FieldPanel("enrolled_at", read_only=True),
        FieldPanel("completed_at", read_only=True),
    ]

    class Meta:
        unique_together = ("user", "course")
        verbose_name = "Course Enrollment"
        verbose_name_plural = "Course Enrollments"

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

    def get_progress(self):
        """Get user's progress in this course (SCORM courses only)."""
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


class LessonCompletion(models.Model):
    """Track per-lesson completion for H5P-powered lessons.

    Created when all H5P activities in a LessonPage have been completed by the
    user. Acts as the middle layer between CourseEnrollment and H5PAttempt,
    enabling course completion to be determined by a simple all-lessons-complete
    query rather than iterating StreamField blocks on every xAPI event.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(LessonPage, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    panels = [
        FieldPanel("user", read_only=True),
        FieldPanel("lesson", read_only=True),
        FieldPanel("completed_at", read_only=True),
    ]

    class Meta:
        unique_together = ("user", "lesson")
        verbose_name = "Lesson Completion"
        verbose_name_plural = "Lesson Completions"

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"


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

    panels = [
        FieldPanel("user", read_only=True),
        FieldPanel("scorm_package", read_only=True),
        FieldPanel("completion_status", read_only=True),
        FieldPanel("success_status", read_only=True),
        FieldPanel("score_raw", read_only=True),
        FieldPanel("score_min", read_only=True),
        FieldPanel("score_max", read_only=True),
        FieldPanel("score_scaled", read_only=True),
        FieldPanel("total_time", read_only=True),
        FieldPanel("location", read_only=True),
        FieldPanel("started_at", read_only=True),
        FieldPanel("last_accessed", read_only=True),
    ]

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


class H5PAttempt(models.Model):
    """Track progress for an individual H5P activity.

    Created lazily on the first xAPI event from the learner. One record
    per user + activity combination.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity = models.ForeignKey(H5PActivity, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)

    completion_status = models.CharField(
        max_length=20,
        choices=[
            ("not_attempted", "Not Attempted"),
            ("incomplete", "Incomplete"),
            ("completed", "Completed"),
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

    panels = [
        FieldPanel("user", read_only=True),
        FieldPanel("activity", read_only=True),
        FieldPanel("completion_status", read_only=True),
        FieldPanel("success_status", read_only=True),
        FieldPanel("score_raw", read_only=True),
        FieldPanel("score_min", read_only=True),
        FieldPanel("score_max", read_only=True),
        FieldPanel("score_scaled", read_only=True),
        FieldPanel("started_at", read_only=True),
        FieldPanel("last_accessed", read_only=True),
    ]

    class Meta:
        verbose_name = "H5P Attempt"
        verbose_name_plural = "H5P Attempts"
        unique_together = [("user", "activity")]

    def __str__(self):
        return (
            f"{self.user.username} - {self.activity.title} ({self.completion_status})"
        )


class H5PXAPIStatement(models.Model):
    """Store xAPI statements emitted by H5P content.

    One record per statement. Provides a granular audit trail useful for
    debugging and future reporting features.
    """

    attempt = models.ForeignKey(
        H5PAttempt, on_delete=models.CASCADE, related_name="xapi_statements"
    )
    verb = models.CharField(max_length=255)  # xAPI verb IRI
    verb_display = models.CharField(max_length=255, blank=True)  # Human-readable label
    statement = models.JSONField()  # Full xAPI statement
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "H5P xAPI Statement"
        verbose_name_plural = "H5P xAPI Statements"

    def __str__(self):
        return f"{self.attempt} - {self.verb_display or self.verb}"


class H5PContentUserData(models.Model):
    """Persist H5P content user data used for resume/progress state.

    Mirrors the H5P "content user data" concept keyed by:
      - attempt (user + activity)
      - data_type (e.g. "state")
      - sub_content_id (nested content part, usually 0)
    """

    attempt = models.ForeignKey(
        H5PAttempt,
        on_delete=models.CASCADE,
        related_name="content_user_data",
    )
    data_type = models.CharField(max_length=255)
    sub_content_id = models.PositiveIntegerField(default=0)
    value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "H5P Content User Data"
        verbose_name_plural = "H5P Content User Data"
        unique_together = [("attempt", "data_type", "sub_content_id")]

    def __str__(self):
        return f"{self.attempt} - {self.data_type}[{self.sub_content_id}]"
