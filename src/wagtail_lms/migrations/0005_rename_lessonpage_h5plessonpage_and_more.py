from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "wagtail_lms",
            "0004_scormlessonpage_remove_coursepage_scorm_package",
        ),
        ("wagtailcore", "0091_remove_revision_submitted_for_moderation"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="LessonPage",
            new_name="H5PLessonPage",
        ),
        migrations.RenameModel(
            old_name="LessonCompletion",
            new_name="H5PLessonCompletion",
        ),
        migrations.AlterModelOptions(
            name="h5plessoncompletion",
            options={
                "verbose_name": "H5P Lesson Completion",
                "verbose_name_plural": "H5P Lesson Completions",
            },
        ),
        migrations.AlterModelOptions(
            name="h5plessonpage",
            options={"verbose_name": "H5P lesson page"},
        ),
    ]
