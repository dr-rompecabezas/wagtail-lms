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

### Course

| Model | Purpose |
|-------|---------|
| `CoursePage` | Wagtail Page representing a course; can hold a SCORM package |
| `LessonPage` | Child of `CoursePage`; StreamField body of rich text + H5P activities |
| `CourseEnrollment` | Tracks a user's enrollment in a course |
