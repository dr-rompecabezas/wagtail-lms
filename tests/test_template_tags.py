"""Tests for CSS customization template tags"""

from django.template import Context, Template
from django.test import override_settings

from wagtail_lms.templatetags.lms_tags import css_class


class TestCssClassTag:
    """Test the css_class template tag"""

    def test_css_class_returns_default_bootstrap_classes(self):
        """Test that default Bootstrap classes are returned"""
        assert css_class("container") == "container"
        assert css_class("btn_primary") == "btn btn-primary"
        assert css_class("alert_info") == "alert alert-info"

    def test_css_class_returns_key_if_not_found(self):
        """Test that the key itself is returned if not found in mappings"""
        assert css_class("nonexistent_key") == "nonexistent_key"

    @override_settings(
        WAGTAIL_LMS_CSS_CLASSES={
            "container": "max-w-7xl mx-auto px-4",
            "btn_primary": "bg-blue-600 text-white hover:bg-blue-700 px-4 py-2",
        }
    )
    def test_css_class_with_custom_settings(self):
        """Test that custom settings override defaults"""
        # Need to reload the conf module to pick up the override
        from importlib import reload

        from wagtail_lms import conf

        reload(conf)

        # Now test with the reloaded configuration
        from wagtail_lms.templatetags.lms_tags import css_class

        assert css_class("container") == "max-w-7xl mx-auto px-4"
        assert (
            css_class("btn_primary")
            == "bg-blue-600 text-white hover:bg-blue-700 px-4 py-2"
        )

    def test_css_class_in_template(self):
        """Test the template tag works in actual template rendering"""
        # Reload conf to ensure we have defaults (in case previous tests modified it)
        from importlib import reload

        from wagtail_lms import conf

        reload(conf)

        template_string = """
        {% load lms_tags %}
        <div class="{% css_class 'container' %}">
            <button class="{% css_class 'btn_primary' %}">Click</button>
        </div>
        """
        template = Template(template_string)
        rendered = template.render(Context({}))

        # Check that Bootstrap classes appear in rendered output
        assert "container" in rendered
        assert "btn btn-primary" in rendered

    @override_settings(
        WAGTAIL_LMS_CSS_CLASSES={
            "container": "custom-container",
            "btn_primary": "custom-btn custom-btn-primary",
        }
    )
    def test_css_class_in_template_with_custom_settings(self):
        """Test template rendering with custom CSS settings"""
        # Reload conf to pick up settings
        from importlib import reload

        from wagtail_lms import conf

        reload(conf)

        template_string = """
        {% load lms_tags %}
        <div class="{% css_class 'container' %}">
            <button class="{% css_class 'btn_primary' %}">Click</button>
        </div>
        """
        template = Template(template_string)
        rendered = template.render(Context({}))

        # Check that custom classes appear in rendered output
        assert "custom-container" in rendered
        assert "custom-btn custom-btn-primary" in rendered

    def test_all_default_keys_exist(self):
        """Test that all documented CSS class keys have defaults"""
        from wagtail_lms.conf import DEFAULT_CSS_CLASSES

        expected_keys = [
            "container",
            "row",
            "col_main",
            "col_sidebar",
            "btn",
            "btn_primary",
            "btn_success",
            "btn_secondary",
            "btn_lg",
            "alert",
            "alert_info",
            "alert_warning",
            "alert_success",
            "list_unstyled",
        ]

        for key in expected_keys:
            assert key in DEFAULT_CSS_CLASSES, f"Key '{key}' missing from defaults"
            assert (
                DEFAULT_CSS_CLASSES[key]
            ), f"Key '{key}' has empty value in defaults"

    def test_partial_override_with_defaults(self):
        """Test that partial overrides work correctly"""
        from wagtail_lms.conf import DEFAULT_CSS_CLASSES

        # Simulate a partial override (common use case)
        custom_classes = {
            **DEFAULT_CSS_CLASSES,
            "btn_primary": "custom-primary-btn",
        }

        # Check that override works
        assert custom_classes["btn_primary"] == "custom-primary-btn"

        # Check that other defaults remain
        assert custom_classes["container"] == "container"
        assert custom_classes["alert_info"] == "alert alert-info"
