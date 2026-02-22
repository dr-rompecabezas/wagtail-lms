"""Lesson access helpers."""

from .models import CourseEnrollment


def default_lesson_access_check(request, lesson_page, course_page):
    """Return True when the user can access a lesson."""
    return CourseEnrollment.objects.filter(
        user=request.user,
        course__page_ptr_id=course_page.pk,
    ).exists()
