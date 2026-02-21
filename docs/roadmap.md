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

## Version 0.4.0 - Q3 2026

**Goal:** Enhanced Wagtail integration and developer experience

### Wagtail Integration Improvements

- [ ] Pure Wagtail admin interface
  - Replace Django admin with Wagtail SnippetViewSet or ModelAdmin
  - SCORM package upload directly in Wagtail admin
  - Drag-and-drop file upload with progress indication
- [ ] Improved admin UX
  - Better SCORM package validation feedback
  - Preview SCORM content in admin
  - Inline enrollment management

### Documentation & Developer Experience

- [ ] Comprehensive user guide
  - Step-by-step course creation tutorial
  - SCORM package preparation guide
  - Troubleshooting common issues
- [ ] API documentation improvements
  - Detailed SCORM API reference
  - Code examples for customization
- [ ] Docker setup for quick testing
  - Docker Compose configuration
  - Pre-loaded sample SCORM packages
- [ ] Improved error handling and logging
- [ ] Better validation messages for SCORM packages
- [ ] Configuration documentation

### Testing & Quality

- [ ] Increase test coverage to 90%+

## Version 0.5.0 - Q4 2026

**Goal:** Enhanced LMS features and reporting

### Features

- [ ] Progress reporting and analytics
  - Course completion reports
  - Student progress dashboard
  - Export reports to CSV/Excel
- [ ] Batch enrollment
  - Enroll multiple users at once
  - Import from CSV
  - Group-based enrollment
- [ ] Course prerequisites
  - Define required courses
  - Lock courses until prerequisites complete
- [ ] Notifications
  - Email notifications for enrollment
  - Completion certificates via email
- [ ] Course completion certificates
  - PDF certificate generation
  - Customizable certificate templates
  - Download and email options

### Admin Enhancements

- [ ] Bulk SCORM package operations
- [ ] Advanced filtering and search
- [ ] Student progress monitoring in admin

## Version 1.0.0 (Stable) - Q1 2027

**Goal:** Production-ready, feature-complete LMS

### Stability

- [ ] No breaking API changes for 1.x series
- [ ] Comprehensive documentation
- [ ] 90%+ test coverage
- [ ] Performance optimization
  - Database query optimization
  - Caching strategies for SCORM content
  - Large file upload handling

### Additional Features

- [ ] Multi-language support (i18n)
- [ ] Advanced SCORM features
  - Sequencing and navigation
  - Adaptive content delivery
- [ ] Course versioning
  - Update SCORM packages without losing progress
  - Migration tools for package updates
- [ ] LTI (Learning Tools Interoperability) support
  - Integration with external LMS platforms
  - SSO authentication

## Version 2.0.0+ (long-term vision)

### xAPI / LRS Integration

- [ ] Learning Record Store (LRS) integration for external xAPI consumers
- [ ] Advanced analytics with xAPI data

### Advanced Learning Features

- [ ] Quizzing and assessment tools
  - Built-in quiz builder
  - Question banks
  - Automated grading
- [ ] Discussion forums per course
- [ ] Live webinar integration
- [ ] Gamification
  - Badges and achievements
  - Leaderboards
  - Progress milestones

### Content Authoring

- [ ] Built-in content editor
  - Create simple courses without SCORM
  - Rich media support
- [ ] Content templates
- [ ] Multi-format export

### Enterprise Features

- [ ] Organizations and subgroups
- [ ] Role-based access control (RBAC)
- [ ] Custom branding per organization
- [ ] API for integrations
  - RESTful API for course management
  - Webhooks for events
- [ ] Advanced reporting
  - Custom report builder
  - Scheduled reports

## Contributing

We welcome contributions! If you're interested in working on any of these features:

1. Check the [GitHub Issues](https://github.com/dr-rompecabezas/wagtail-lms/issues) for current work
2. Comment on an issue to claim it or discuss your approach
3. Submit a PR following our [Contributing Guidelines](../CONTRIBUTING.md)

## Feedback

Have ideas for features not listed here? Please:

- Open a [GitHub Discussion](https://github.com/dr-rompecabezas/wagtail-lms/discussions) to discuss ideas
- File a [Feature Request](https://github.com/dr-rompecabezas/wagtail-lms/issues/new) for specific proposals

---

*This roadmap is subject to change based on community feedback and priorities.*
