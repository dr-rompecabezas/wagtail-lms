import django.db.models.deletion
import wagtail.fields
from django.db import migrations, models


def forward_migrate_scorm_packages(apps, schema_editor):
    """Create a SCORMLessonPage child for each CoursePage that has a scorm_package.

    Uses historical model for the CoursePage query (scorm_package still exists at
    this point in migration history) and real model classes for Wagtail tree
    operations (add_child requires the live model, not the historical proxy).
    This is a forward-only migration.
    """
    from wagtail_lms.models import CoursePage, SCORMLessonPage

    # Use historical CoursePage to access scorm_package (field removed in this migration)
    HistoricalCoursePage = apps.get_model("wagtail_lms", "CoursePage")

    from wagtail.models import Page

    for hist_course in HistoricalCoursePage.objects.filter(
        scorm_package__isnull=False
    ).iterator():
        course = CoursePage.objects.get(pk=hist_course.pk)

        # Generate a slug that is unique among the course's existing children
        base_slug = f"scorm-{course.id}"
        existing_slugs = set(
            Page.objects.child_of(course).values_list("slug", flat=True)
        )
        slug = base_slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1

        lesson = SCORMLessonPage(
            title=f"{course.title} - SCORM Content",
            slug=slug,
            scorm_package_id=hist_course.scorm_package_id,
        )
        course.add_child(instance=lesson)
        # Mirror the parent's live status without triggering Wagtail's
        # full publish workflow (signals, notifications, etc.) inside a migration.
        lesson.live = course.live
        lesson.has_unpublished_changes = False
        lesson.save(update_fields=["live", "has_unpublished_changes"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        (
            "wagtail_lms",
            "0003_alter_lessonpage_body",
        ),
        ("wagtailcore", "0091_remove_revision_submitted_for_moderation"),
    ]

    operations = [
        migrations.CreateModel(
            name="SCORMLessonPage",
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
                ("intro", wagtail.fields.RichTextField(blank=True)),
                (
                    "scorm_package",
                    models.ForeignKey(
                        blank=True,
                        help_text="Select a SCORM package for this lesson",
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
        migrations.RunPython(
            forward_migrate_scorm_packages,
            reverse_noop,
        ),
        migrations.RemoveField(
            model_name="coursepage",
            name="scorm_package",
        ),
    ]
