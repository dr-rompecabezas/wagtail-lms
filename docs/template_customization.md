# Template Customization

Wagtail-LMS provides minimal, framework-agnostic templates that you can easily customize to match your project's design.

## Default Styling

The package includes basic CSS with minimal, functional styling:

- **course.css** - Simple grid layout and basic button/notice styles
- **Inline styles in scorm_player.html** - Self-contained player interface

These styles ensure the LMS works out of the box without looking broken, but they're designed to be overridden.

## Customization Approaches

You have three options, depending on your needs:

### Option 1: Use the Default Styles (Quickest)

Include the LMS CSS in your base template's `<head>` section:

```django
{# templates/base.html #}
{% load static wagtailcore_tags %}
<!DOCTYPE html>
<html>
<head>
    <!-- Your site CSS -->
    <link rel="stylesheet" href="{% static 'css/your-site.css' %}">

    <!-- LMS default styles -->
    <link rel="stylesheet" href="{% static 'lms/css/course.css' %}">
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

That's it! The default styles provide a clean, functional interface.

### Option 2: Override with Your Own CSS (Recommended)

Keep the HTML structure but apply your own styles. Create a custom stylesheet that targets the LMS classes:

```css
/* your-project/static/css/custom-lms.css */

/* Override LMS button styles with your design */
.lms-button--primary {
    background-color: #your-brand-color;
    border-radius: 8px;
    /* ...your custom styles */
}

/* Customize the layout */
.lms-course__layout {
    grid-template-columns: 3fr 1fr; /* Different proportions */
    gap: 3rem;
}

