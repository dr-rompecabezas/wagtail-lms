# CSS Framework Customization

Wagtail-LMS provides flexible CSS framework support, allowing you to use any CSS framework (Bootstrap, Tailwind CSS, Bulma, etc.) or your own custom styles without modifying templates.

## Quick Start

The package uses Bootstrap classes by default. To use a different framework, simply configure your CSS class mappings in your Django settings:

```python
# settings.py
WAGTAIL_LMS_CSS_CLASSES = {
    # Layout
    "container": "max-w-7xl mx-auto px-4",  # Tailwind example
    "row": "flex flex-wrap -mx-4",
    "col_main": "w-full md:w-2/3 px-4",
    "col_sidebar": "w-full md:w-1/3 px-4",
    # ... more mappings
}
```

That's it! Your LMS pages will now use your configured classes.

## How It Works

### The `{% css_class %}` Template Tag

Templates use the `{% css_class %}` template tag instead of hardcoded classes:

```django
{% load lms_tags %}
<div class="{% css_class 'container' %}">
    <button class="{% css_class 'btn_primary' %}">Click me</button>
</div>
```

This tag retrieves the configured CSS class from your settings, with Bootstrap as the fallback.

### Available CSS Class Keys

| Key | Purpose | Default (Bootstrap) |
|-----|---------|---------------------|
| `container` | Main container | `container` |
| `row` | Grid row | `row` |
| `col_main` | Main content column | `col-md-8` |
| `col_sidebar` | Sidebar column | `col-md-4` |
| `btn` | Base button | `btn` |
| `btn_primary` | Primary button | `btn btn-primary` |
| `btn_success` | Success button | `btn btn-success` |
| `btn_secondary` | Secondary button | `btn btn-secondary` |
| `btn_lg` | Large button | `btn-lg` |
| `alert` | Base alert | `alert` |
| `alert_info` | Info alert | `alert alert-info` |
| `alert_warning` | Warning alert | `alert alert-warning` |
| `alert_success` | Success alert | `alert alert-success` |
| `list_unstyled` | Unstyled list | `list-unstyled` |

## Framework Examples

### Bootstrap 5 (Default)

No configuration needed! The package uses Bootstrap classes by default.

```python
# settings.py
# No WAGTAIL_LMS_CSS_CLASSES needed - Bootstrap is the default
```

### Tailwind CSS

```python
# settings.py
WAGTAIL_LMS_CSS_CLASSES = {
    # Layout
    "container": "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
    "row": "flex flex-wrap -mx-4",
    "col_main": "w-full md:w-2/3 px-4",
    "col_sidebar": "w-full md:w-1/3 px-4",

    # Buttons
    "btn": "inline-flex items-center justify-center rounded-md font-medium transition-colors",
    "btn_primary": "inline-flex items-center justify-center rounded-md font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 px-4 py-2",
    "btn_success": "inline-flex items-center justify-center rounded-md font-medium transition-colors bg-green-600 text-white hover:bg-green-700 px-4 py-2",
    "btn_secondary": "inline-flex items-center justify-center rounded-md font-medium transition-colors bg-gray-600 text-white hover:bg-gray-700 px-4 py-2",
    "btn_lg": "px-6 py-3 text-lg",

    # Alerts
    "alert": "rounded-lg p-4 mb-4",
    "alert_info": "rounded-lg p-4 mb-4 bg-blue-50 text-blue-900 border border-blue-200",
    "alert_warning": "rounded-lg p-4 mb-4 bg-yellow-50 text-yellow-900 border border-yellow-200",
    "alert_success": "rounded-lg p-4 mb-4 bg-green-50 text-green-900 border border-green-200",

    # Lists
    "list_unstyled": "list-none pl-0",
}
```

### Bulma

```python
# settings.py
WAGTAIL_LMS_CSS_CLASSES = {
    # Layout
    "container": "container",
    "row": "columns",
    "col_main": "column is-two-thirds",
    "col_sidebar": "column is-one-third",

    # Buttons
    "btn": "button",
    "btn_primary": "button is-primary",
    "btn_success": "button is-success",
    "btn_secondary": "button is-light",
    "btn_lg": "button is-large",

    # Alerts (using Bulma's notification component)
    "alert": "notification",
    "alert_info": "notification is-info",
    "alert_warning": "notification is-warning",
    "alert_success": "notification is-success",

    # Lists
    "list_unstyled": "content ul",
}
```

### Custom Framework or No Framework

You can use your own custom classes or no framework at all:

```python
# settings.py
WAGTAIL_LMS_CSS_CLASSES = {
    # Custom semantic classes
    "container": "lms-container",
    "row": "lms-grid",
    "col_main": "lms-main-content",
    "col_sidebar": "lms-sidebar",

    # Custom button classes
    "btn": "lms-btn",
    "btn_primary": "lms-btn lms-btn--primary",
    "btn_success": "lms-btn lms-btn--success",
    "btn_secondary": "lms-btn lms-btn--secondary",
    "btn_lg": "lms-btn--large",

    # Custom alert classes
    "alert": "lms-alert",
    "alert_info": "lms-alert lms-alert--info",
    "alert_warning": "lms-alert lms-alert--warning",
    "alert_success": "lms-alert lms-alert--success",

    # Lists
    "list_unstyled": "lms-list-plain",
}
```

