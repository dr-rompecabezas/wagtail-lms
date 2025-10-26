from django.contrib import admin

from .models import CourseEnrollment, SCORMAttempt, SCORMData, SCORMPackage


@admin.register(SCORMPackage)
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


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at", "completed_at")
    list_filter = ("enrolled_at", "completed_at")
    search_fields = ("user__username", "course__title")


@admin.register(SCORMAttempt)
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


@admin.register(SCORMData)
class SCORMDataAdmin(admin.ModelAdmin):
    list_display = ("attempt", "key", "value_preview", "timestamp")
    list_filter = ("key", "timestamp")
    search_fields = ("attempt__user__username", "key", "value")

    def value_preview(self, obj):
        return obj.value[:50] + "..." if len(obj.value) > 50 else obj.value

    value_preview.short_description = "Value Preview"
