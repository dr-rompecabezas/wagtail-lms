# Wagtail LMS

[![CI](https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/ci.yml/badge.svg)](https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/dr-rompecabezas/wagtail-lms/branch/main/graph/badge.svg)](https://codecov.io/gh/dr-rompecabezas/wagtail-lms)
[![PyPI version](https://badge.fury.io/py/wagtail-lms.svg)](https://badge.fury.io/py/wagtail-lms)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/dr-rompecabezas/wagtail-lms/main.svg)](https://results.pre-commit.ci/latest/github/dr-rompecabezas/wagtail-lms/main)

A Learning Management System extension for Wagtail CMS with SCORM 1.2/2004 support.

## ⚠️ Alpha Release

**This package is in early development.**

**Supported versions:**

- **Python:** 3.11, 3.12, 3.13
- **Django:** 4.2 (LTS), 5.0, 5.1, 5.2 (LTS)
- **Wagtail:** 6.0, 6.1, 6.2, 6.3, 7.0 (LTS), 7.1

All combinations are tested in CI. See our [compatibility matrix](https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/ci.yml) for specific version combinations.

## Features

- 📚 **Course Management** - Integrate courses into Wagtail's page system
- 📦 **SCORM Support** - Full SCORM 1.2 and 2004 package compatibility
- 👥 **Enrollment Tracking** - Automatic student enrollment and progress monitoring
- 📊 **SCORM API** - Complete runtime API implementation for content interactivity
- 🔒 **Secure Delivery** - Path-validated content serving with iframe support
- 💾 **Progress Persistence** - CMI data model storage with suspend/resume capability
- 🔄 **Concurrency Handling** - Retry logic for SQLite database lock scenarios
- 🎨 **Framework Agnostic** - Minimal default styling, easy to customize with any CSS framework

## Development Status

✅ **Core functionality tested and working**

- Comprehensive test suite with **86% code coverage**
- 65+ tests covering models, views, API, and integration workflows
- Example project fully functional for development and testing
- Database lock handling for concurrent SCORM operations
- Wagtail preview mode fully supported

See `example_project/README.md` for setup instructions.

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

### Customizing Templates

The package includes minimal, functional styling that works out of the box. To match your project's design:

- **Quick:** Override the CSS classes in your own stylesheet
- **Full control:** Override the templates in your project (standard Django approach)
- **Examples:** See [Template Customization Guide](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/docs/template_customization.md) for Bootstrap, Tailwind CSS, and Bulma examples

For API-first projects, the templates are optional and can be ignored entirely.

## Development

### Running Tests

The project includes a comprehensive test suite with 86% code coverage.

```bash
# Install testing dependencies (pytest, pytest-django, pytest-cov)
uv sync --extra testing

# Run all tests
PYTHONPATH=. uv run pytest

# Run with coverage report
PYTHONPATH=. uv run pytest --cov=src/wagtail_lms --cov-report=term-missing

# Run specific test file
PYTHONPATH=. uv run pytest tests/test_models.py -v
```

### Database Considerations

**SQLite**: The package includes retry logic with exponential backoff to handle database lock errors during concurrent SCORM API operations. For development with the example project:

```python
# example_project/settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
        "OPTIONS": {
            "timeout": 20,  # Increased timeout for SCORM operations
        },
    }
}
```

**Production**: For production deployments, PostgreSQL is recommended for better concurrency handling:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "wagtail_lms",
        # ... other PostgreSQL settings
    }
}
```

## Acknowledgments

- Built with [Django](https://djangoproject.com/) and [Wagtail CMS](https://wagtail.org/)
- SCORM implementation based on ADL specifications
- Inspired by open-source LMS solutions like [Moodle](https://moodle.org/) and [Open edX](https://openedx.org/)

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/LICENSE) file for details.
