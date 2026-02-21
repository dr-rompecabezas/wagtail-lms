# API Reference

## URL Endpoints

### SCORM

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/lms/scorm-api/{attempt_id}/` | SCORM runtime API communication |
| `GET` | `/lms/scorm-content/{path}` | Secure SCORM asset serving |
| `GET` | `/lms/player/{course_id}/` | SCORM player view |
| `POST` | `/lms/enroll/{course_id}/` | Enroll the current user in a course |

### H5P

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/lms/h5p-xapi/{activity_id}/` | Ingest an xAPI statement for an H5P activity |
| `GET`, `POST` | `/lms/h5p-content-user-data/{activity_id}/` | Load/save H5P runtime state for resume/progress |
| `GET` | `/lms/h5p-content/{path}` | Secure H5P asset serving |

---

## SCORM Content View Customization

`wagtail_lms.views.ServeScormContentView` can be subclassed to customize SCORM asset
delivery without duplicating path-traversal protection:

- `get_storage_path(normalized_content_path)` — Build the full storage key from the
  normalized path. Override to change the base directory.
- `get_cache_control(content_type)` — Return a `Cache-Control` header value, or `None`
  to omit the header.
- `should_redirect(content_type, storage_path)` — Return `True` to issue a redirect to
  the storage URL instead of proxying the file (useful for large media on S3).
- `get_redirect_url(storage_path)` — Return the redirect URL (defaults to the storage
  backend's URL for the given path).

`wagtail_lms.views.ServeH5PContentView` is a minimal subclass that overrides only
`get_storage_path()` to use `WAGTAIL_LMS_H5P_CONTENT_PATH`.

---

## SCORM Runtime API Methods

The `POST /lms/scorm-api/{attempt_id}/` endpoint accepts a JSON body with a `method`
field and optional `params` list.

| Method | Description |
|--------|-------------|
| `Initialize()` | Start a SCORM session |
| `Terminate()` | End a SCORM session |
| `GetValue(element)` | Retrieve a CMI data model value |
| `SetValue(element, value)` | Store a CMI data model value |
| `Commit()` | Flush buffered data to the server |
| `GetLastError()` | Return the last error code |
| `GetErrorString(code)` | Return a human-readable error description |
| `GetDiagnostic(code)` | Return diagnostic information for an error code |

---

## H5P xAPI Endpoint

`POST /lms/h5p-xapi/{activity_id}/`

- **Auth:** Login required; CSRF protected.
- **Body:** JSON — any valid xAPI statement. The `verb.id` field drives attempt updates.

**Verb → attempt field mapping:**

| `verb.id` | Effect |
|-----------|--------|
| `.../completed` | `completion_status = "completed"` |
| `.../passed` | `success_status = "passed"`, `completion_status = "completed"` |
| `.../failed` | `success_status = "failed"` |
| `.../scored` | Score fields updated from `result.score` |

Scores are read from `result.score`: `raw`, `min`, `max`, `scaled`.

An `H5PAttempt` is created automatically on the first statement for a given
user/activity pair. Subsequent statements for the same pair update the existing attempt
and append a new `H5PXAPIStatement` record.

**Response:** `200 OK` with `{"status": "ok"}` on success, `400` for invalid JSON,
`405` for non-POST requests.

---

## H5P Content User Data Endpoint

`GET|POST /lms/h5p-content-user-data/{activity_id}/?dataType=<type>&subContentId=<id>`

- **Auth:** Login required.
- **CSRF:** Exempt (H5P runtime submits form-encoded AJAX internally).

**GET behavior**

- Returns saved value for `(user, activity_id, dataType, subContentId)`.
- Response shape: `{"success": true, "data": "<string>"}`.
- If no value exists: `{"success": true, "data": false}`.

**POST behavior**

- Form field `data` stores the value.
- Special case: `data=0` clears the stored value for that key.
- Response shape: `{"success": true}`.

This endpoint powers H5P resume/progress state and is wired via
`h5p-lesson.js` (`options.ajax.contentUserDataUrl` + `options.saveFreq`).

---

## Models

### SCORM

| Model | Purpose |
|-------|---------|
| `SCORMPackage` | Uploaded SCORM ZIP; auto-extracted on save |
| `SCORMAttempt` | Per-user, per-package learning attempt |
| `SCORMData` | Key-value CMI data store for an attempt |

### H5P

| Model | Purpose |
|-------|---------|
| `H5PActivity` | Uploaded `.h5p` package (Wagtail snippet); auto-extracted on save |
| `H5PAttempt` | Per-user, per-activity progress (completion, success, scores) |
| `H5PXAPIStatement` | Raw xAPI statement log for an attempt |
| `H5PContentUserData` | Per-user/activity runtime state used by H5P resume/progress |

### Course

| Model | Purpose |
|-------|---------|
| `CoursePage` | Wagtail Page representing a course; can hold a SCORM package |
| `LessonPage` | Child of `CoursePage`; StreamField body of rich text + H5P activities |
| `CourseEnrollment` | Tracks a user's enrollment in a course |

---

## Downstream Extensibility Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `WAGTAIL_LMS_SCORM_PACKAGE_VIEWSET_CLASS` | `"wagtail_lms.viewsets.SCORMPackageViewSet"` | Replace the SCORM package Wagtail admin viewset |
| `WAGTAIL_LMS_H5P_ACTIVITY_VIEWSET_CLASS` | `"wagtail_lms.viewsets.H5PActivityViewSet"` | Replace the H5P activity Wagtail admin viewset |
| `WAGTAIL_LMS_CHECK_LESSON_ACCESS` | `"wagtail_lms.access.default_lesson_access_check"` | Dotted-path callable used by `LessonPage.serve()` |
| `WAGTAIL_LMS_REGISTER_DJANGO_ADMIN` | `True` | Enable/disable wagtail-lms Django admin registration |
| `WAGTAIL_LMS_SCORM_ADMIN_CLASS` | `"wagtail_lms.admin.SCORMPackageAdmin"` | Dotted-path Django `ModelAdmin` for `SCORMPackage` |
| `WAGTAIL_LMS_H5P_ADMIN_CLASS` | `"wagtail_lms.admin.H5PActivityAdmin"` | Dotted-path Django `ModelAdmin` for `H5PActivity` |

`WAGTAIL_LMS_CHECK_LESSON_ACCESS` callable signature:

```python
def check_access(request, lesson_page, course_page) -> bool:
    ...
```

Return `True` to allow access, `False` to redirect learners to the parent course page with an error message.

---

## Subclassing CoursePage

If your project subclasses `CoursePage`, you **must** include `"wagtail_lms.LessonPage"`
in your subclass's `subpage_types` for H5P lessons to be available:

```python
class ExtendedCoursePage(CoursePage):
    subpage_types = ["wagtail_lms.LessonPage"]
    # ... your extra fields
```

`LessonPage.parent_page_types` is intentionally unrestricted (`None`), so no child-side patching is required.

If you previously set `subpage_types = []` to prevent child pages entirely, update it
before using H5P lessons. Wagtail will silently hide the "Add child page" option for
`LessonPage` if it is absent — editors will see no error, the option simply won't appear.

A Django system check (`wagtail_lms.W001`) will warn at startup if a `CoursePage`
subclass has `subpage_types` defined without `"wagtail_lms.LessonPage"`:

```
wagtail_lms.W001: ExtendedCoursePage subclasses CoursePage but its subpage_types does
not include 'wagtail_lms.LessonPage'. H5P lessons cannot be added to this page type.
```
