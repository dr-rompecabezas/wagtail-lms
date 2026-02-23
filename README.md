# Wagtail LMS

[![CI](https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/ci.yml/badge.svg)](https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/dr-rompecabezas/wagtail-lms/branch/main/graph/badge.svg)](https://codecov.io/gh/dr-rompecabezas/wagtail-lms)
[![PyPI version](https://img.shields.io/pypi/v/wagtail-lms.svg)](https://pypi.org/project/wagtail-lms/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/dr-rompecabezas/wagtail-lms/main.svg)](https://results.pre-commit.ci/latest/github/dr-rompecabezas/wagtail-lms/main)
[![Documentation Status](https://readthedocs.org/projects/wagtail-lms/badge/?version=latest)](https://wagtail-lms.readthedocs.io/en/latest/)

A Learning Management System extension for Wagtail CMS with SCORM 1.2/2004 and H5P support.

## ⚠️ Alpha Release

**This package is in early development.** That said, it is actively used in production at [thinkelearn.com](https://thinkelearn.com).

**Supported versions:**

- **Python:** 3.11, 3.12, 3.13, 3.14
- **Django:** 4.2 (LTS), 5.0, 5.1, 5.2 (LTS), 6.0
- **Wagtail:** 6.0, 6.2, 6.3, 7.1, 7.2, 7.3

Selected combinations are tested in CI. See our [compatibility matrix](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/.github/workflows/ci.yml) for specific version combinations.

## Features

- 📚 **Course Management** - Integrate courses into Wagtail's page system
- 📦 **SCORM Support** - Full SCORM 1.2 and 2004 package compatibility
- 🎯 **H5P Support** - Embed interactive H5P activities in long-scroll lesson pages
- 👥 **Enrollment Tracking** - Automatic student enrollment and progress monitoring
- 📊 **SCORM API** - Complete runtime API implementation for content interactivity
- 📡 **xAPI Tracking** - Record H5P learner interactions as xAPI statements
- 🔒 **Secure Delivery** - Path-validated content serving with iframe support
- 💾 **Progress Persistence** - CMI data model storage with suspend/resume capability
- 🔄 **Concurrency Handling** - Retry logic for SQLite database lock scenarios
- 🎨 **Framework Agnostic** - Minimal default styling, easy to customize with any CSS framework

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
WAGTAIL_LMS_AUTO_ENROLL = False                    # Auto-enroll on course visit

# SCORM
WAGTAIL_LMS_SCORM_UPLOAD_PATH = 'scorm_packages/'  # Upload directory
WAGTAIL_LMS_SCORM_CONTENT_PATH = 'scorm_content/'  # Extracted content

# H5P
WAGTAIL_LMS_H5P_UPLOAD_PATH = 'h5p_packages/'      # Upload directory
WAGTAIL_LMS_H5P_CONTENT_PATH = 'h5p_content/'      # Extracted content

# Cache-Control rules for served assets (exact MIME, wildcard, and default)
WAGTAIL_LMS_CACHE_CONTROL = {
    "text/html": "no-cache",
    "text/css": "max-age=86400",
    "application/javascript": "max-age=86400",
    "text/javascript": "max-age=86400",
    "image/*": "max-age=604800",
    "font/*": "max-age=604800",
    "default": "max-age=86400",
}

# Redirect audio/video assets to storage URLs (useful for S3 backends)
WAGTAIL_LMS_REDIRECT_MEDIA = False

# Use custom Wagtail admin viewsets for upload flows
WAGTAIL_LMS_SCORM_PACKAGE_VIEWSET_CLASS = "wagtail_lms.viewsets.SCORMPackageViewSet"
WAGTAIL_LMS_H5P_ACTIVITY_VIEWSET_CLASS = "wagtail_lms.viewsets.H5PActivityViewSet"
WAGTAIL_LMS_H5P_SNIPPET_VIEWSET_CLASS = "wagtail_lms.viewsets.H5PActivitySnippetViewSet"

# Lesson access hook (dotted-path callable)
WAGTAIL_LMS_CHECK_LESSON_ACCESS = "wagtail_lms.access.default_lesson_access_check"

# Django admin registration controls
WAGTAIL_LMS_REGISTER_DJANGO_ADMIN = True
WAGTAIL_LMS_SCORM_ADMIN_CLASS = "wagtail_lms.admin.SCORMPackageAdmin"
WAGTAIL_LMS_H5P_ADMIN_CLASS = "wagtail_lms.admin.H5PActivityAdmin"
```

## Usage

### SCORM Courses

1. Log into Wagtail admin
2. Create a new **Course Page** under Pages
3. Upload a SCORM package via **LMS → SCORM Packages** in the Wagtail admin
4. Add a **SCORM Lesson Page** as a child of the Course Page and assign the SCORM package to it
5. Publish — enrolled learners can access the lesson from the course page

**SCORM package requirements:**

- Valid SCORM 1.2 or 2004 ZIP file
- Must contain `imsmanifest.xml` at the root
- Launch file must be specified in the manifest

### H5P Lessons

H5P activities are composed into long-scroll **H5P Lesson Pages** alongside rich text. A lesson is always a child of a Course Page; enrollment in the course is required to access its lessons.

1. Upload an **H5P Activity** snippet via **LMS → H5P Activities** in the Wagtail admin
2. Create a **Course Page** (no SCORM package required for H5P-only courses)
3. Add an **H5P Lesson Page** as a child of the Course Page
4. In the lesson body, add **H5P Activity** blocks (and/or rich text blocks) to compose the lesson
5. Publish — enrolled learners can access the lesson; xAPI statements are recorded automatically

**H5P package requirements:**

- Valid `.h5p` file (ZIP with an `.h5p` extension) containing `h5p.json` at the root
- **Must include library JavaScript files** — h5p-standalone renders content using
  library JS bundled inside the package (e.g. `H5P.InteractiveVideo-1.27/`).
  A warning is logged and "Could not load activity." is shown if files are missing.

  - ✅ [Lumi desktop editor](https://lumi.education) (free, open-source) — recommended
  - ✅ Moodle / WordPress / Drupal H5P plugin export
  - ✅ Lumi Cloud (free tier available at lumi.education)
  - ❌ H5P.org "Reuse" download — content-only, no library files included
  - ❌ H5P.org does not offer a download-with-libraries option for any content

### Customizing Templates

The package includes minimal, functional styling that works out of the box. To match your project's design:

- **Quick:** Override the CSS classes in your own stylesheet
- **Full control:** Override the templates in your project (standard Django approach)
- **Examples:** See [Template Customization](https://wagtail-lms.readthedocs.io/en/latest/template_customization/) for Bootstrap, Tailwind CSS, and Bulma examples

For API-first projects, the templates are optional and can be ignored entirely.

## Development

An example project is available in `example_project/` for local development and testing. See its [README](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/example_project/README.md) for setup instructions.

### Running Tests

```bash
uv sync --extra testing
PYTHONPATH=. uv run pytest
PYTHONPATH=. uv run pytest --cov=src/wagtail_lms --cov-report=term-missing
```

See the [Testing Guide](https://wagtail-lms.readthedocs.io/en/latest/testing/) for full details, including writing new tests and CI configuration.

### Database

SQLite works for development (the package includes retry logic for concurrent SCORM operations). PostgreSQL is recommended for production. See the [example project README](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/example_project/README.md) for configuration examples.

## Acknowledgments

- Built with [Django](https://djangoproject.com/) and [Wagtail CMS](https://wagtail.org/)
- SCORM implementation based on ADL specifications
- H5P support powered by [H5P](https://h5p.org/) and [h5p-standalone](https://github.com/tunapanda/h5p-standalone)
- [Lumi](https://lumi.education/) — recommended free, open-source H5P editor for creating self-contained packages
- Inspired by open-source LMS solutions like [Moodle](https://moodle.org/) and [Open edX](https://openedx.org/)

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/LICENSE) file for details.
