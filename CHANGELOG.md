# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for 0.2.0

- CI/CD pipeline with GitHub Actions
- Multi-version testing (Python 3.11-3.13, Django 4.2+, Wagtail 6.x-7.x)
- Pure Wagtail admin interface (remove Django admin dependency)

## [0.1.0] - 2025-10-26

### Status

**Alpha Release** - Initial release with core SCORM functionality and comprehensive testing.

### Added

- **Core SCORM Features**
  - SCORM 1.2 and 2004 package support
  - Automatic ZIP extraction and manifest parsing
  - Version detection from manifest metadata
  - Launch URL extraction and validation
- **Course Management**
  - Course page model integrated with Wagtail's page system
  - Student enrollment system with progress tracking
  - SCORM attempt tracking with CMI data model
  - Support for suspend/resume functionality
- **SCORM API Implementation**
  - Complete SCORM API 2004 Runtime
  - Methods: Initialize, Terminate, GetValue, SetValue, Commit, GetLastError, GetErrorString, GetDiagnostic
  - Proper error code handling
  - CMI data model storage with key-value pairs
- **Security & Content Delivery**
  - Secure SCORM content serving with path traversal protection
  - CSRF-exempt API with login_required authentication
  - Iframe-friendly headers (X-Frame-Options: SAMEORIGIN)
  - User-isolated progress tracking
- **Database Concurrency Handling**
  - Retry decorator with exponential backoff for SQLite database locks
  - Atomic transactions for SCORM data operations
  - Configurable timeout settings (20s default for example project)
- **Testing & Quality**
  - Comprehensive test suite with **86% code coverage**
  - 65+ tests covering models, views, API, and integration workflows
  - SCORM package extraction and manifest parsing tests
  - Full SCORM API endpoint testing
  - Integration tests for complete course enrollment workflows
  - Concurrent operation and error handling tests
  - Security and authentication tests
  - Test fixtures for SCORM 1.2 and 2004 packages
- **Example Project**
  - Fully functional Wagtail project for development and testing
  - Complete setup guide in `example_project/README.md`
  - Pre-configured settings optimized for SCORM operations
  - Home page and course page templates
- **Admin Integration**
  - Wagtail admin menu item for SCORM Packages
  - Django admin interface for SCORM package management
  - Custom admin panels for course configuration
- **Documentation**
  - Comprehensive README with installation and usage instructions
  - Test running instructions with PYTHONPATH configuration
  - Database configuration recommendations

### Fixed

- Wagtail preview mode error when viewing unsaved course pages
  - Added `self.pk` check before querying enrollments
  - Graceful handling of pages without primary keys
- SQLite database lock errors during concurrent SCORM API calls
  - Implemented retry logic (up to 5 attempts with exponential backoff)
  - Transaction atomicity for data consistency

### Limitations

- **Only tested on Python 3.13.0, Django 5.2.3, Wagtail 7.0.1**
  - Other versions may work but are untested
- Django admin required for SCORM package upload (not pure Wagtail interface)
- SQLite recommended for development only (PostgreSQL for production)
- No CI/CD pipeline yet

### Known Issues & Future Plans

- xAPI/TinCan API support not yet implemented (planned for future release)
- No certificate generation (planned for future release)
- No batch enrollment features
- No course completion certificates
- Multi-version testing planned for 0.2.0
