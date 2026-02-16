# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Wagtail admin interface for SCORM packages, enrollments, and attempts** ([#52](https://github.com/dr-rompecabezas/wagtail-lms/issues/52))
  - New `ModelViewSet` classes for `SCORMPackage` (full CRUD), `CourseEnrollment` (list/edit), and `SCORMAttempt` (read-only inspect)
  - `LMSViewSetGroup` provides a top-level "LMS" menu in Wagtail admin with sub-items for each model
  - `SCORMAttempt` uses a `ReadOnlyPermissionPolicy` to disable add/edit/delete — attempts are created automatically by the SCORM player
  - Panels added to `SCORMPackage`, `CourseEnrollment`, and `SCORMAttempt` models with appropriate read-only fields
  - Django admin registrations preserved for backward compatibility
  - 11 new tests covering viewset registration, admin view access, and read-only enforcement

### Removed

- `SCORMPackageListView` and its template (`scorm_package_list.html`) — replaced by Wagtail's built-in viewset views
- `/lms/scorm-packages/` URL endpoint — SCORM packages are now managed at `/admin/scormpackage/`

## [0.7.0] - 2026-02-15

### Added

- **SCORM file cleanup on package deletion** ([#51](https://github.com/dr-rompecabezas/wagtail-lms/issues/51))
  - Uploaded ZIP and extracted content directory are now deleted from storage when a `SCORMPackage` is removed
  - Uses `post_delete` signal with `transaction.on_commit()` to avoid deleting files on rollback
  - Works with both `FileSystemStorage` and remote backends (S3, etc.)
  - Empty directories are cleaned up on filesystem-backed storage

### Fixed

- **Publish workflow: TestPyPI now runs on release events**
  - Previously `publish-to-testpypi` and `verify-testpypi` were gated to `workflow_dispatch` only
  - TestPyPI publish and verification now run before PyPI publish on every release

## [0.6.1] - 2026-02-12

### Added

- Django 6.0 and Wagtail 7.2/7.3 support with two new CI matrix entries
- Example project: add `setup_pages` management command replacing manual home page setup
- Example project: document all `WAGTAIL_LMS_*` settings, update lockfile to latest versions

### Changed

- Remove extra `default_storage.exists()` call from `ServeScormContentView` redirect path ([#44](https://github.com/dr-rompecabezas/wagtail-lms/issues/44))
  - Eliminates ~50-100ms latency per media asset request in S3-backed deployments
  - Missing files now produce a redirect to S3 (which returns 403/404) instead of a Django 404

### Fixed

- Handle exceptions in `ServeScormContentView` redirect path ([#43](https://github.com/dr-rompecabezas/wagtail-lms/issues/43))
  - `get_redirect_url()` failures (expired AWS credentials, transient S3 errors) now return 404 instead of unhandled 500
  - Intentional Django exceptions (`Http404`, `PermissionDenied`, `SuspiciousOperation`) from subclass overrides propagate correctly

## [0.6.0] - 2026-02-11

### Added

- **Extensible SCORM content serving with cache and media redirect hooks** ([#41](https://github.com/dr-rompecabezas/wagtail-lms/issues/41))
  - Replaced function-based content serving with `ServeScormContentView` (CBV), making downstream subclass overrides straightforward
  - Added `WAGTAIL_LMS_CACHE_CONTROL` setting with exact MIME, wildcard (e.g. `image/*`), and `default` matching
  - Added `WAGTAIL_LMS_REDIRECT_MEDIA` setting to redirect `audio/*` and `video/*` assets to storage-backed URLs (useful for S3)
  - Preserved upstream path traversal protection and iframe headers

### Changed

- `serve_scorm_content` now applies `Cache-Control` headers by default via `WAGTAIL_LMS_CACHE_CONTROL`
- Migration: set `WAGTAIL_LMS_CACHE_CONTROL = {}` to restore previous no-header behavior

### Fixed

- `serve_scorm_content` now returns `404` (not `500`) for directory-like and dot/empty normalized paths
- `WAGTAIL_LMS_CACHE_CONTROL` now supports explicit per-MIME `None` values to disable the header without falling back to wildcard/default
- README cache-control example now includes both `application/javascript` and `text/javascript` MIME variants

## [0.5.0] - 2026-02-10

### Added

- **Django storage backend support for SCORM content** ([#38](https://github.com/dr-rompecabezas/wagtail-lms/issues/38))
  - `extract_package()` now uses `default_storage.save()` instead of `zipfile.extractall()`, enabling S3 and other remote storage backends
  - `serve_scorm_content()` now uses `default_storage.exists()` and `default_storage.open()` instead of `os.path` operations
  - Works transparently with both `FileSystemStorage` (local) and `S3Boto3Storage` (or any Django storage backend)
  - Fixes SCORM content loss on platforms with ephemeral filesystems (Railway, Heroku, Render)
- **Path traversal security in ZIP extraction**
  - Rejects ZIP members containing `..` segments or absolute paths during extraction (logged as warnings)
  - `serve_scorm_content()` now explicitly rejects `..` segments and leading `/` in request paths
- **8 new tests** for storage backend compatibility, path traversal protection, and `parse_manifest()` flexibility

### Changed

- `parse_manifest()` parameter renamed from `manifest_path` to `manifest_source` to reflect it now accepts both file paths and file-like objects
- `extract_package()` captures manifest content in-memory during extraction to avoid an extra storage round-trip
- `extract_package()` and `serve_scorm_content()` now use `conf.WAGTAIL_LMS_CONTENT_PATH` instead of hardcoded `"scorm_content/"`
- Replaced `os` import with `posixpath` in views (forward slashes for S3 key compatibility)

## [0.4.1] - 2025-12-27

### Changed

- User foreign keys now use `settings.AUTH_USER_MODEL` instead of `auth.User` in model definitions, aligning code with existing migrations and Django best practices for reusable apps.

## [0.4.0] - 2025-12-04

### Breaking

- Static assets moved from `static/lms/*` to `static/wagtail_lms/*`; any custom templates that manually include `course.css` must update the path (`{% static 'wagtail_lms/css/course.css' %}`).

### Fixed

- Corrected admin SCORM CSS/JS namespace to match the app, resolving 404s in production.
- Admin SCORM assets now use Django's `static()` helper, so `STATIC_URL` prefixes and hashed filenames from `ManifestStaticFilesStorage` are honored.

## 0.3.1 - 2025-11-09

### Fixed

- **GitHub Actions publish workflow**
  - Fixed workflow stopping after build step when triggered via workflow_dispatch
  - Added conditional `if: github.event_name == 'release'` to publish-to-pypi job
  - Separated TestPyPI testing workflow from production PyPI release workflow
  - TestPyPI publish now only runs on manual workflow_dispatch trigger
  - PyPI publish now correctly runs on GitHub release events
  - Removed verify-testpypi dependency from publish-to-pypi job to prevent blocking

## 0.3.0 - 2025-11-09

### Added

- **Multi-version testing infrastructure**
  - Comprehensive CI testing across Python 3.11-3.13
  - Django 4.2 (LTS), 5.0, 5.1, 5.2 (LTS) support verified
  - Wagtail 6.0-7.1 compatibility confirmed
  - Strategic test matrix with 6 key version combinations
  - Enhanced GitHub Actions workflow with version-specific installations
  - Updated package classifiers and dependency specifications

### Breaking Changes

- **SCORM content serving now requires authentication**
  - The `serve_scorm_content` view now has `@login_required` decorator
  - **Migration:** SCORM content files can no longer be accessed without login
  - **Rationale:** Security fix - prevents unauthorized access to course content

- **URL name correction for SCORM content endpoint**
  - Changed URL name from `scorm_content` to `serve_scorm_content` in `wagtail_lms/urls.py`
  - **Impact:** Code using `reverse('wagtail_lms:scorm_content', ...)` will break
  - **Migration:** Update to `reverse('wagtail_lms:serve_scorm_content', ...)`
  - **Note:** This fixes a bug where the URL name didn't match the view function name

### Fixed

- **Test suite reliability**
  - Fixed 9 failing tests and 2 transaction errors
  - All 65 tests now passing consistently
  - Wrapped IntegrityError tests in atomic transactions to prevent cleanup errors

- **SCORM 2004 version detection**
  - Fixed ElementTree compatibility (removed lxml-specific `nsmap` usage)
  - Implemented explicit version string matching to prevent false positives
  - Now correctly identifies SCORM 2004 packages via schemaversion element
  - Supports: "2004 3rd Edition", "2004 4th Edition", "CAM 1.3", "2004"

- **Security improvements**
  - Fixed open redirect vulnerability in enrollment view
  - Now uses `settings.ALLOWED_HOSTS` for redirect validation
  - Added proper null checks to prevent AttributeError in manifest parsing

- **Course enrollment redirect handling**
  - Fixed crash when `course.url` is None
  - Added safe fallback to HTTP_REFERER with proper validation
  - Falls back to home page if no safe redirect available

### Changed

- **Test assertions updated for Django 5.2**
  - Fixed FileResponse test to use `streaming_content` instead of `content`
  - Updated test expectations to match actual template output

## [0.2.0] - 2025-11-05

### Status

**Breaking Changes Release** - Removes Bootstrap classes, adds framework-agnostic styling.

### Breaking Changes

**IMPORTANT:** This release changes template class names. If you installed v0.1.0, you'll need to update your templates.

- **Template class names changed from Bootstrap-style to LMS-prefixed classes**
  - Old: `.container`, `.row`, `.col-md-8`, `.btn-primary`, `.alert-info`
  - New: `.lms-course`, `.lms-course__layout`, `.lms-button--primary`, `.lms-notice--info`
  - **Migration:** Update any custom CSS targeting old classes, or override templates with your own
  - See [Template Customization Guide](docs/template_customization.md) for examples

### Added

- **Framework-Agnostic Styling**
  - New `lms/css/course.css` with minimal, functional default styles
  - BEM-style naming convention (`.lms-component__element--modifier`)
  - Works out of the box without external CSS frameworks
  - Fully responsive with mobile-first grid layout
  - Easy to override or replace with your own styles

- **Comprehensive Template Customization Documentation**
  - New `docs/template_customization.md` guide
  - Examples for Bootstrap 5, Tailwind CSS, and Bulma
  - Three customization approaches: default styles, CSS overrides, or template replacement
  - Guidance for API-first/headless projects
  - Dynamic template location finder command

- **Accessibility Improvements**
  - Added `:focus` state to SCORM player back button for keyboard navigation
  - Visible focus indicator with outline for better accessibility
  - Semantic HTML structure with proper ARIA roles

- **Developer Experience**
  - In-template comments explaining CSS requirements
  - Clear documentation on including stylesheets in base templates
  - Example project now demonstrates default LMS styling
  - Updated release process documentation to use `uv publish` instead of `twine` (closes #2)

- **Testing Infrastructure**
  - Added `tests/templates/base.html` for template rendering in tests
  - Updated test settings to include test templates directory
  - Fixed 4 previously failing tests related to missing base template

### Changed

- Templates now use semantic HTML with BEM-style CSS classes
- Example project updated to include LMS CSS in base template
- Removed unused Bootstrap-style classes from example project
- Updated README with template customization section

### Fixed

- v0.1.0 templates had Bootstrap classes but no CSS (broken out of the box)
  - Now includes working CSS by default
  - Clear documentation on how to include it
- FOUC (Flash of Unstyled Content) issue resolved
  - Documented proper CSS placement in `<head>` section
  - Removed inline CSS loading from templates

### Notes for v0.1.0 Users

If you installed v0.1.0 and customized the templates:

1. **If you added Bootstrap yourself:** Continue using it by overriding templates (see docs)
2. **If you have custom CSS:** Update selectors to target new `.lms-*` classes
3. **Fresh install recommended:** v0.1.0 templates were incomplete, v0.2.0 provides working defaults

### Planned for 0.3.0

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
