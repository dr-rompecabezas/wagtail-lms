# Wagtail LMS

A Learning Management System extension for Wagtail CMS with SCORM 1.2/2004 support.

## ⚠️ Alpha Release

**This package is in early development (v0.1.0-alpha).**

**Currently tested on:**

- Python 3.13.0
- Django 5.2.3
- Wagtail 7.0.1

Other versions may work but are untested. See the [Roadmap](https://github.com/dr-rompecabezas/wagtail-lms/docs/roadmap.md) for planned improvements including broader version support, comprehensive testing, and enhanced features.

## Features

- 📚 Course management using Wagtail's page system
- 📦 SCORM 1.2 and 2004 package support
- 👥 Student enrollment and progress tracking
- 📊 SCORM API implementation
- 🔒 Secure content delivery

## Development Status

An example project is included in `example_project/` for testing and development purposes. **Note:** The example project is currently work-in-progress and requires debugging before it's fully functional. See `example_project/README.md` for setup instructions.

## Installation

```bash
pip install wagtail-lms
```

## Quick Start

1. Add to `INSTALLED_APPS` in your Django settings:

    ```python
    INSTALLED_APPS = [
        # ...
        'wagtail_lms',
        # ...
    ]
    ```

2. Add wagtail-lms URLs to your `urls.py`:

    ```python
    from django.urls import path, include

    urlpatterns = [
        # ...
        path('lms/', include('wagtail_lms.urls')),
        # ...
    ]
    ```

3. Run migrations:

    ```bash
    python manage.py migrate wagtail_lms
    ```

4. Collect static files:

    ```bash
    python manage.py collectstatic
    ```

## Configuration

Optional settings in your Django settings:

```python
# SCORM package upload directory
WAGTAIL_LMS_SCORM_UPLOAD_PATH = 'scorm_packages/'

# Extracted SCORM content directory
WAGTAIL_LMS_CONTENT_PATH = 'scorm_content/'

# Auto-enroll users when they visit a course
WAGTAIL_LMS_AUTO_ENROLL = False
```

## Usage

### Creating a Course

1. Log into Wagtail admin
2. Create a new "Course Page" under Pages
3. Upload a SCORM package via Django Admin → SCORM Packages
4. Assign the SCORM package to your course page

### SCORM Package Requirements

- Must be a valid SCORM 1.2 or 2004 ZIP file
- Must contain `imsmanifest.xml` at the root
- Launch file must be specified in the manifest

## Acknowledgments

- Built with [Django](https://djangoproject.com/) and [Wagtail CMS](https://wagtail.org/)
- SCORM implementation based on ADL specifications
- Inspired by open-source LMS solutions like [Moodle](https://moodle.org/) and [Open edX](https://openedx.org/)

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/dr-rompecabezas/LICENSE) file for details.
