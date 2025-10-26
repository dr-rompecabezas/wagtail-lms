from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """
    Home page model for the example project.
    """

    body = RichTextField(blank=True)

    content_panels = [
        *Page.content_panels,
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = "Home Page"
