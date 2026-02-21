# Wagtail LMS

A Learning Management System extension for [Wagtail CMS](https://wagtail.org) with SCORM 1.2/2004 and H5P support.

[![CI](https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/ci.yml/badge.svg)](https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/wagtail-lms.svg)](https://pypi.org/project/wagtail-lms/)
[![Documentation Status](https://readthedocs.org/projects/wagtail-lms/badge/?version=latest)](https://wagtail-lms.readthedocs.io/en/latest/)

## Features

- **SCORM Support** — Full SCORM 1.2 and 2004 package compatibility
- **H5P Support** — Embed interactive H5P activities in long-scroll lesson pages
- **xAPI Tracking** — Record H5P learner interactions as xAPI statements
- **Course Management** — Integrate courses into Wagtail's page system
- **Enrollment Tracking** — Automatic student enrollment and progress monitoring
- **Secure Delivery** — Path-validated content serving with iframe support
- **Progress Persistence** — CMI data model storage with suspend/resume capability
- **Framework Agnostic** — Minimal default styling, easy to customize

## Quick Install

```bash
pip install wagtail-lms
```

Then follow the [Installation Guide](installation.md) for full setup instructions.

## Documentation

- [Installation](installation.md)
- [API Reference](api.md)
- [Template Customization](template_customization.md)
- [Testing](testing.md)
- [Contributing](contributing.md)
- [Release Process](release_process.md)
- [Changelog](changelog.md)
- [Roadmap](roadmap.md)
