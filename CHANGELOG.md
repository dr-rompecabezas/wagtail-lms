# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for 0.2.0

- Comprehensive test suite with pytest
- CI/CD pipeline with GitHub Actions
- Multi-version testing (Python 3.11-3.13, Django 4.2+, Wagtail 6.x-7.x)
- Pure Wagtail admin interface (remove Django admin dependency)
- Enhanced example project with full setup

## [0.1.0] - 2025-10-26

### Status

**Alpha Release** - This is an early release to establish the package and gather community feedback.

### Added

- Initial release
- SCORM 1.2 and 2004 package support
  - Automatic ZIP extraction and manifest parsing
  - Support for both SCORM 1.2 and 2004 specifications
- Course page model integrated with Wagtail's page system
- Student enrollment system with progress tracking
- SCORM attempt tracking with CMI data model
- SCORM API 2004 Runtime implementation
  - Initialize, Terminate, GetValue, SetValue, Commit
  - Proper error code handling
- Secure SCORM content delivery with path traversal protection
- Wagtail admin integration with SCORM Packages menu item
- Django admin interface for SCORM package management

### Limitations

- **Only tested on Python 3.13.0, Django 5.2.3, Wagtail 7.0.1**
- Minimal test coverage (only basic stub tests)
- No CI/CD pipeline
- Django admin required for SCORM package upload (not pure Wagtail)
- No example project yet (only partial settings file)
- Limited documentation

### Known Issues

- xAPI/TinCan API support not yet implemented (planned for future release)
- No certificate generation (planned for future release)
- No batch enrollment features
- No course completion certificates
