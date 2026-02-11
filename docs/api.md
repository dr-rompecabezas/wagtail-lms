# API Reference

## SCORM API Endpoints

- `POST /lms/scorm-api/{attempt_id}/` - SCORM API communication
- `GET /lms/scorm-content/{path}` - Secure SCORM content serving

## SCORM Content View Customization

`wagtail_lms.views.ServeScormContentView` can be subclassed by downstream projects.
Override these hooks to customize behavior without duplicating path traversal checks:

- `get_cache_control(content_type)` - Return Cache-Control value or `None`
- `should_redirect(content_type, storage_path)` - Return `True` to redirect instead of proxying
- `get_redirect_url(storage_path)` - Return URL for redirects (defaults to storage URL)

## Supported SCORM API Methods

- `Initialize()` - Start SCORM session
- `Terminate()` - End SCORM session
- `GetValue(element)` - Retrieve data
- `SetValue(element, value)` - Store data
- `Commit()` - Save data to server
- `GetLastError()` - Get error information
