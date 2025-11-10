# Roadmap

This document outlines the planned development path for Wagtail LMS.

## Current Status: v0.3.0 (Alpha)

The current release includes **framework-agnostic templates, comprehensive CI/CD infrastructure, and improved developer experience**.

**Completed in v0.3.0:**

✅ **Framework-Agnostic Templates** - Breaking changes for better flexibility

- Replaced Bootstrap-style classes with BEM-style `.lms-*` classes
- Added `lms/css/course.css` with minimal, functional default styles
- Works out of the box without external CSS frameworks
- Comprehensive template customization documentation with Bootstrap, Tailwind, and Bulma examples

✅ **Accessibility Improvements**

- Added `:focus` state to SCORM player back button for keyboard navigation
- Semantic HTML structure with proper ARIA roles
- Visible focus indicators for better accessibility

✅ **Developer Experience Enhancements**

- In-template comments explaining CSS requirements
- Updated release process to use `uv publish` instead of `twine`
- Example project demonstrates default LMS styling
- Testing infrastructure improvements (base.html for tests)

✅ **Documentation**

- New `docs/template_customization.md` with complete framework examples
- Dynamic template location finder
- FOUC (Flash of Unstyled Content) prevention guidance

✅ **Testing & Quality Infrastructure**

- CI/CD pipeline with GitHub Actions
  - Automated testing on every push and PR
  - Multi-version test matrix
  - Code quality checks (ruff, pre-commit)
- Multi-platform testing
  - Python: 3.11, 3.12, 3.13
  - Django: 4.2 LTS, 5.0, 5.1, 5.2
  - Wagtail: 6.0, 6.1, 6.2, 6.3, 7.0, 7.1

**Previously completed in v0.1.0:**

✅ **Comprehensive test suite** - 86% code coverage with 65+ tests

- Unit tests for all models, views, and SCORM API endpoints
- Integration tests for complete course workflows
- Concurrent operation and security testing
- Test fixtures for SCORM 1.2 and 2004 packages

✅ **Fully functional example project** with complete setup guide

✅ **Bug fixes** for preview mode and database concurrency

**Supported versions:**

- **Python:** 3.11, 3.12, 3.13
- **Django:** 4.2 (LTS), 5.0, 5.1, 5.2 (LTS)
- **Wagtail:** 6.0, 6.1, 6.2, 6.3, 7.0 (LTS), 7.1

All combinations tested in CI with strategic version matrix.

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

### xAPI/TinCan API Support

- [ ] xAPI statement storage and retrieval
- [ ] Learning Record Store (LRS) integration
- [ ] Advanced analytics with xAPI data
- [ ] Modern learning experience tracking

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
