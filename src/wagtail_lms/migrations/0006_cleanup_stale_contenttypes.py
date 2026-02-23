from django.db import migrations


def remove_stale_contenttypes(apps, schema_editor):
    """Delete ContentType rows left behind by the RenameModel operations in 0005.

    Django's RenameModel migration updates the matching ContentType row in-place
    (model='lessonpage' → 'h5plessonpage', 'lessoncompletion' →
    'h5plessoncompletion').  On some databases / ORM cache states an orphan row
    for the *old* name can survive alongside the new one.  Any such row has
    model_class() == None (the Python class no longer exists) and will cause
    'NoneType' attribute errors when Wagtail resolves page.specific for children
    of a CoursePage.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(
        app_label="wagtail_lms",
        model__in=["lessonpage", "lessoncompletion"],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("wagtail_lms", "0005_rename_lessonpage_h5plessonpage_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(
            remove_stale_contenttypes,
            migrations.RunPython.noop,
        ),
    ]
