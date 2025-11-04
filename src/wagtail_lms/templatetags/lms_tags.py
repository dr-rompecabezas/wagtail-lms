"""Custom template tags for wagtail-lms CSS framework flexibility"""

from django import template

from wagtail_lms import conf

register = template.Library()


@register.simple_tag
def css_class(class_name):
    """
    Retrieve a CSS class from the configured CSS class mappings.

    Usage in templates:
        {% load lms_tags %}
        <div class="{% css_class 'container' %}">

    Args:
        class_name: The key name for the CSS class (e.g., 'container', 'btn_primary')

    Returns:
        The configured CSS class string, or the class_name itself if not found
    """
    css_classes = conf.WAGTAIL_LMS_CSS_CLASSES
    return css_classes.get(class_name, class_name)
