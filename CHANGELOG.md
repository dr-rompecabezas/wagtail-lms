# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking Changes

- **`SCORMLessonPage` introduced; `CoursePage.scorm_package` removed** ([#82](https://github.com/dr-rompecabezas/wagtail-lms/pull/82))
  - SCORM delivery now lives at the lesson level: `SCORMLessonPage` is a Wagtail Page that is a direct child of `CoursePage` and holds a `scorm_package` FK and an `intro` rich-text field
  - `CoursePage.scorm_package` FK removed; the SCORM package chooser no longer appears in the course editor
  - A data migration automatically creates a `SCORMLessonPage` child for every existing `CoursePage` that had a `scorm_package` value
  - SCORM player URL changed: `/lms/player/<course_id>/` → `/lms/scorm-lesson/<lesson_id>/play/`; update any hard-coded URL reversals to `reverse("wagtail_lms:scorm_player", args=[scorm_lesson_page.id])`
  - `CourseEnrollment.get_progress()` removed; query `SCORMAttempt` directly per lesson

- **`LessonPage` renamed to `H5PLessonPage`; `LessonCompletion` renamed to `H5PLessonCompletion`**
  - DB tables, content types, and all internal references updated via `RenameModel` migrations
  - Update any downstream references to these model classes and their string labels (e.g. `"wagtail_lms.LessonPage"` → `"wagtail_lms.H5PLessonPage"`)
  - `WAGTAIL_LMS_CHECK_LESSON_ACCESS` callable is now invoked by `H5PLessonPage.serve()` (interface unchanged)

### Added

- **`SCORMLessonPage`** — new Wagtail Page delivering a single SCORM package; renders a launch button linking to the SCORM player; access gated to enrolled users (Wagtail editors bypass)
- **System check `wagtail_lms.W002`** — warns at startup when a `CoursePage` subclass defines `subpage_types` without `"wagtail_lms.SCORMLessonPage"`
- **Mixed-mode course completion** — `CourseEnrollment.completed_at` is now set when *all* lessons in a course are done, regardless of type: `H5PLessonPage` requires an `H5PLessonCompletion` record; `SCORMLessonPage` requires a `SCORMAttempt` with `completion_status` of `"completed"` or `"passed"`
- **Completion state visible in default templates** — the bundled templates now surface per-lesson and course-level completion state:
  - `course_page.html`: SCORM lesson list items show a checkmark when the user has a completed/passed attempt (mirrors existing H5P lesson checkmarks)
  - `scorm_lesson_page.html`: displays the current attempt's `completion_status` and `success_status` above the launch button; includes a back-link to the parent course
  - `h5p_lesson_page.html`: shows a "Lesson completed" banner when an `H5PLessonCompletion` record exists for the user
- **Lesson page layout styles moved to `course.css`** — `.lms-lesson` and related classes (`__header`, `__nav`, `__title`, `__intro`, `__block`, `__content`, `.lms-h5p-activity`) are now defined in the shared stylesheet rather than inline in `h5p_lesson_page.html`; `lms-button--secondary` added to complete the button palette

### Fixed

- **SCORM player enrollment gate now consistent with H5P lesson access** — Wagtail editors (users with `wagtailadmin.access_admin`) can access the SCORM player without being enrolled in the course, matching the existing editor bypass in `H5PLessonPage.serve()`
- **LMS admin menu items hidden for all users** — `ReadOnlyPermissionPolicy` blocked `add`/`change`/`delete` unconditionally (including for superusers), causing Wagtail's menu-visibility check to hide SCORM Attempts, H5P Attempts, and H5P Lesson Completions from the sidebar. Fixed by overriding `user_has_any_permission` to redirect to the `view` permission check instead.
- **`H5PLessonPage` and `SCORMLessonPage` displayed with incorrect casing** — Wagtail title-cases class names when no `verbose_name` is set, producing "H5p lesson page" and "Scorm lesson page" in the page type chooser. Explicit `verbose_name` values added to both models.

### Migration notes

1. Run `python manage.py migrate wagtail_lms` — migrations 0004–0006 apply automatically:
   - 0004: creates `SCORMLessonPage`, migrates existing `CoursePage.scorm_package` data, removes the field
   - 0005: renames `LessonPage` → `H5PLessonPage` and `LessonCompletion` → `H5PLessonCompletion`
   - 0006: removes any stale `lessonpage` / `lessoncompletion` ContentType rows left behind by the rename (see note below)
2. **Run `python manage.py fixtree` after migrating** — if a `CoursePage` previously had a `scorm_package` and the data migration in 0004 incremented the parent's `numchild` counter but the child page did not persist (can occur with SQLite under certain transaction conditions), the page tree will have an inconsistent `numchild`. `fixtree` detects and corrects this automatically; it is a no-op if the tree is already consistent.
3. Update `subpage_types` on any `CoursePage` subclasses to include `"wagtail_lms.H5PLessonPage"` and `"wagtail_lms.SCORMLessonPage"`
4. Update any template URL tags that referenced the old SCORM player URL (`wagtail_lms:scorm_player` now takes a `lesson_id`)
5. Remove references to `CoursePage.scorm_package` and `CourseEnrollment.get_progress()`

> **Note on stale ContentTypes (migration 0006):** Django's `RenameModel` migration updates the `django_content_type` row for the renamed model in-place. On some database/cache combinations an orphan row for the old model name (`lessonpage`, `lessoncompletion`) can survive alongside the new one. When present, this orphan causes an `AttributeError: 'NoneType' object has no attribute '_inc_path'` crash whenever Wagtail tries to add a child page under a `CoursePage` whose existing children include a page with the stale ContentType. Migration 0006 deletes these orphan rows unconditionally; it is safe to run even when the orphans were never created.

---

## [0.10.1] - 2026-02-22

### Fixed

- **Missing migration state update for `LessonPage.body`**
  - Added `src/wagtail_lms/migrations/0003_alter_lessonpage_body.py` so `makemigrations wagtail_lms --check --dry-run` no longer reports pending model changes on current supported stacks.

### Changed

- **CI now enforces migration-state consistency for `wagtail_lms`**
  - Added a dedicated workflow step running `python example_project/manage.py makemigrations wagtail_lms --check --dry-run` before tests.

## [0.10.0] - 2026-02-21

### Added

- **Downstream integration extension points** ([#73](https://github.com/dr-rompecabezas/wagtail-lms/issues/73), [#64](https://github.com/dr-rompecabezas/wagtail-lms/issues/64), [#63](https://github.com/dr-rompecabezas/wagtail-lms/issues/63), [#61](https://github.com/dr-rompecabezas/wagtail-lms/issues/61))
  - `LessonPage.parent_page_types` set to `None` so `CoursePage` subclasses can host lessons without monkey-patching
  - `WAGTAIL_LMS_SCORM_PACKAGE_VIEWSET_CLASS` / `WAGTAIL_LMS_H5P_ACTIVITY_VIEWSET_CLASS` settings for swapping Wagtail admin upload viewsets
  - `WAGTAIL_LMS_H5P_SNIPPET_VIEWSET_CLASS` setting for swapping the H5P snippet viewset without runtime mutation
  - `WAGTAIL_LMS_CHECK_LESSON_ACCESS` setting (dotted-path callable) used by `LessonPage.serve()` access gate
  - `WAGTAIL_LMS_REGISTER_DJANGO_ADMIN` setting to opt out of automatic Django admin model registration
  - `WAGTAIL_LMS_SCORM_ADMIN_CLASS` / `WAGTAIL_LMS_H5P_ADMIN_CLASS` settings for swapping Django admin classes without `unregister()`
  - New test coverage for all downstream extension points

### Changed

- **H5P snippet registration now uses explicit hidden snippet viewset**
  - Removed `@register_snippet` decorator from `H5PActivity` model
  - Registered `H5PActivity` snippet in hooks with a snippet viewset configured for chooser support without a duplicate sidebar admin entry
  - Added backward-compatible `lms_viewset_group` alias in hooks for downstream projects still migrating off in-place patching

- **Snippet model title panels fixed**
  - Replaced `TitleFieldPanel("title")` with `FieldPanel("title")` on `SCORMPackage` and `H5PActivity` to avoid `w-sync` slug-target JavaScript errors on non-Page models

### Documentation

- **MkDocs Material site with Read the Docs publishing**
  - Added `readthedocs.yaml` configuration for RTD builds using MkDocs
  - Added `mkdocs.yml` with Material theme, navigation, and search
  - Added `mkdocs-material` and `mkdocs-include-markdown-plugin` to `[project.optional-dependencies] docs`
  - `docs/index.md` rewritten as a proper landing page with feature highlights and quick-install snippet
  - `docs/changelog.md` and `docs/contributing.md` added as thin `include-markdown` wrappers so `CHANGELOG.md` and `CONTRIBUTING.md` are included verbatim in the site without duplication
  - `docs/testing.md` updated: H5P models documented, hardcoded CI matrix replaced with a link to the workflow file
  - `docs/roadmap.md` updated: current status set to v0.9.0, H5P activity support marked complete, v0.10.0 section added (downstream integration fixes — issues [#73](https://github.com/dr-rompecabezas/wagtail-lms/issues/73), [#64](https://github.com/dr-rompecabezas/wagtail-lms/issues/64), [#63](https://github.com/dr-rompecabezas/wagtail-lms/issues/63), [#61](https://github.com/dr-rompecabezas/wagtail-lms/issues/61), [#71](https://github.com/dr-rompecabezas/wagtail-lms/issues/71)), future versions renumbered to 0.11.0 / 0.12.0 / 1.0.0
  - RTD documentation badge added to `README.md`

- **Read the Docs release-versioning rollout for v0.10.0+**
  - Pinned docs build dependencies, documented one-time RTD automation/default-version setup, added post-release RTD version verification, and fixed docs links so MkDocs strict mode passes

### Deprecated

- `WAGTAIL_LMS_CONTENT_PATH` renamed to `WAGTAIL_LMS_SCORM_CONTENT_PATH` for consistency with the `WAGTAIL_LMS_SCORM_*` prefix convention. The old name still works and its configured value is honoured, but it now emits a `DeprecationWarning` at startup. It will be removed in a future release — rename the setting in your Django settings to silence the warning.

## [0.9.0] - 2026-02-20

### Added

- **H5P activity support** ([#57](https://github.com/dr-rompecabezas/wagtail-lms/issues/57), [#60](https://github.com/dr-rompecabezas/wagtail-lms/issues/60), [#65](https://github.com/dr-rompecabezas/wagtail-lms/issues/65), [#66](https://github.com/dr-rompecabezas/wagtail-lms/issues/66))
  - `H5PActivity` Wagtail snippet — upload `.h5p` packages, auto-extract to any Django storage backend (local, S3, etc.), parse `h5p.json` metadata; choosable in lesson composition blocks; respects `WAGTAIL_LMS_H5P_UPLOAD_PATH` and `WAGTAIL_LMS_H5P_CONTENT_PATH` settings
  - `LessonPage` Wagtail page — long-scroll layout with `StreamField` body (`RichTextBlock` + `H5PActivityBlock`); enforces page hierarchy under `CoursePage`; enrollment gate in `serve()` redirects unenrolled users to the parent course
  - `H5PAttempt` — per-user, per-activity progress record (completion/success status, raw/min/max/scaled scores); lazily created on first xAPI event; DB-level `unique_together` on `(user, activity)`
  - `H5PXAPIStatement` — append-only xAPI statement log with verb display and full raw payload
  - `POST /lms/h5p-xapi/<activity_id>/` — CSRF-protected xAPI ingestion endpoint; validates that `verb` and `result` are JSON objects (returns 400 otherwise); maps `completed`, `passed`, `failed`, and `scored` verbs to attempt fields; sets `CourseEnrollment.completed_at` on `completed` or `passed`
  - `GET /lms/h5p-content/<path>` — authenticated H5P asset serving via `ServeH5PContentView`, a subclass of `ServeScormContentView`; inherits the same extensibility hooks (`get_storage_path`, `get_cache_control`, `should_redirect`, `get_redirect_url`) and path-traversal protection; content URL built via `reverse()` so any URL mount point is respected
  - `H5PActivityViewSet` (full CRUD) and `H5PAttemptViewSet` (read-only) added to the `LMSViewSetGroup` Wagtail admin menu; Django admin registrations included
  - **h5p-standalone v3.8.0** (MIT) vendored: `main.bundle.js`, `frame.bundle.js`, `styles/h5p.css`
  - `h5p-lesson.js` — `IntersectionObserver` lazy loading (300 px look-ahead); xAPI listener registered synchronously before player init so the same activity embedded multiple times on a page never double-posts; `X-CSRFToken` on every fetch; append `?h5pLazy=0` to the lesson URL to disable lazy loading and initialise all activities immediately (useful for debugging); append `?h5pDebug=1` to enable verbose console logging of xAPI routing decisions, resume preload results, and dispatcher lifecycle events
  - H5P file cleanup on package deletion via `post_delete` signal, mirroring existing SCORM behaviour
  - Example project updated with H5P workflow documentation and navigation link

- **H5P resume state persistence**
  - `H5PContentUserData` model — stores per-user, per-activity H5P runtime state keyed by `(attempt, data_type, sub_content_id)`; `unique_together` constraint prevents duplicate rows; auto-managed `created_at`/`updated_at` timestamps
  - `GET /lms/h5p-content-user-data/<activity_id>/` — returns saved state payload or `{"success": true, "data": false}` for first-time learners; does not create an attempt record on read
  - `POST /lms/h5p-content-user-data/<activity_id>/` — stores or updates state payload; H5P's clear signal (`data=0`) deletes the row; rejects payloads exceeding 64 KB (HTTP 413) to prevent storage exhaustion
  - State is pre-fetched before H5P Standalone initialises and passed as `contentUserData` so learners resume where they left off without an extra round-trip after load
  - Verified with `H5P.QuestionSet`; Django admin registration included

- **Per-lesson completion tracking** (closes [#69](https://github.com/dr-rompecabezas/wagtail-lms/issues/69))
  - `LessonCompletion` model — records when a user has completed every H5P activity in a `LessonPage`; `unique_together = ("user", "lesson")` prevents duplicate rows; idempotent via `get_or_create`
  - Course enrollment is now marked complete only when every live lesson in the course has a `LessonCompletion` record, replacing the previous single-activity trigger
  - `CoursePage.get_context()` now emits `completed_lesson_ids` (a `set` of lesson PKs) so the template can render per-lesson progress indicators in a single extra query
  - `course_page.html` lesson items gain `lms-lesson-list__item--completed` CSS class and a checkmark (`✓`) when the lesson has a completion record
  - `LessonCompletionViewSet` (read-only) added to the `LMSViewSetGroup` Wagtail admin menu; Django admin registration included
  - Comprehensive xAPI verb coverage — all verbs that signal a learner has fully interacted with an activity now trigger lesson/course completion:
    - `completed`, `passed` — unchanged behaviour
    - `answered` (top-level only) — primary terminal verb for standalone question types (MultiChoice, TrueFalse, Blanks, DragDrop, MarkTheWords, FindHotspot, Summary, ArithmeticQuiz, SpeakTheWords, Flashcards, Crossword, Essay); child-question `answered` statements from inside containers (QuestionSet, InteractiveVideo, etc.) are filtered out via `context.contextActivities.parent` so they don't prematurely complete a lesson
    - `mastered` — emitted by H5P.Essay on a perfect score; treated as `completed + passed`
    - `failed` — completion and success are now tracked orthogonally; a learner who submits and fails has still finished the activity and must not be blocked from progressing
    - `consumed` (`http://activitystrea.ms/schema/1.0/consume`) — emitted by informational types (H5P.Accordion, H5P.Column) that have no pass/fail state (closes [#70](https://github.com/dr-rompecabezas/wagtail-lms/issues/70))

- **System check `wagtail_lms.W001`** ([#65](https://github.com/dr-rompecabezas/wagtail-lms/issues/65))
  - Raised at startup when a `CoursePage` subclass defines `subpage_types` without `"wagtail_lms.LessonPage"`, preventing the Wagtail editor from silently omitting lessons; see `docs/api.md` for the upgrade guide

- **Course page lists and links to lesson pages**
  - `CoursePage.get_context()` now includes `lesson_pages` (live `LessonPage` children, ordered by tree position)
  - `course_page.html` displays a numbered lesson list with direct links when lessons exist; enrolled users see their enrollment date, unenrolled users see an enroll CTA
  - The "no content" notice now correctly reflects courses that have neither a SCORM package nor any lesson pages
  - Sidebar shows the lesson count alongside existing SCORM metadata

### Fixed

- **H5P completion now requires enrollment before writing lesson/course progress**
  - `_mark_h5p_enrollment_complete()` now skips completion writes unless the user has a `CourseEnrollment` for the parent course
  - Prevents pre-enrollment xAPI submissions from pre-creating `LessonCompletion` records and bypassing course progression gates after later enrollment

- **Migration compatibility restored for Wagtail 6.0/6.1 baselines**
  - `wagtailcore` migration dependencies were aligned to the oldest shared node (`0091_remove_revision_submitted_for_moderation`) across app and example migrations
  - H5P `StreamField` migration serialization was rewritten to explicit block classes (no `block_lookup` kwarg), so historical migrations load on supported Wagtail 6.x versions

- **Security: path-normalization bypass in ZIP extraction and content-directory deletion**
  - `posixpath.normpath("a/..")` resolves to `"."`, which previously passed the traversal guard; in the deletion path this would have wiped the entire base content directory on package removal. Guard now also rejects the `"."` result. Fix applied to ZIP extraction in both the SCORM and H5P extractors and to `_delete_extracted_content`.

- **Example project: broken CSS path since v0.4.0**
  - `base.html` still referenced `lms/css/course.css` after static assets moved to `wagtail_lms/css/course.css` in v0.4.0; LMS styles were silently absent in the example project. Corrected to `{% static 'wagtail_lms/css/course.css' %}`.

### Known Limitations (0.9.0)

- Activities that emit only `consumed` (e.g. `H5P.Accordion`) do not persist resume state — they have no meaningful resume position, so resetting on reload is the correct behaviour
- Resume state has been verified with `H5P.QuestionSet`; other activity types have not yet been systematically tested ([#71](https://github.com/dr-rompecabezas/wagtail-lms/issues/71))

### Changed

- **Default `WAGTAIL_LMS_AUTO_ENROLL` reverted to `False`**
  - v0.8.1 changed the default to `True`; upcoming v0.9.0 returns to `False` so explicit enrollment is the default behavior
  - Set `WAGTAIL_LMS_AUTO_ENROLL = True` to keep the v0.8.1 auto-enrollment flow

## [0.8.1] - 2026-02-19

### Added

- Python 3.14 support; CI matrix rebalanced to two entries per Python version (3.11–3.14)

### Fixed

- **`CourseEnrollment.completed_at` now set on SCORM course completion** ([#60](https://github.com/dr-rompecabezas/wagtail-lms/issues/60))
  - When `cmi.core.lesson_status` is set to `"completed"` or `"passed"`, the linked `CourseEnrollment.completed_at` is updated atomically in the same transaction
  - Uses a queryset `.update()` with `completed_at__isnull=True` to be idempotent — existing timestamps are never overwritten
  - Downstream projects relying on `completed_at` for prerequisite checks and dashboard completion tracking will now work correctly without manual admin intervention

- **`WAGTAIL_LMS_AUTO_ENROLL` setting is now wired up** ([#62](https://github.com/dr-rompecabezas/wagtail-lms/issues/62))
  - Setting was defined in `conf.py` but never read; the SCORM player always auto-enrolled users
  - Default changed from `False` → `True` to preserve existing behaviour
  - With `WAGTAIL_LMS_AUTO_ENROLL = False`, unenrolled users who reach the SCORM player are redirected to the course page with an error message instead of being silently enrolled

## [0.8.0] - 2026-02-16

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
- **Deprecated `serve_scorm_content` compatibility wrapper** ([#56](https://github.com/dr-rompecabezas/wagtail-lms/issues/56))
  - Removed `serve_scorm_content()` function alias in `wagtail_lms.views`
  - Removed one-time deprecation warning globals (`_serve_scorm_content_view`, `_serve_scorm_content_warned`)
  - Removed deprecated-wrapper warning test (`test_serve_scorm_content_import_warning_emitted_once`)

### Changed

- `uv.lock` removed from version control; lock file patterns added to `.gitignore`
  - This is a reusable library — pinning transitive dependencies in the repo is inappropriate for end users
  - Contributors should run `uv sync` to generate a local lock file

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
  - See [Template Customization Guide](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/docs/template_customization.md) for examples

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
