import logging
import os
import posixpath

from django.core.files.storage import FileSystemStorage, default_storage
from django.db import transaction
from django.db.models.signals import post_delete

from . import conf

logger = logging.getLogger(__name__)


def _delete_storage_dir(path):
    """Recursively delete all files under a storage path.

    Works with any Django storage backend. Removes the now-empty directory
    on filesystem-backed storage as a best-effort cleanup.
    """
    try:
        dirs, files = default_storage.listdir(path)
    except FileNotFoundError:
        return

    for filename in files:
        file_path = path + "/" + filename if path else filename
        try:
            default_storage.delete(file_path)
        except Exception:
            logger.exception("Failed to delete file: %s", file_path)

    for dirname in dirs:
        dir_path = path + "/" + dirname if path else dirname
        _delete_storage_dir(dir_path)

    # Remove the now-empty directory on filesystem-backed storage
    if isinstance(default_storage, FileSystemStorage):
        full_path = default_storage.path(path)
        try:
            os.rmdir(full_path)
        except (FileNotFoundError, OSError):
            pass


def _delete_extracted_content(extracted_path, content_base_path):
    """Validate and recursively delete an extracted content directory.

    Args:
        extracted_path: The relative extracted directory name (e.g. 'package_1_foo').
        content_base_path: The configured base path (e.g. conf.WAGTAIL_LMS_SCORM_CONTENT_PATH).
    """
    normalized = posixpath.normpath(extracted_path)
    # Reject anything that isn't a single, plain directory name:
    #   - "." / "" — resolves to the base content directory itself
    #   - starts with ".." — traversal above the base
    #   - starts with "/" — absolute path
    #   - contains "/" — nested path (we only store top-level dirs)
    if (
        not normalized
        or normalized in (".", "..")
        or "/" in normalized
        or normalized.startswith("/")
    ):
        logger.warning(
            "Refusing to delete suspicious extracted_path: %s", extracted_path
        )
        return

    prefix = content_base_path.rstrip("/") + "/" + normalized
    _delete_storage_dir(prefix)


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
                _delete_extracted_content(
                    extracted_path, conf.WAGTAIL_LMS_SCORM_CONTENT_PATH
                )
            except Exception:
                logger.exception(
                    "Failed to delete extracted SCORM content: %s", extracted_path
                )

    transaction.on_commit(_cleanup, using=db_alias)


def post_delete_h5p_cleanup(sender, instance, **kwargs):
    """Delete the uploaded .h5p file and extracted content when an H5PActivity is deleted."""
    db_alias = kwargs.get("using")
    package_file_name = instance.package_file.name if instance.package_file else None
    extracted_path = instance.extracted_path

    def _cleanup():
        if package_file_name:
            try:
                default_storage.delete(package_file_name)
            except Exception:
                logger.exception(
                    "Failed to delete H5P package file: %s", package_file_name
                )

        if extracted_path:
            try:
                _delete_extracted_content(
                    extracted_path, conf.WAGTAIL_LMS_H5P_CONTENT_PATH
                )
            except Exception:
                logger.exception(
                    "Failed to delete extracted H5P content: %s", extracted_path
                )

    transaction.on_commit(_cleanup, using=db_alias)


def register_signal_handlers():
    from .models import H5PActivity, SCORMPackage

    post_delete.connect(
        post_delete_scorm_cleanup,
        sender=SCORMPackage,
        dispatch_uid="wagtail_lms.scormpackage.post_delete_cleanup",
    )

    post_delete.connect(
        post_delete_h5p_cleanup,
        sender=H5PActivity,
        dispatch_uid="wagtail_lms.h5pactivity.post_delete_cleanup",
    )
