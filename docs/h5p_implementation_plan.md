# H5P Implementation Plan

**Status:** Planning complete, implementation not started (as of 2026-02-18)
**GitHub Issue:** [#57](https://github.com/dr-rompecabezas/wagtail-lms/issues/57)
**Mental model:** Articulate Rise — a long-scrolling lesson page that mixes rich text with embedded H5P interactive activities.

---

## Context and Design Decisions

### H5P is not SCORM

SCORM packages are self-contained courses. H5P packages are single interactive activities (a quiz, a drag-and-drop, a course presentation slide deck, etc.). A lesson is composed of *multiple* H5P activities interspersed with text.

### What we are NOT building

- In-admin H5P authoring (authors create content externally and export `.h5p` files)
- A full H5P platform/editor lifecycle
- Changes to the existing SCORM/CoursePage flow — that stays as-is and is in production use

### Existing SCORM flow — unchanged

`CoursePage` with a `scorm_package` FK continues to work exactly as before. The new H5P flow is additive.

---

## Target Architecture

### Page Hierarchy

```
CoursePage  (existing)
└── LessonPage  (new — one or more per course)
```

- `CoursePage.subpage_types = ["wagtail_lms.LessonPage"]`
- `LessonPage.parent_page_types = ["wagtail_lms.CoursePage"]`
- `LessonPage.subpage_types = []`

### Enrollment Gate

`LessonPage.serve()` is overridden to verify that `request.user` has a `CourseEnrollment` for the parent `CoursePage` before rendering. Unauthenticated users are redirected to login; enrolled users proceed normally. This is critical because `CoursePage` is tied to commercial checkout flows (e.g., thinkelearn.com via Stripe).

### Learner Experience

- Learner lands on the lesson page and scrolls linearly through the content
- Content blocks render top-to-bottom: paragraphs, headings, H5P activities
- H5P activities are embedded inline — no popups, no separate player pages
- Fullscreen uses the browser Fullscreen API in-place (H5P built-in, no UX disruption)

---

## New Models

### `H5PActivity` (Wagtail Snippet)

Registered with `@register_snippet` so it appears in the Wagtail chooser.

| Field | Type | Notes |
|---|---|---|
| `title` | `CharField(255)` | Display name in admin |
| `description` | `TextField(blank=True)` | Admin context only |
| `package_file` | `FileField` | Uploads to `h5p_packages/` (configurable via `WAGTAIL_LMS_H5P_UPLOAD_PATH`) |
| `extracted_path` | `CharField(500, blank=True)` | Auto-populated on save, e.g. `h5p_1_my_activity` |
| `main_library` | `CharField(255, blank=True)` | From `h5p.json`, e.g. `H5P.CoursePresentation` |
| `h5p_json` | `JSONField` | Full parsed `h5p.json` for reference |
| `created_at` | `DateTimeField(auto_now_add)` | |
| `updated_at` | `DateTimeField(auto_now)` | |

**Extraction flow** (mirrors `SCORMPackage`):
1. `save()` calls `super().save()` first to persist the file
2. If `package_file` exists and `extracted_path` is empty, calls `extract_package()`
3. `extract_package()` unzips `.h5p` to `h5p_content/h5p_{id}_{name}/` via `default_storage`
4. Path traversal protection: same logic as SCORM (normalize, reject `..` and absolute paths)
5. Captures `h5p.json` in-memory during extraction, calls `parse_h5p_json()`
6. `parse_h5p_json()` populates `main_library`, `h5p_json`, and `title` if not set
7. `save()` called again to persist `extracted_path`, `main_library`, `h5p_json`

**`get_content_base_url()`** returns `/lms/h5p-content/{extracted_path}` — the base URL passed to h5p-standalone's `h5pJsonPath` option. The player appends `/h5p.json`, `/content/content.json`, etc. to this.

**Cleanup signal:** `post_delete` signal deletes the uploaded `.h5p` file and the extracted directory (mirrors `post_delete_scorm_cleanup`).

---

### `LessonPage` (Wagtail Page)

| Field | Type | Notes |
|---|---|---|
| `intro` | `RichTextField(blank=True)` | Optional intro shown above the StreamField body |
| `body` | `StreamField` | See block types below |

**StreamField block types (MVP):**
- `paragraph` → `RichTextBlock()` — standard Wagtail rich text
- `h5p_activity` → `H5PActivityBlock` (see below) — inline H5P player

More block types (heading, image, callout, video) can be added later without migrations by extending the StreamField definition and providing block templates.

**`H5PActivityBlock`** (`StructBlock`):
```python
class H5PActivityBlock(StructBlock):
    activity = SnippetChooserBlock("wagtail_lms.H5PActivity")

    class Meta:
        icon = "media"
        label = "H5P Activity"
        template = "wagtail_lms/blocks/h5p_activity_block.html"
```

---

### `H5PAttempt`

One record per user + H5PActivity, created lazily on the first xAPI event.

| Field | Type | Notes |
|---|---|---|
| `user` | `ForeignKey(AUTH_USER_MODEL)` | |
| `activity` | `ForeignKey(H5PActivity)` | |
| `started_at` | `DateTimeField(auto_now_add)` | |
| `last_accessed` | `DateTimeField(auto_now)` | |
| `completion_status` | `CharField` | `not_attempted / incomplete / completed / unknown` |
| `success_status` | `CharField` | `passed / failed / unknown` |
| `score_raw` | `FloatField(null)` | |
| `score_min` | `FloatField(null)` | |
| `score_max` | `FloatField(null)` | |
| `score_scaled` | `FloatField(null)` | |

---

### `H5PXAPIStatement`

Raw xAPI statement log. One record per statement received. Granular, useful for debugging.

| Field | Type | Notes |
|---|---|---|
| `attempt` | `ForeignKey(H5PAttempt)` | |
| `verb` | `CharField(255)` | xAPI verb IRI, e.g. `http://adlnet.gov/expapi/verbs/completed` |
| `verb_display` | `CharField(255, blank=True)` | Human-readable, e.g. `completed` |
| `statement` | `JSONField` | Full xAPI statement JSON |
| `timestamp` | `DateTimeField(auto_now_add)` | |

---

### Configuration (`conf.py`)

```python
WAGTAIL_LMS_H5P_UPLOAD_PATH   # default: "h5p_packages/"
WAGTAIL_LMS_H5P_CONTENT_PATH  # default: "h5p_content/"
```

---

## New Views

### `h5p_xapi_view(request, activity_id)`

- **URL:** `POST /lms/h5p-xapi/<int:activity_id>/`
- **Auth:** `@login_required` (no `@csrf_exempt` — POST originates from our own page JS)
- **Flow:**
  1. Get `H5PActivity` by `activity_id`
  2. `H5PAttempt.objects.get_or_create(user=request.user, activity=activity)`
  3. Parse xAPI statement JSON from request body
  4. Create `H5PXAPIStatement`
  5. Update `H5PAttempt` fields based on verb (see mapping below)
  6. Return `JsonResponse({"status": "ok"})`

**Verb → Attempt field mapping:**

| xAPI Verb IRI | Effect on `H5PAttempt` |
|---|---|
| `.../verbs/completed` | `completion_status = "completed"` |
| `.../verbs/passed` | `completion_status = "completed"`, `success_status = "passed"` |
| `.../verbs/failed` | `success_status = "failed"` |
| `.../verbs/answered`, `.../verbs/scored`, `.../verbs/completed`, `.../verbs/passed`, `.../verbs/failed` | Update `score_raw/min/max/scaled` from `result.score` if present |

### `ServeH5PContentView`

Subclass of `ServeScormContentView`. Only override: `get_storage_path()` uses `WAGTAIL_LMS_H5P_CONTENT_PATH` instead of `WAGTAIL_LMS_CONTENT_PATH`. All path traversal protection, security headers, and caching inherited from base class.

- **URL:** `/lms/h5p-content/<path:content_path>`

---

## New URLs

```python
path("h5p-xapi/<int:activity_id>/",  views.h5p_xapi_view,          name="h5p_xapi"),
path("h5p-content/<path:content_path>", views.ServeH5PContentView.as_view(), name="serve_h5p_content"),
```

LessonPage URLs are handled by Wagtail page routing (no custom URL needed).

---

## Templates and Static Assets

### `lesson_page.html`

- Extends `base.html`
- Renders `page.intro` (richtext) then `{% include_block page.body %}`
- Loads `main.bundle.js` once at bottom of page
- Loads `h5p-lesson.js` (our custom JS, see below)

### `blocks/h5p_activity_block.html`

Renders a lightweight placeholder `<div>` with `data-` attributes. No player JS here — the shared `h5p-lesson.js` handles initialization.

```html
<div class="lms-h5p-activity"
     data-activity-id="{{ value.activity.pk }}"
     data-content-url="{{ value.activity.get_content_base_url }}"
     data-xapi-url="{% url 'wagtail_lms:h5p_xapi' value.activity.pk %}"
     data-xapi-iri="{{ request.scheme }}://{{ request.get_host }}/lms/h5p-activity/{{ value.activity.pk }}/">
  <div class="lms-h5p-activity__placeholder" id="h5p-placeholder-{{ value.activity.pk }}">
    <p>{{ value.activity.title }}</p>
  </div>
  <div id="h5p-container-{{ value.activity.pk }}"></div>
</div>
```

### `wagtail_lms/js/h5p-lesson.js`

Single shared script for all H5P activity blocks on a page. Responsibilities:

1. **Lazy init via `IntersectionObserver`** — watches all `.lms-h5p-activity` containers; initializes the h5p-standalone player when a container is within 300px of the viewport. Prevents loading activities the learner never reaches.

2. **One-time CSS injection** — injects `h5p.css` into `<head>` on first player init (avoids duplicate `<link>` tags).

3. **`H5P.externalDispatcher` proxy** — sets up `window.H5P.externalDispatcher` before player init so that iframe-embed-type H5P content can forward events to the parent window.

4. **xAPI event listener** — each player's `.then()` callback registers an `on('xAPI', ...)` listener. Events are filtered by `xAPIObjectIRI` (set per-activity) to prevent cross-contamination between multiple players on the same page.

5. **xAPI POST** — on matching event, `fetch()` POSTs to `data-xapi-url` with `X-CSRFToken` header. Failures are logged to console but do not interrupt the learner.

### Vendored static assets (already downloaded)

- `wagtail_lms/vendor/h5p-standalone/main.bundle.js` — h5p-standalone v3.8.0
- `wagtail_lms/vendor/h5p-standalone/frame.bundle.js`
- `wagtail_lms/vendor/h5p-standalone/styles/h5p.css`

---

## Admin Integration

### Wagtail Admin

- `H5PActivity` registered as a Wagtail Snippet (`@register_snippet`) → appears in chooser for `H5PActivityBlock`
- Add `H5PActivityViewSet` and `H5PAttemptViewSet` (read-only) to `LMSViewSetGroup` in `viewsets.py`

### Django Admin

- `H5PActivityAdmin` — list display: title, main_library, created_at; readonly: extracted_path, h5p_json
- `H5PAttemptAdmin` — list display: user, activity, completion_status, success_status, started_at
- `H5PXAPIStatementAdmin` — list display: attempt, verb_display, timestamp; searchable

---

## Signal Handlers

`post_delete_h5p_cleanup` — registered for `H5PActivity.post_delete`. Deletes:
1. The uploaded `.h5p` package file
2. The extracted content directory under `h5p_content/`

Uses `transaction.on_commit()` for safety, same pattern as `post_delete_scorm_cleanup`.

---

## Migration

One new migration: `0002_h5p_lesson.py`

Creates:
- `H5PActivity`
- `H5PAttempt`
- `H5PXAPIStatement`
- `LessonPage` (Wagtail Page subclass)

No changes to existing SCORM models or `CoursePage`. `CoursePage` gets `subpage_types` enforced at the Python level only (no schema change).

---

## Tests

New file: `tests/test_h5p.py`

### `H5PActivity` model tests
- Upload and extraction from a valid `.h5p` ZIP
- `h5p.json` parsing (title, mainLibrary)
- Path traversal protection (malicious ZIP members skipped)
- `get_content_base_url()` returns correct path
- Storage backend agnostic (using `InMemoryStorage` fixture)

### `LessonPage` tests
- Unauthenticated user redirected to login
- Authenticated but unenrolled user redirected to course page
- Enrolled user can access lesson
- StreamField renders paragraph and H5P activity blocks

### `h5p_xapi_view` tests
- Requires login
- GET returns 405
- Valid POST creates `H5PAttempt` + `H5PXAPIStatement`
- `completed` verb updates `completion_status`
- `passed` verb updates both `completion_status` and `success_status`
- `failed` verb updates `success_status`
- Score fields updated from `result.score`
- Subsequent POST to same activity reuses existing `H5PAttempt`

### `ServeH5PContentView` tests
- Serves files from H5P content path
- Rejects path traversal attempts
- Requires login
- Returns 404 for missing files

### Fixtures needed (add to `conftest.py`)
- `h5p_zip_file` — in-memory `.h5p` ZIP with `h5p.json` + `content/content.json`
- `h5p_activity` — saved `H5PActivity` instance with extracted content
- `lesson_page` — `LessonPage` child of `course_page` with one H5P activity block

---

## Implementation Order

Work in this order to keep the codebase in a runnable state at each step:

1. `conf.py` — add `H5P_UPLOAD_PATH` and `H5P_CONTENT_PATH` settings
2. `models.py` — add `H5PActivity`, `H5PAttempt`, `H5PXAPIStatement`, `LessonPage`
3. `signal_handlers.py` — add `post_delete_h5p_cleanup`; register in `apps.py`
4. `views.py` — add `h5p_xapi_view`, `ServeH5PContentView`
5. `urls.py` — add H5P URL patterns
6. `admin.py` — add H5P admin classes
7. `viewsets.py` — add H5P viewsets to `LMSViewSetGroup`
8. `templates/wagtail_lms/lesson_page.html` — LessonPage template
9. `templates/wagtail_lms/blocks/h5p_activity_block.html` — activity block template
10. `static/wagtail_lms/js/h5p-lesson.js` — lazy-load + xAPI JS
11. Migration — run `makemigrations`, review, commit
12. `tests/test_h5p.py` + `conftest.py` fixtures — test suite
13. Update `CLAUDE.md` with H5P architecture notes

---

## Explicitly Out of MVP Scope

- Lesson navigation menu / side panel
- Course cover page
- Lesson completion gates (must finish lesson N before N+1)
- Course-level progress aggregation across lessons
- Additional StreamField block types (heading, callout, image, video)
- H5P library version management
- Configurable completion rules per activity
- Reporting dashboard
- Certificates
- Multi-attempt scoring strategies (currently: last attempt wins)
- H5P authoring inside Wagtail (authors use external tools and export `.h5p`)

---

## Key Files to Touch

| File | Change |
|---|---|
| `src/wagtail_lms/conf.py` | Add H5P path settings |
| `src/wagtail_lms/models.py` | Add `H5PActivity`, `H5PAttempt`, `H5PXAPIStatement`, `LessonPage` |
| `src/wagtail_lms/signal_handlers.py` | Add H5P cleanup signal |
| `src/wagtail_lms/apps.py` | Register H5P signal |
| `src/wagtail_lms/views.py` | Add `h5p_xapi_view`, `ServeH5PContentView` |
| `src/wagtail_lms/urls.py` | Add H5P URL patterns |
| `src/wagtail_lms/admin.py` | Add H5P admin classes |
| `src/wagtail_lms/viewsets.py` | Add H5P viewsets |
| `src/wagtail_lms/templates/wagtail_lms/lesson_page.html` | New |
| `src/wagtail_lms/templates/wagtail_lms/blocks/h5p_activity_block.html` | New |
| `src/wagtail_lms/static/wagtail_lms/js/h5p-lesson.js` | New |
| `src/wagtail_lms/static/wagtail_lms/vendor/h5p-standalone/` | Already downloaded (v3.8.0) |
| `src/wagtail_lms/migrations/0002_h5p_lesson.py` | Generated |
| `tests/test_h5p.py` | New |
| `tests/conftest.py` | Add H5P fixtures |
| `CLAUDE.md` | Update with H5P architecture notes |
