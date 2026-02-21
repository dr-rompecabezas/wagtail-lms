from django.contrib import admin
from django.utils.module_loading import import_string

from . import conf
from .models import (
    CourseEnrollment,
    H5PActivity,
    H5PAttempt,
    H5PContentUserData,
    H5PXAPIStatement,
    LessonCompletion,
    SCORMAttempt,
    SCORMData,
    SCORMPackage,
)


class SCORMPackageAdmin(admin.ModelAdmin):
    list_display = ("title", "version", "created_at", "launch_url")
    list_filter = ("version", "created_at")
    search_fields = ("title", "description")
    readonly_fields = (
        "extracted_path",
        "launch_url",
        "manifest_data",
        "created_at",
        "updated_at",
    )


class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at", "completed_at")
    list_filter = ("enrolled_at", "completed_at")
    search_fields = ("user__username", "course__title")


class SCORMAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "scorm_package",
        "completion_status",
        "success_status",
        "started_at",
        "last_accessed",
    )
    list_filter = ("completion_status", "success_status", "started_at")
    search_fields = ("user__username", "scorm_package__title")


class SCORMDataAdmin(admin.ModelAdmin):
    list_display = ("attempt", "key", "value_preview", "timestamp")
    list_filter = ("key", "timestamp")
    search_fields = ("attempt__user__username", "key", "value")

    def value_preview(self, obj):
        return obj.value[:50] + "..." if len(obj.value) > 50 else obj.value

    value_preview.short_description = "Value Preview"


class H5PActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "main_library", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "description", "main_library")
    readonly_fields = (
        "extracted_path",
        "main_library",
        "h5p_json",
        "created_at",
        "updated_at",
    )


class H5PAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "activity",
        "completion_status",
        "success_status",
        "started_at",
        "last_accessed",
    )
    list_filter = ("completion_status", "success_status", "started_at")
    search_fields = ("user__username", "activity__title")


class H5PXAPIStatementAdmin(admin.ModelAdmin):
    list_display = ("attempt", "verb_display", "timestamp")
    list_filter = ("timestamp",)
    search_fields = ("attempt__user__username", "verb", "verb_display")


class H5PContentUserDataAdmin(admin.ModelAdmin):
    list_display = ("attempt", "data_type", "sub_content_id", "updated_at")
    list_filter = ("data_type", "updated_at")
    search_fields = ("attempt__user__username", "attempt__activity__title", "data_type")


class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "completed_at")
    list_filter = ("completed_at",)
    search_fields = ("user__username", "lesson__title")


def _import_admin_class(dotted_path):
    admin_class = import_string(dotted_path)
    if not issubclass(admin_class, admin.ModelAdmin):
        raise TypeError(f"{dotted_path} is not a Django ModelAdmin subclass")
    return admin_class


def _register_django_admin():
    if not conf.WAGTAIL_LMS_REGISTER_DJANGO_ADMIN:
        return

    scorm_admin_class = _import_admin_class(conf.WAGTAIL_LMS_SCORM_ADMIN_CLASS)
    h5p_admin_class = _import_admin_class(conf.WAGTAIL_LMS_H5P_ADMIN_CLASS)

    admin.site.register(SCORMPackage, scorm_admin_class)
    admin.site.register(CourseEnrollment, CourseEnrollmentAdmin)
    admin.site.register(SCORMAttempt, SCORMAttemptAdmin)
    admin.site.register(SCORMData, SCORMDataAdmin)
    admin.site.register(H5PActivity, h5p_admin_class)
    admin.site.register(H5PAttempt, H5PAttemptAdmin)
    admin.site.register(H5PXAPIStatement, H5PXAPIStatementAdmin)
    admin.site.register(H5PContentUserData, H5PContentUserDataAdmin)
    admin.site.register(LessonCompletion, LessonCompletionAdmin)


_register_django_admin()