Then define your CSS:

```css
/* custom-lms.css */
.lms-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

.lms-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 2rem;
}

.lms-btn {
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    text-decoration: none;
    display: inline-block;
}

.lms-btn--primary {
    background: #007bff;
    color: white;
}

/* ... more custom styles */
```

## Advanced Customization with Template Blocks

For even more control, templates include strategic blocks that allow you to override entire sections:

### Available Template Blocks

**course_page.html:**
- `course_header` - Course title and description
- `course_content` - Main course content area
- `enrollment_section` - Enrollment status and actions
- `course_action_button` - Start/Continue/Review button
- `enrollment_button` - Enroll button
- `course_sidebar` - Sidebar with course info

**scorm_player.html:**
- `scorm_header` - Player header with title and controls
- `scorm_back_button` - Back to course button
- `scorm_content` - SCORM iframe container

### Example: Custom Course Page

Create a custom template that extends the base course page:

```django
{# templates/custom_course_page.html #}
{% extends "wagtail_lms/course_page.html" %}
{% load static %}

{% block course_header %}
<div class="custom-header">
    <div class="custom-banner" style="background-image: url('{{ page.banner_image.url }}')">
        <h1 class="custom-title">{{ page.title }}</h1>
    </div>
    {% if page.description %}
        <div class="custom-description">
            {{ page.description|richtext }}
        </div>
    {% endif %}
</div>
{% endblock course_header %}

{% block course_sidebar %}
<div class="custom-sidebar">
    <div class="sidebar-card">
        <h4>Course Details</h4>
        <ul>
            <li><strong>Duration:</strong> {{ page.duration }}</li>
            <li><strong>Level:</strong> {{ page.level }}</li>
            <li><strong>Language:</strong> {{ page.language }}</li>
        </ul>
    </div>
    {{ block.super }}  {# Include original sidebar content #}
</div>
{% endblock course_sidebar %}
```

Then use this template in your model:

```python
from wagtail_lms.models import CoursePage

class CustomCoursePage(CoursePage):
    template = "custom_course_page.html"

    # Add custom fields
    banner_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    duration = models.CharField(max_length=100, blank=True)
    level = models.CharField(max_length=50, blank=True)
```

## Partial Overrides

You don't need to specify all CSS classes - only override what you need:

```python
# settings.py
from wagtail_lms.conf import DEFAULT_CSS_CLASSES

WAGTAIL_LMS_CSS_CLASSES = {
    **DEFAULT_CSS_CLASSES,  # Start with defaults
    # Only override buttons to use Tailwind
    "btn_primary": "bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded",
    "btn_success": "bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded",
}
```

## Migration Guide

If you're upgrading from a version that had hardcoded Bootstrap classes, your existing setup will continue to work with no changes required. The default configuration uses Bootstrap classes.

### Migrating to a New Framework

1. Choose your CSS framework and add it to your project
2. Configure `WAGTAIL_LMS_CSS_CLASSES` in settings.py
3. Test your course pages to ensure styling looks correct
4. Fine-tune class mappings as needed

### Testing Your Configuration

1. Create a test course page
2. Check the enrollment flow (unauthenticated → login prompt)
3. Test enrolled state (progress display, action buttons)
4. Verify the SCORM player interface
5. Check responsive behavior on mobile devices

## Best Practices

1. **Use framework documentation**: Reference your CSS framework's official docs for class names
2. **Test responsive layouts**: Ensure your class mappings work on all screen sizes
3. **Maintain semantic meaning**: Map classes that serve similar purposes (e.g., primary actions → primary buttons)
4. **Document your configuration**: Add comments in settings.py explaining your choices
5. **Version control**: Keep your CSS class configuration in version control
6. **Test before deploying**: Always test your styling changes in a staging environment

## Troubleshooting

### Classes not applying

**Problem**: Your configured classes don't seem to apply.

**Solution**:
- Ensure your CSS framework is properly loaded in your base template
- Check that `WAGTAIL_LMS_CSS_CLASSES` is spelled correctly in settings
- Clear your browser cache
- Check Django's settings are being loaded: `python manage.py shell` → `from django.conf import settings` → `settings.WAGTAIL_LMS_CSS_CLASSES`

### Layout looks broken

**Problem**: Layout doesn't work as expected with your framework.

**Solution**:
- Review your framework's grid system documentation
- Ensure container/row/column classes match your framework's structure
- Some frameworks need specific HTML structure - consider using template blocks for major overhauls

### Mixing frameworks

**Problem**: You want to use different frameworks for different parts.

**Solution**:
- Use template blocks to override specific sections
- Create custom templates for special cases
- Consider using CSS custom properties (variables) for easier styling

## Support

For issues, questions, or contributions related to CSS customization:
- GitHub Issues: https://github.com/dr-rompecabezas/wagtail-lms/issues
- Discussions: Check existing issues for CSS and styling topics

## Examples Repository

See the `example_project` directory for working examples using different CSS frameworks.
