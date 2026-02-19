from django.apps import AppConfig


class WagtailLmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wagtail_lms"
    verbose_name = "Wagtail LMS"

    def ready(self):
        from .signal_handlers import register_signal_handlers

        register_signal_handlers()

        from . import checks  # noqa: F401
