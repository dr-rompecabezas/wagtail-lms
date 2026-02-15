import logging
import os
import posixpath

from django.core.files.storage import FileSystemStorage, default_storage
from django.db import transaction
from django.db.models.signals import post_delete

from . import conf

logger = logging.getLogger(__name__)


def _delete_extracted_content(extracted_path):
    """Recursively delete all files and directories under the extracted content path."""
    # Validate extracted_path against path traversal
    normalized = posixpath.normpath(extracted_path)
    if (
        normalized.startswith("/")
        or normalized.startswith("..")
        or "/../" in normalized
    ):
        logger.warning(
            "Refusing to delete suspicious extracted_path: %s", extracted_path
        )
        return

    prefix = conf.WAGTAIL_LMS_CONTENT_PATH.rstrip("/") + "/" + normalized

    def _delete_dir(path):
        try:
            dirs, files = default_storage.listdir(path)
        except FileNotFoundError:
            return

        for filename in files:
            file_path = path + "/" + filename if path else filename
            try:
                default_storage.delete(file_path)
            except Exception:
                logger.exception("Failed to delete extracted file: %s", file_path)

        for dirname in dirs:
            dir_path = path + "/" + dirname if path else dirname
            _delete_dir(dir_path)

        # Remove the now-empty directory on filesystem-backed storage
        if isinstance(default_storage, FileSystemStorage):
            full_path = default_storage.path(path)
            try:
                os.rmdir(full_path)
            except (FileNotFoundError, OSError):
                pass

    _delete_dir(prefix)


def post_delete_scorm_cleanup(sender, instance, **kwargs):
    """Delete the uploaded ZIP and extracted content when a SCORMPackage is deleted."""
    db_alias = kwargs.get("using")
    package_file_name = instance.package_file.name if instance.package_file else None
    extracted_path = instance.extracted_path

    def _cleanup():
        if package_file_name:
            try:
                default_storage.delete(package_file_name)
            except Exception:
                logger.exception("Failed to delete package file: %s", package_file_name)

        if extracted_path:
            try:
                _delete_extracted_content(extracted_path)
            except Exception:
                logger.exception(
                    "Failed to delete extracted content: %s", extracted_path
                )

    transaction.on_commit(_cleanup, using=db_alias)


def register_signal_handlers():
    from .models import SCORMPackage

    post_delete.connect(
        post_delete_scorm_cleanup,
        sender=SCORMPackage,
        dispatch_uid="wagtail_lms.scormpackage.post_delete_cleanup",
    )
