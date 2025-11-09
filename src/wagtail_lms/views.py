import json
import mimetypes
import os
import time
from datetime import datetime
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from .models import CourseEnrollment, CoursePage, SCORMAttempt, SCORMData, SCORMPackage


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


class SCORMPackageListView(ListView):
    """List all SCORM packages (admin view)"""

    model = SCORMPackage
    template_name = "wagtail_lms/scorm_package_list.html"
    context_object_name = "packages"


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


@login_required
def serve_scorm_content(request, content_path):
    """Serve SCORM content files with proper headers for iframe embedding"""
    # Construct the full file path
    file_path = os.path.join(settings.MEDIA_ROOT, "scorm_content", content_path)

    # Security check: ensure the path is within the SCORM content directory
    scorm_dir = os.path.join(settings.MEDIA_ROOT, "scorm_content")
    if not os.path.commonpath([file_path, scorm_dir]) == scorm_dir:
        raise Http404("File not found")

    # Check if file exists
    if not os.path.exists(file_path):
        raise Http404("File not found")

    # Get the MIME type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"

    # Create response
    response = FileResponse(open(file_path, "rb"), content_type=content_type)

    # Set headers to allow iframe embedding
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["Content-Security-Policy"] = "frame-ancestors 'self'"

    return response
