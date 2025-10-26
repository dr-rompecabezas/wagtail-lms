import django.db.models.deletion
import wagtail.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("wagtailcore", "0094_alter_page_locale"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SCORMPackage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("package_file", models.FileField(upload_to="scorm_packages/")),
                ("extracted_path", models.CharField(blank=True, max_length=500)),
                ("launch_url", models.CharField(blank=True, max_length=500)),
                ("version", models.CharField(default="1.2", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("manifest_data", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "SCORM Package",
                "verbose_name_plural": "SCORM Packages",
            },
        ),
        migrations.CreateModel(
            name="SCORMAttempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("last_accessed", models.DateTimeField(auto_now=True)),
                (
                    "completion_status",
                    models.CharField(
                        choices=[
                            ("incomplete", "Incomplete"),
                            ("completed", "Completed"),
                            ("not_attempted", "Not Attempted"),
                            ("unknown", "Unknown"),
                        ],
                        default="not_attempted",
                        max_length=20,
                    ),
                ),
                (
                    "success_status",
                    models.CharField(
                        choices=[
                            ("passed", "Passed"),
                            ("failed", "Failed"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=20,
                    ),
                ),
                ("score_raw", models.FloatField(blank=True, null=True)),
                ("score_min", models.FloatField(blank=True, null=True)),
                ("score_max", models.FloatField(blank=True, null=True)),
                ("score_scaled", models.FloatField(blank=True, null=True)),
                ("total_time", models.DurationField(blank=True, null=True)),
                ("location", models.CharField(blank=True, max_length=1000)),
                ("suspend_data", models.TextField(blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "scorm_package",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="wagtail_lms.scormpackage",
                    ),
                ),
            ],
            options={
                "verbose_name": "SCORM Attempt",
                "verbose_name_plural": "SCORM Attempts",
            },
        ),
        migrations.CreateModel(
            name="CoursePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                ("description", wagtail.fields.RichTextField(blank=True)),
                (
                    "scorm_package",
                    models.ForeignKey(
                        blank=True,
                        help_text="Select a SCORM package for this course",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="wagtail_lms.scormpackage",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="CourseEnrollment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="wagtail_lms.coursepage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course Enrollment",
                "verbose_name_plural": "Course Enrollments",
                "unique_together": {("user", "course")},
            },
        ),
        migrations.CreateModel(
            name="SCORMData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=255)),
                ("value", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now=True)),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scorm_data",
                        to="wagtail_lms.scormattempt",
                    ),
                ),
            ],
            options={
                "verbose_name": "SCORM Data",
                "verbose_name_plural": "SCORM Data",
                "unique_together": {("attempt", "key")},
            },
        ),
    ]
