# Roadmap

This document outlines the planned development path for Wagtail LMS.

## Current Status: v0.9.0 (Alpha)

The current release includes **full H5P support, xAPI tracking, long-scroll lesson pages, and all prior SCORM infrastructure**.

**Completed in v0.9.0:**

✅ **H5P Activity Support**

- `H5PActivity` Wagtail snippet — upload `.h5p` packages, auto-extract, parse metadata
- `LessonPage` — long-scroll layout with StreamField body (RichText + H5PActivityBlock)
- `H5PAttempt`, `H5PXAPIStatement`, `H5PContentUserData` — progress, audit log, resume state
- xAPI ingestion endpoint with verb → attempt field mapping
- H5P resume/progress state endpoint (H5P content-user-data protocol)
- Secure H5P asset serving via `ServeH5PContentView`
- h5p-standalone v3.8.0 vendored; `h5p-lesson.js` with lazy loading and xAPI dispatch

✅ **Lesson and Course Completion Logic**

- Lesson completes when all H5P activities in it reach `completion_status="completed"`
- Course completes when all lessons containing H5P activities are complete
- Informational lessons (no H5P blocks) do not gate completion

**Previously completed:**

✅ **SCORM 1.2/2004** — full runtime API, package upload/extraction, attempt tracking

✅ **Framework-Agnostic Templates** — BEM-style `.lms-*` classes, minimal default CSS

✅ **Comprehensive test suite** — models, views, SCORM API, H5P endpoints, integration workflows

✅ **CI/CD pipeline** — GitHub Actions, multi-version matrix, ruff, pre-commit

✅ **Fully functional example project** with complete setup guide

**Supported versions:**

- **Python:** 3.11, 3.12, 3.13, 3.14
- **Django:** 4.2 (LTS), 5.0, 5.1, 5.2 (LTS), 6.0
- **Wagtail:** 6.0, 6.2, 6.3, 7.1, 7.2, 7.3

Selected combinations tested in CI — see the [CI matrix](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/.github/workflows/ci.yml) for details.

---

## Version 0.10.0 — Downstream Integration

**Goal:** Remove integration friction for projects that build on top of wagtail-lms

This release addresses extensibility gaps discovered while integrating the package downstream (see [#73](https://github.com/dr-rompecabezas/wagtail-lms/issues/73), [#64](https://github.com/dr-rompecabezas/wagtail-lms/issues/64), [#63](https://github.com/dr-rompecabezas/wagtail-lms/issues/63), [#61](https://github.com/dr-rompecabezas/wagtail-lms/issues/61)). No new end-user features — the focus is on making the package easier to extend without monkey-patching.

### Extensibility Fixes

- [x] Set `LessonPage.parent_page_types = None` so `CoursePage` subclasses can host lesson pages without requiring downstream patches ([#73](https://github.com/dr-rompecabezas/wagtail-lms/issues/73))
- [x] Fix `H5PActivity` snippet registration to remove the duplicate Wagtail admin entry that bypasses custom upload flows ([#73](https://github.com/dr-rompecabezas/wagtail-lms/issues/73))
- [x] Add `WAGTAIL_LMS_SCORM_PACKAGE_VIEWSET_CLASS` and `WAGTAIL_LMS_H5P_ACTIVITY_VIEWSET_CLASS` settings so downstream projects can substitute their own upload viewsets ([#73](https://github.com/dr-rompecabezas/wagtail-lms/issues/73))
- [x] Add `WAGTAIL_LMS_CHECK_LESSON_ACCESS` setting — a dotted-path callable for customising the enrollment gate in `LessonPage.serve()` ([#64](https://github.com/dr-rompecabezas/wagtail-lms/issues/64))
- [x] Add `WAGTAIL_LMS_REGISTER_DJANGO_ADMIN` setting to opt out of automatic Django admin registration ([#63](https://github.com/dr-rompecabezas/wagtail-lms/issues/63))
- [x] Allow downstream projects to swap `SCORMPackage`/`H5PActivity` Django admin classes without calling `unregister()` ([#61](https://github.com/dr-rompecabezas/wagtail-lms/issues/61))

### Testing

- [ ] Verify H5P resume state with all supported activity types ([#71](https://github.com/dr-rompecabezas/wagtail-lms/issues/71))

---

## Version 0.11.0 — Q3 2026

**Goal:** Enhanced Wagtail integration and developer experience

### Wagtail Admin Improvements

- [ ] Replace Django admin with pure Wagtail admin for SCORM packages and enrollments
- [ ] Improved upload UX — validation feedback, progress indication
- [ ] Inline enrollment management in the Wagtail admin

### Documentation & Developer Experience

- [ ] Step-by-step course creation tutorial
- [ ] Docker Compose setup for quick local testing with pre-loaded sample content
- [ ] Improved error handling and logging for SCORM and H5P upload failures

### Testing & Quality

- [ ] Increase test coverage to 90%+

---

## Version 0.12.0 — Q4 2026

**Goal:** Enhanced LMS features and reporting

### Features

- [ ] Progress reporting — course completion reports and student progress dashboard
- [ ] Batch enrollment — enroll multiple users at once, import from CSV
- [ ] Course prerequisites — lock courses until required courses are complete
- [ ] Email notifications for enrollment and completion events

### Admin Enhancements

- [ ] Bulk SCORM package operations
- [ ] Advanced filtering and search
- [ ] Student progress monitoring in admin

---

## Version 1.0.0 (Stable) — 2027

**Goal:** Production-ready, feature-complete LMS with stable public API

### Stability

- [ ] Stable public API — no breaking changes within the 1.x series
- [ ] 90%+ test coverage
- [ ] Performance optimisation — query optimisation, caching strategies for large content

### Additional Features

- [ ] Multi-language support (i18n)
- [ ] Course versioning — update packages without losing learner progress
- [ ] LTI (Learning Tools Interoperability) support

---

## Version 2.0.0+ (long-term vision)

### xAPI / LRS Integration

- [ ] Learning Record Store (LRS) integration for external xAPI consumers
- [ ] Advanced analytics with xAPI data

### Advanced Learning Features

- [ ] Quizzing and assessment tools — built-in quiz builder, question banks, automated grading
- [ ] Discussion forums per course
- [ ] Gamification — badges, achievements, leaderboards

### Enterprise Features

- [ ] Organizations and subgroups
- [ ] Role-based access control (RBAC)
- [ ] RESTful API for course management and webhooks

---

## Contributing

We welcome contributions! If you're interested in working on any of these features:

1. Check the [GitHub Issues](https://github.com/dr-rompecabezas/wagtail-lms/issues) for current work
2. Comment on an issue to claim it or discuss your approach
3. Submit a PR following our [Contributing Guidelines](contributing.md)

## Feedback

Have ideas for features not listed here? Please:

- Open a [GitHub Discussion](https://github.com/dr-rompecabezas/wagtail-lms/discussions) to discuss ideas
- File a [Feature Request](https://github.com/dr-rompecabezas/wagtail-lms/issues/new) for specific proposals

---

*This roadmap is subject to change based on community feedback and priorities.*
