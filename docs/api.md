# API Reference

## SCORM API Endpoints

- `POST /lms/scorm-api/{attempt_id}/` - SCORM API communication
- `GET /lms/scorm-content/{path}` - Secure SCORM content serving

## Supported SCORM API Methods

- `Initialize()` - Start SCORM session
- `Terminate()` - End SCORM session
- `GetValue(element)` - Retrieve data
- `SetValue(element, value)` - Store data
- `Commit()` - Save data to server
- `GetLastError()` - Get error information