/* Match your site's notice/alert styling */
.lms-notice--info {
    background-color: var(--your-info-color);
    /* ...your custom styles */
}
```

Include the LMS CSS and your custom overrides in your base template's `<head>`:

```django
{# templates/base.html #}
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <!-- LMS default styles (optional) -->
    <link rel="stylesheet" href="{% static 'lms/css/course.css' %}">

    <!-- Your custom overrides -->
    <link rel="stylesheet" href="{% static 'css/custom-lms.css' %}">
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

### Option 3: Override Templates Entirely (Maximum Control)

Replace the LMS templates with your own. This is the standard Django approach for reusable apps (see: django-allauth, django-tables2).

**Step 1:** Create template overrides in your project:

```text
your-project/
├── templates/
│   └── wagtail_lms/
│       ├── course_page.html      # Your Bootstrap/Tailwind/Bulma version
│       └── scorm_player.html     # Your custom player
```

**Step 2:** Ensure your `TEMPLATES` setting has your templates directory first:

```python
# settings.py
TEMPLATES = [{
    'DIRS': [BASE_DIR / 'templates'],  # Your templates override package templates
    # ...
}]
```

**Step 3:** Copy and modify the default templates (see examples below).

## Template Reference

### Available Templates

| Template | Page model | Notes |
|----------|------------|-------|
| `course_page.html` | `CoursePage` | Lists H5P lessons, SCORM lessons, enrollment CTA |
| `h5p_lesson_page.html` | `H5PLessonPage` | Long-scroll H5P activity page |
| `scorm_lesson_page.html` | `SCORMLessonPage` | Launch button + SCORM player link |
| `scorm_player.html` | — | Full-page iframe SCORM player |

### H5P Lesson Integration Notes

If you customize `h5p_lesson_page.html`, keep the H5P scripts in this order:

1. `main.bundle.js` (with `id="h5p-standalone-script"` and its data attributes)
2. `h5p-lesson.js`

Do not include `frame.bundle.js` as a standalone `<script>` tag. It is loaded by `main.bundle.js` at runtime. Loaded directly, it can overwrite `window.H5PStandalone`, which breaks initialization of later H5P activities on the same page.

### Available LMS CSS Classes

**Layout:**

- `.lms-course` - Main course container
- `.lms-course__layout` - Grid layout wrapper
- `.lms-course__main` - Main content area
- `.lms-course__sidebar` - Sidebar area

**Components:**

- `.lms-button` - Base button
- `.lms-button--primary` - Primary action button (blue)
- `.lms-button--success` - Success button (green)
- `.lms-notice` - Base notice/alert
- `.lms-notice--info` - Info notice (blue)
- `.lms-notice--warning` - Warning notice (yellow)
- `.lms-notice--success` - Success notice (green)

**Course elements:**

- `.lms-course__description` - Course description
- `.lms-course__info` - Course package info
- `.lms-enrollment` - Enrollment section
- `.lms-sidebar-section` - Sidebar section wrapper
- `.lms-info-list` - List of course metadata

**SCORM Player:**

- `.lms-player` - Player container
- `.lms-player__header` - Player header
- `.lms-player__controls` - Control buttons area
- `.lms-player__back-button` - Back to course button
- `.lms-player__status` - Status indicator
- `.lms-player__content` - Iframe container

## Framework Examples

### Bootstrap 5

```django
{# templates/wagtail_lms/course_page.html #}
{% extends "base.html" %}
{% load wagtailcore_tags %}

{% block content %}
<div class="container my-5">
    <div class="row">
        <div class="col-lg-8">
            <h1>{{ page.title }}</h1>

            {% if page.description %}
                <div class="mb-4">
                    {{ page.description|richtext }}
                </div>
            {% endif %}

            {% if lesson_pages %}
                <div class="mb-4">
                    <h3>Lessons</h3>
                    <ol class="list-group list-group-numbered">
                        {% for lesson in lesson_pages %}
                            <li class="list-group-item{% if lesson.pk in completed_lesson_ids %} list-group-item-success{% endif %}">
                                <a href="{% pageurl lesson %}">{{ lesson.title }}</a>
                                {% if lesson.pk in completed_lesson_ids %}<span class="badge bg-success ms-2">&#10003;</span>{% endif %}
                            </li>
                        {% endfor %}
                    </ol>
                </div>
            {% endif %}

            {% if scorm_lesson_pages %}
                <div class="mb-4">
                    <h3>SCORM Lessons</h3>
                    <ol class="list-group list-group-numbered">
                        {% for lesson in scorm_lesson_pages %}
                            <li class="list-group-item">
                                <a href="{% pageurl lesson %}">{{ lesson.title }}</a>
                            </li>
                        {% endfor %}
                    </ol>
                </div>
            {% endif %}

            {% if lesson_pages or scorm_lesson_pages %}
                {% if user.is_authenticated %}
                    {% if enrollment %}
                        <div class="alert alert-info">
                            <strong>Enrolled:</strong> {{ enrollment.enrolled_at|date:"M d, Y" }}
                            {% if enrollment.completed_at %}
                                <br><strong>Completed:</strong> {{ enrollment.completed_at|date:"M d, Y" }}
                            {% endif %}
                        </div>
                    {% else %}
                        <a href="{% url 'wagtail_lms:enroll_course' page.id %}"
                           class="btn btn-success btn-lg">
                            Enroll in Course
                        </a>
                    {% endif %}
                {% else %}
                    <div class="alert alert-warning">
                        Please login to enroll in this course.
                    </div>
                {% endif %}
            {% else %}
                <div class="alert alert-warning">
                    This course doesn't have any content assigned yet.
                </div>
            {% endif %}
        </div>

        <div class="col-lg-4">
            <div class="card">
                <div class="card-body">
                    <h4>Course Information</h4>
                    <ul class="list-unstyled">
                        {% if lesson_pages %}
                            <li><strong>Lessons:</strong> {{ lesson_pages|length }}</li>
                        {% endif %}
                        {% if scorm_lesson_pages %}
                            <li><strong>SCORM Lessons:</strong> {{ scorm_lesson_pages|length }}</li>
                        {% endif %}
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Tailwind CSS

```django
{# templates/wagtail_lms/course_page.html #}
{% extends "base.html" %}
{% load wagtailcore_tags %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <main class="lg:col-span-2">
            <h1 class="text-3xl font-bold mb-4">{{ page.title }}</h1>

            {% if page.description %}
                <div class="prose mb-6">
                    {{ page.description|richtext }}
                </div>
            {% endif %}

            {% if lesson_pages %}
                <div class="mb-6">
                    <h3 class="text-xl font-semibold mb-2">Lessons</h3>
                    <ol class="space-y-2">
                        {% for lesson in lesson_pages %}
                            <li class="{% if lesson.pk in completed_lesson_ids %}text-green-700{% endif %}">
                                <a href="{% pageurl lesson %}" class="hover:underline">{{ lesson.title }}</a>
                                {% if lesson.pk in completed_lesson_ids %}<span class="ml-2">&#10003;</span>{% endif %}
                            </li>
                        {% endfor %}
                    </ol>
                </div>
            {% endif %}

            {% if scorm_lesson_pages %}
                <div class="mb-6">
                    <h3 class="text-xl font-semibold mb-2">SCORM Lessons</h3>
                    <ol class="space-y-2">
                        {% for lesson in scorm_lesson_pages %}
                            <li>
                                <a href="{% pageurl lesson %}" class="hover:underline">{{ lesson.title }}</a>
                            </li>
                        {% endfor %}
                    </ol>
                </div>
            {% endif %}

            {% if lesson_pages or scorm_lesson_pages %}
                {% if user.is_authenticated %}
                    {% if enrollment %}
                        <div class="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4">
                            <strong>Enrolled:</strong> {{ enrollment.enrolled_at|date:"M d, Y" }}
                            {% if enrollment.completed_at %}
                                <br><strong>Completed:</strong> {{ enrollment.completed_at|date:"M d, Y" }}
                            {% endif %}
                        </div>
                    {% else %}
                        <a href="{% url 'wagtail_lms:enroll_course' page.id %}"
                           class="inline-block bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg">
                            Enroll in Course
                        </a>
                    {% endif %}
                {% else %}
                    <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                        Please login to enroll in this course.
                    </div>
                {% endif %}
            {% else %}
                <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    This course doesn't have any content assigned yet.
                </div>
            {% endif %}
        </main>

        <aside>
            <div class="bg-gray-50 p-6 rounded-lg">
                <h4 class="text-lg font-semibold mb-4">Course Information</h4>
                <ul class="space-y-2">
                    {% if lesson_pages %}
                        <li><strong>Lessons:</strong> {{ lesson_pages|length }}</li>
                    {% endif %}
                    {% if scorm_lesson_pages %}
                        <li><strong>SCORM Lessons:</strong> {{ scorm_lesson_pages|length }}</li>
                    {% endif %}
                </ul>
            </div>
        </aside>
    </div>
</div>
{% endblock %}
```

### Bulma

```django
{# templates/wagtail_lms/course_page.html #}
{% extends "base.html" %}
{% load wagtailcore_tags %}

{% block content %}
<section class="section">
    <div class="container">
        <div class="columns">
            <div class="column is-two-thirds">
                <h1 class="title is-2">{{ page.title }}</h1>

                {% if page.description %}
                    <div class="content mb-5">
                        {{ page.description|richtext }}
                    </div>
                {% endif %}

                {% if lesson_pages %}
                    <div class="box mb-5">
                        <h3 class="title is-4">Lessons</h3>
                        <ol>
                            {% for lesson in lesson_pages %}
                                <li class="{% if lesson.pk in completed_lesson_ids %}has-text-success{% endif %}">
                                    <a href="{% pageurl lesson %}">{{ lesson.title }}</a>
                                    {% if lesson.pk in completed_lesson_ids %}<span class="ml-2">&#10003;</span>{% endif %}
                                </li>
                            {% endfor %}
                        </ol>
                    </div>
                {% endif %}

                {% if scorm_lesson_pages %}
                    <div class="box mb-5">
                        <h3 class="title is-4">SCORM Lessons</h3>
                        <ol>
                            {% for lesson in scorm_lesson_pages %}
                                <li><a href="{% pageurl lesson %}">{{ lesson.title }}</a></li>
                            {% endfor %}
                        </ol>
                    </div>
                {% endif %}

                {% if lesson_pages or scorm_lesson_pages %}
                    {% if user.is_authenticated %}
                        {% if enrollment %}
                            <div class="notification is-info">
                                <strong>Enrolled:</strong> {{ enrollment.enrolled_at|date:"M d, Y" }}
                                {% if enrollment.completed_at %}
                                    <br><strong>Completed:</strong> {{ enrollment.completed_at|date:"M d, Y" }}
                                {% endif %}
                            </div>
                        {% else %}
                            <a href="{% url 'wagtail_lms:enroll_course' page.id %}"
                               class="button is-success is-large">
                                Enroll in Course
                            </a>
                        {% endif %}
                    {% else %}
                        <div class="notification is-warning">
                            Please login to enroll in this course.
                        </div>
                    {% endif %}
                {% else %}
                    <div class="notification is-warning">
                        This course doesn't have any content assigned yet.
                    </div>
                {% endif %}
            </div>

            <div class="column">
                <div class="box">
                    <h4 class="title is-5">Course Information</h4>
                    <div class="content">
                        <ul>
                            {% if lesson_pages %}
                                <li><strong>Lessons:</strong> {{ lesson_pages|length }}</li>
                            {% endif %}
                            {% if scorm_lesson_pages %}
                                <li><strong>SCORM Lessons:</strong> {{ scorm_lesson_pages|length }}</li>
                            {% endif %}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}
```

## API-First Projects

If you're building an API-first or headless application, you can ignore the templates entirely. They're completely optional and have no impact on the LMS functionality:

- Models work independently of templates
- API endpoints (SCORM API, enrollment) work without templates
- Admin interface uses Wagtail's admin templates

Simply don't visit the course page URLs in your application, or override them to return JSON responses.

## Best Practices

1. **Start with the defaults** - See if they work for your use case before customizing
2. **Override CSS first** - Easier to maintain than template overrides
3. **Use semantic HTML** - The default templates use semantic elements and ARIA attributes
4. **Test responsively** - Ensure your customizations work on mobile devices
5. **Version control** - Keep template overrides in version control to track changes across package updates

## Need Help?

**Finding the default templates:**

To locate the installed templates directory (useful for reference when creating overrides):

```bash
python -c "import wagtail_lms; from pathlib import Path; print(Path(wagtail_lms.__file__).parent / 'templates')"
```

This will output the path where the default templates are installed, regardless of your environment setup.

**Additional resources:**

- Check Django's template override docs: <https://docs.djangoproject.com/en/stable/howto/overriding-templates/>
- Open an issue: <https://github.com/dr-rompecabezas/wagtail-lms/issues>
