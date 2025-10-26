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
- [x] Created CLAUDE.md for future development
- [x] Updated installation docs with version warnings

### Package Validation

- [x] Package builds successfully: `uv build`
- [x] All templates included in distribution
- [x] All static files included in distribution
- [x] All migrations included in distribution
- [x] Ruff checks pass: `ruff check .`

## ⚠️ Work In Progress

### Example Project

- [x] Basic structure created
- [x] Settings, URLs, WSGI/ASGI configured
- [x] Home and search apps created
- [x] Templates and base.html created
- [x] README with setup instructions
- [ ] **NEEDS DEBUGGING** - Project not fully functional yet
  - Multiple runtime issues discovered
  - Requires testing of full workflow
  - See `example_project/README.md` for details

## 🚧 Before Release

### Must Do

- [ ] Debug and test example_project completely
- [ ] Test full workflow:
  - [ ] Install package: `pip install -e .`
  - [ ] Run example project
  - [ ] Upload actual SCORM package
  - [ ] Create course page
  - [ ] Test enrollment
  - [ ] Test SCORM player
  - [ ] Verify SCORM API works
- [ ] Test package installation in fresh virtualenv
- [ ] Verify all URLs work correctly
- [ ] Test on actual SCORM content

### Should Do

- [ ] Add basic unit tests (even if minimal)
- [ ] Test installation from built package (not just -e)
- [ ] Create sample SCORM package for testing

### Nice to Have

- [ ] Screenshots for documentation
- [ ] Video walkthrough
- [ ] More comprehensive tests

## 📋 Known Issues

1. **Example Project** - Needs debugging before it's fully functional
2. **No Tests** - Package has minimal test coverage
3. **Single Version** - Only tested on Python 3.13/Django 5.2.3/Wagtail 7.0.1
4. **Django Admin Required** - Not pure Wagtail (planned for v0.2.0)

## 🎯 Decision Point

### Option A: Release Now (Not Recommended)

- Reserve PyPI name
- Mark as alpha with clear warnings
- Accept that example project is broken
- **Risk**: Poor first impression

### Option B: Debug First (Recommended)

- Get example project working
- Test full workflow with real SCORM
- Release with confidence
- **Timeline**: Additional 2-4 hours of work

## 📝 Notes for Next Session

When debugging example_project, start with:

1. Fresh database setup following README
2. Create superuser
3. Set up HomePage via admin
4. Upload SCORM package via Django admin
5. Create Course Page via Wagtail admin
6. Test enrollment and player

Focus on making the happy path work, then document any workarounds needed.
