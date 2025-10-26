# Release Checklist for v0.1.0

## ✅ Completed

### Package Structure

- [x] Created src/ layout with wagtail_lms package
- [x] Created pyproject.toml with correct dependencies
- [x] Set up ruff for code quality
- [x] Added pre-commit hooks
- [x] Removed MANIFEST.in (not needed with uv)

### Core Package Fixes

- [x] **CRITICAL**: Fixed migration bug (`lms.` → `wagtail_lms.`)
  - File: `src/wagtail_lms/migrations/0001_initial.py`
  - Lines: 100, 131, 164, 194
- [x] Fixed URL namespace issues (`lms:` → `wagtail_lms:`)
  - Templates: course_page.html, scorm_player.html
- [x] Fixed Django admin URLs (`/django-admin/lms/` → `/django-admin/wagtail_lms/`)
  - Template: scorm_package_list.html
- [x] Removed external dependency (django-allauth)
  - Template: course_page.html
- [x] Dynamic version in **init**.py (reads from package metadata)

### Version Management

- [x] Strict version requirements (Python 3.13, Django 5.2.3, Wagtail 7.0.1)
- [x] Alpha status clearly marked in classifiers
- [x] Single source of truth for version (pyproject.toml)

### Documentation

- [x] Updated README with alpha warning
- [x] Created comprehensive CHANGELOG with limitations
- [x] Created roadmap (docs/roadmap.md)
- [x] Created release process guide (docs/release_process.md)
- [x] Updated installation docs with version warnings

### Package Validation

- [x] Package builds successfully: `uv build`
- [x] All templates included in distribution
- [x] All static files included in distribution
- [x] All migrations included in distribution
- [x] Ruff checks pass: `ruff check .`

## ✅ Example Project & Testing

### Example Project

- [x] Basic structure created
- [x] Settings, URLs, WSGI/ASGI configured
- [x] Home and search apps created
- [x] Templates and base.html created
- [x] README with setup instructions
- [x] **FULLY FUNCTIONAL** - All features working
  - All setup steps verified and documented
  - Database migrations working
  - SCORM package upload and extraction tested
  - Course enrollment workflow complete
  - SCORM player and API fully functional

### Testing & Quality Assurance

- [x] **Comprehensive test suite** - 86% code coverage
  - [x] Unit tests for all models (SCORMPackage, CoursePage, CourseEnrollment, SCORMAttempt, SCORMData)
  - [x] View tests for SCORM player, enrollment, and content serving
  - [x] Complete SCORM API endpoint testing (Initialize, Terminate, Get/SetValue, Commit)
  - [x] Integration tests for full course workflows
  - [x] Concurrent operation testing
  - [x] Security and authentication tests
  - [x] Test fixtures for SCORM 1.2 and 2004 packages
- [x] Code quality tools configured (ruff, pre-commit)
- [x] Test infrastructure (pytest, pytest-django, pytest-cov)

### Full Workflow Testing

- [x] Install package: `uv pip install -e .`
- [x] Run example project with fresh database
- [x] Upload actual SCORM package
- [x] Create course page
- [x] Test enrollment
- [x] Test SCORM player
- [x] Verify SCORM API works with real content
- [x] Test suspend/resume functionality
- [x] Verify progress tracking
- [x] Test multiple users same course

### Bug Fixes

- [x] Fixed Wagtail preview mode error (ValueError with unsaved pages)
- [x] Fixed SQLite database lock errors (retry logic with exponential backoff)
- [x] Added transaction atomicity for SCORM data writes

## 🚧 Before PyPI Release

### Must Do

- [ ] Create release tag (v0.1.0)
- [ ] Test package installation in fresh virtualenv
- [ ] Test installation from built wheel: `uv build && pip install dist/wagtail_lms-0.1.0-*.whl`
- [ ] Verify package metadata on test.pypi.org
- [ ] Final review of README and CHANGELOG

### Nice to Have

- [ ] Screenshots for documentation
- [ ] Video walkthrough
- [ ] Sample SCORM packages in repository

## 📋 Known Limitations (Documented)

1. **Single Version Tested** - Only verified on Python 3.13/Django 5.2.3/Wagtail 7.0.1
   - Other versions may work but are untested
   - Multi-version testing planned for v0.2.0
2. **Django Admin Required** - SCORM package upload requires Django admin
   - Pure Wagtail interface planned for v0.2.0
3. **SQLite Concurrency** - Database locks possible under heavy load
   - Retry logic implemented with exponential backoff
   - PostgreSQL recommended for production
4. **No CI/CD** - Manual testing required before commits
   - GitHub Actions pipeline planned for v0.2.0

## ✅ Ready for Release

**Status**: Package is production-ready for alpha release

- ✅ Core functionality complete and tested
- ✅ Example project fully functional
- ✅ Comprehensive test suite (86% coverage)
- ✅ Documentation complete
- ✅ Bug fixes implemented and tested
- ✅ All workflows verified with real SCORM content

**Release Confidence**: HIGH

The package has been thoroughly tested and debugged. All major workflows work correctly:

- Package upload and extraction ✓
- Course creation and enrollment ✓
- SCORM player and API ✓
- Progress tracking and persistence ✓
- Multiple users and concurrent operations ✓

**Next Steps**:

1. Build and test distribution package
2. Upload to test.pypi.org for verification
3. Create release tag and publish to PyPI
4. Announce on Wagtail community channels
