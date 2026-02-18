import json
import mimetypes
import posixpath
import time
from datetime import datetime
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.files.storage import default_storage
from django.db import OperationalError, transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from . import conf
from .models import (
    CourseEnrollment,
    CoursePage,
    H5PActivity,
    H5PAttempt,
    H5PXAPIStatement,
    SCORMAttempt,
    SCORMData,
)


def retry_on_db_lock(max_attempts=3, delay=0.1, backoff=2):
    """
    Decorator to retry database operations on OperationalError (database locked).

    This is especially useful for SQLite which has limited concurrency support.
    SCORM packages often make rapid concurrent API calls, causing lock conflicts.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 0.1)
        backoff: Multiplier for delay after each attempt (default: 2)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        # Max retries exceeded, re-raise the exception
                        raise

                    # Only retry on "database is locked" errors
                    if "database is locked" not in str(e).lower():
                        raise

                    # Wait before retrying with exponential backoff
                    time.sleep(current_delay)
                    current_delay *= backoff

            return func(*args, **kwargs)

        return wrapper

    return decorator


@login_required
def scorm_player_view(request, course_id):
    """Display SCORM player for a course"""
    course = get_object_or_404(CoursePage, id=course_id)

    if not course.scorm_package:
        messages.error(request, "This course doesn't have a SCORM package assigned.")
        return redirect("/")

    # Check if SCORM package is properly extracted
    launch_url = course.scorm_package.get_launch_url()
    if not launch_url:
        messages.error(
            request, "SCORM package is not properly extracted or has no launch URL."
        )
        return redirect(course.url)

    # Get or create enrollment
    CourseEnrollment.objects.get_or_create(user=request.user, course=course)

    # Get or create SCORM attempt
    attempt, _ = SCORMAttempt.objects.get_or_create(
        user=request.user,
        scorm_package=course.scorm_package,
        defaults={"completion_status": "incomplete"},
    )

    context = {
        "course": course,
        "scorm_package": course.scorm_package,
        "attempt": attempt,
        "launch_url": launch_url,
    }

    return render(request, "wagtail_lms/scorm_player.html", context)


def handle_scorm_initialize():
    """Handle SCORM Initialize method"""
    return JsonResponse({"result": "true", "errorCode": "0"})


def handle_scorm_terminate(attempt):
    """Handle SCORM Terminate method"""
    attempt.last_accessed = datetime.now()
    attempt.save()
    return JsonResponse({"result": "true", "errorCode": "0"})


def handle_scorm_get_value(attempt, parameters):
    """Handle SCORM GetValue method"""
    key = parameters[0] if parameters else ""
    value = get_scorm_value(attempt, key)
    return JsonResponse({"result": value, "errorCode": "0"})


def handle_scorm_set_value(attempt, parameters):
    """Handle SCORM SetValue method"""
    if len(parameters) >= 2:
        key, value = parameters[0], parameters[1]
        set_scorm_value(attempt, key, value)
        return JsonResponse({"result": "true", "errorCode": "0"})
    return JsonResponse({"result": "false", "errorCode": "201"})


def handle_scorm_commit():
    """Handle SCORM Commit method"""
    # Save any pending data
    return JsonResponse({"result": "true", "errorCode": "0"})


def handle_scorm_get_error_string(parameters):
    """Handle SCORM GetErrorString method"""
    error_code = parameters[0] if parameters else "0"
    return JsonResponse({"result": get_error_string(error_code), "errorCode": "0"})


def handle_scorm_get_last_error():
    """Handle SCORM GetLastError method"""
    return JsonResponse({"result": "0", "errorCode": "0"})


def handle_scorm_get_diagnostic():
    """Handle SCORM GetDiagnostic method"""
    return JsonResponse({"result": "", "errorCode": "0"})


@csrf_exempt
@login_required
def scorm_api_endpoint(request, attempt_id):
    """Handle SCORM API calls"""
    attempt = get_object_or_404(SCORMAttempt, id=attempt_id, user=request.user)

    if request.method != "POST":
        return JsonResponse({"result": "false", "errorCode": "201"})

    try:
        data = json.loads(request.body)
        method = data.get("method")
        parameters = data.get("parameters", [])
    except json.JSONDecodeError:
        return JsonResponse({"result": "false", "errorCode": "201"})

    # Dispatch to appropriate handler
    handlers = {
        "Initialize": lambda: handle_scorm_initialize(),
        "Terminate": lambda: handle_scorm_terminate(attempt),
        "GetValue": lambda: handle_scorm_get_value(attempt, parameters),
        "SetValue": lambda: handle_scorm_set_value(attempt, parameters),
        "Commit": lambda: handle_scorm_commit(),
        "GetErrorString": lambda: handle_scorm_get_error_string(parameters),
        "GetLastError": lambda: handle_scorm_get_last_error(),
        "GetDiagnostic": lambda: handle_scorm_get_diagnostic(),
    }

    handler = handlers.get(method)
    if handler:
        return handler()

    return JsonResponse({"result": "false", "errorCode": "201"})


def get_scorm_value(attempt, key):
    """Get SCORM data value"""
    try:
        scorm_data = SCORMData.objects.get(attempt=attempt, key=key)
    except SCORMData.DoesNotExist:
        # Return default values for common SCORM elements
        defaults = {
            "cmi.core.lesson_status": attempt.completion_status,
            "cmi.core.student_id": str(attempt.user.id),
            "cmi.core.student_name": attempt.user.get_full_name()
            or attempt.user.username,
            "cmi.core.credit": "credit",
            "cmi.core.entry": "ab-initio",
            "cmi.core.lesson_mode": "normal",
            "cmi.core.exit": "",
            "cmi.core.session_time": "",
            "cmi.core.total_time": (
                str(attempt.total_time) if attempt.total_time else "0000:00:00.00"
            ),
            "cmi.core.lesson_location": attempt.location,
            "cmi.suspend_data": attempt.suspend_data,
            "cmi.core.score.raw": (
                str(attempt.score_raw) if attempt.score_raw is not None else ""
            ),
            "cmi.core.score.max": (
                str(attempt.score_max) if attempt.score_max is not None else ""
            ),
            "cmi.core.score.min": (
                str(attempt.score_min) if attempt.score_min is not None else ""
            ),
        }
        return defaults.get(key, "")
    else:
        return scorm_data.value


@retry_on_db_lock(max_attempts=5, delay=0.05, backoff=1.5)
def set_scorm_value(attempt, key, value):  # noqa: C901
    """
    Set SCORM data value with retry logic for database lock errors.

    Uses transaction.atomic() to ensure consistency and @retry_on_db_lock
    to handle SQLite concurrency limitations when SCORM content makes
    rapid concurrent API calls.
    """
    with transaction.atomic():
        # Update attempt fields for core elements
        attempt_modified = False

        if key == "cmi.core.lesson_status":
            attempt.completion_status = value
            attempt_modified = True
        elif key == "cmi.core.lesson_location":
            attempt.location = value
            attempt_modified = True
        elif key == "cmi.suspend_data":
            attempt.suspend_data = value
            attempt_modified = True
        elif key == "cmi.core.score.raw":
            try:
                attempt.score_raw = float(value)
                attempt_modified = True
            except ValueError:
                pass
        elif key == "cmi.core.score.max":
            try:
                attempt.score_max = float(value)
                attempt_modified = True
            except ValueError:
                pass
        elif key == "cmi.core.score.min":
            try:
                attempt.score_min = float(value)
                attempt_modified = True
            except ValueError:
                pass

        # Save attempt if modified
        if attempt_modified:
            attempt.save()

        # Store all data in SCORMData model
        SCORMData.objects.update_or_create(
            attempt=attempt, key=key, defaults={"value": value}
        )


def get_error_string(error_code):
    """Return error message for SCORM error code"""
    error_messages = {
        "0": "No error",
        "101": "General exception",
        "102": "General initialization failure",
        "103": "Already initialized",
        "104": "Content instance terminated",
        "111": "General termination failure",
        "112": "Termination before initialization",
        "113": "Termination after termination",
        "122": "Retrieve data before initialization",
        "123": "Retrieve data after termination",
        "132": "Store data before initialization",
        "133": "Store data after termination",
        "142": "Commit before initialization",
        "143": "Commit after termination",
        "201": "General argument error",
        "301": "General get failure",
        "401": "General set failure",
        "402": "General argument error",
        "403": "Element cannot have children",
        "404": "Element not an array - cannot have count",
        "405": "Element is not an array - cannot have count",
    }
    return error_messages.get(error_code, "Unknown error")


@login_required
def enroll_in_course(request, course_id):
    """Enroll user in a course"""
    course = get_object_or_404(CoursePage, id=course_id)

    _, created = CourseEnrollment.objects.get_or_create(
        user=request.user, course=course
    )

    if created:
        messages.success(request, f"You have been enrolled in {course.title}")
    else:
        messages.info(request, f"You are already enrolled in {course.title}")

    # Redirect to course page or safe referer if course URL is not available
    if course.url:
        return redirect(course.url)

    # Validate referer before using it
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts=settings.ALLOWED_HOSTS, require_https=request.is_secure()
    ):
        return redirect(referer)

    # Fallback to home page
    return redirect("/")


class ServeScormContentView(LoginRequiredMixin, View):
    """Serve SCORM content files with secure path validation.

    Subclass this view to customize caching and redirect behavior while
    preserving upstream security checks.
    """

    def normalize_content_path(self, content_path):
        # Path traversal security: normalize separators then reject ".." and
        # absolute paths. Backslashes are replaced to catch Windows-style paths.
        normalized = content_path.replace("\\", "/")
        normalized = posixpath.normpath(normalized)
        if normalized in {"", "."}:
            raise Http404("File not found")
        if normalized.startswith("/") or normalized.startswith(".."):
            raise Http404("File not found")
        return normalized

    def get_storage_path(self, normalized_content_path):
        content_base = conf.WAGTAIL_LMS_CONTENT_PATH.rstrip("/")
        return posixpath.join(content_base, normalized_content_path)

    def get_content_type(self, content_path):
        content_type, _ = mimetypes.guess_type(content_path)
        return content_type or "application/octet-stream"

    def get_cache_control(self, content_type):
        """Return Cache-Control header value for this MIME type or None."""
        cache_rules = conf.WAGTAIL_LMS_CACHE_CONTROL
        if not isinstance(cache_rules, dict):
            return None

        if content_type in cache_rules:
            return cache_rules[content_type]

        wildcard_matches = []
        for pattern, value in cache_rules.items():
            if pattern.endswith("/*") and content_type.startswith(pattern[:-1]):
                wildcard_matches.append((len(pattern), value))

        if wildcard_matches:
            _, best_match_value = max(wildcard_matches, key=lambda match: match[0])
            return best_match_value

        return cache_rules.get("default")

    def should_redirect(self, content_type, storage_path):
        """Return True to redirect this asset request instead of proxying."""
        if not conf.WAGTAIL_LMS_REDIRECT_MEDIA:
            return False
        return content_type.startswith(("audio/", "video/"))

    def get_redirect_url(self, storage_path):
        return default_storage.url(storage_path)

    def apply_security_headers(self, response):
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["Content-Security-Policy"] = "frame-ancestors 'self'"
        return response

    def apply_cache_header(self, response, content_type):
        cache_control = self.get_cache_control(content_type)
        if cache_control:
            response["Cache-Control"] = cache_control
        return response

    def get(self, request, content_path):
        normalized = self.normalize_content_path(content_path)
        storage_path = self.get_storage_path(normalized)
        content_type = self.get_content_type(normalized)

        if self.should_redirect(content_type, storage_path):
            try:
                response = redirect(self.get_redirect_url(storage_path))
            except (Http404, PermissionDenied, SuspiciousOperation):
                raise
            except Exception:
                raise Http404("File not found") from None
            return self.apply_cache_header(response, content_type)

        try:
            fh = default_storage.open(storage_path, "rb")
        except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
            raise Http404("File not found") from None

        response = FileResponse(fh, content_type=content_type)
        self.apply_security_headers(response)
        self.apply_cache_header(response, content_type)
        return response


class ServeH5PContentView(ServeScormContentView):
    """Serve H5P content files with secure path validation.

    Subclasses ServeScormContentView and overrides only the storage path
    resolution to use the H5P content directory instead of SCORM.
    All security checks, caching, and redirect logic are inherited.
    """

    def get_storage_path(self, normalized_content_path):
        content_base = conf.WAGTAIL_LMS_H5P_CONTENT_PATH.rstrip("/")
        return posixpath.join(content_base, normalized_content_path)


# ---------------------------------------------------------------------------
# H5P xAPI endpoint
# ---------------------------------------------------------------------------

# xAPI verb IRIs that trigger attempt field updates
_XAPI_COMPLETED = "http://adlnet.gov/expapi/verbs/completed"
_XAPI_PASSED = "http://adlnet.gov/expapi/verbs/passed"
_XAPI_FAILED = "http://adlnet.gov/expapi/verbs/failed"
_XAPI_SCORE_VERBS = {
    _XAPI_COMPLETED,
    _XAPI_PASSED,
    _XAPI_FAILED,
    "http://adlnet.gov/expapi/verbs/answered",
    "http://adlnet.gov/expapi/verbs/scored",
}


def _update_h5p_attempt(attempt, statement, verb_id):
    """Update H5PAttempt fields from an xAPI statement.

    Maps xAPI verbs to completion/success status and extracts score data
    from the result object when present.
    """
    modified = False
    result = statement.get("result", {})

    if verb_id == _XAPI_COMPLETED:
        attempt.completion_status = "completed"
        modified = True
    elif verb_id == _XAPI_PASSED:
        attempt.completion_status = "completed"
        attempt.success_status = "passed"
        modified = True
    elif verb_id == _XAPI_FAILED:
        attempt.success_status = "failed"
        modified = True

    if verb_id in _XAPI_SCORE_VERBS:
        score = result.get("score", {})
        if isinstance(score, dict):
            for field, key in (
                ("score_raw", "raw"),
                ("score_max", "max"),
                ("score_min", "min"),
                ("score_scaled", "scaled"),
            ):
                if key in score:
                    try:
                        setattr(attempt, field, float(score[key]))
                        modified = True
                    except (ValueError, TypeError):
                        pass

    if modified:
        attempt.save()


@login_required
def h5p_xapi_view(request, activity_id):
    """Receive and store an xAPI statement from an H5P activity.

    Called by the lesson page JavaScript whenever H5P emits an xAPI event.
    Creates an H5PAttempt on the first interaction (lazy creation), stores
    the raw statement, and updates the attempt's progress fields.

    CSRF protection is active because the POST originates from our own
    page JavaScript, not from inside an iframe we don't control.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    activity = get_object_or_404(H5PActivity, id=activity_id)

    try:
        statement = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Lazy-create the attempt on first interaction
    attempt, _ = H5PAttempt.objects.get_or_create(
        user=request.user,
        activity=activity,
    )

    # Extract verb metadata
    verb = statement.get("verb", {})
    verb_id = verb.get("id", "")
    verb_display_map = verb.get("display", {})
    verb_display = next(iter(verb_display_map.values()), "") if verb_display_map else ""

    # Persist the raw statement
    H5PXAPIStatement.objects.create(
        attempt=attempt,
        verb=verb_id,
        verb_display=verb_display,
        statement=statement,
    )

    # Update attempt progress fields
    _update_h5p_attempt(attempt, statement, verb_id)

    return JsonResponse({"status": "ok"})
