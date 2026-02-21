# Testing Guide

Wagtail LMS includes a comprehensive test suite covering models, views, API endpoints, and integration workflows.

## Test Coverage

The test suite covers:

- **Models**: SCORMPackage, CoursePage, CourseEnrollment, SCORMAttempt, SCORMData, H5PActivity, H5PAttempt, H5PXAPIStatement, H5PContentUserData, LessonPage, LessonCompletion
- **Views**: SCORM player, H5P xAPI endpoint, enrollment, content serving, resume state
- **SCORM API**: All runtime methods (Initialize, Terminate, GetValue, SetValue, Commit)
- **Integration**: Complete course workflows, concurrent operations
- **Security**: Authentication, authorization, path traversal protection

## Running Tests

**IMPORTANT**: All pytest commands must be run with `PYTHONPATH=.` to ensure Python can find the test modules.

### Run All Tests

```bash
PYTHONPATH=. uv run pytest
```

### Run with Coverage Report

```bash
PYTHONPATH=. uv run pytest --cov=src/wagtail_lms --cov-report=term-missing
```

### Run Specific Test File

```bash
PYTHONPATH=. uv run pytest tests/test_models.py -v
```

### Run Specific Test

```bash
PYTHONPATH=. uv run pytest tests/test_models.py::TestSCORMPackage::test_create_scorm_package -v
```

### Run with Verbose Output

```bash
PYTHONPATH=. uv run pytest -v
```

### Run with Short Traceback (for debugging)

```bash
PYTHONPATH=. uv run pytest tests/ -v --tb=short
```

## Test Structure

```text
tests/
├── conftest.py          # Test fixtures and configuration
├── settings.py          # Django settings for tests
├── urls.py              # URL configuration for tests
├── test_models.py       # Model tests
├── test_views.py        # View and API tests
└── test_integration.py  # Integration and workflow tests
```

## Test Fixtures

The test suite includes comprehensive fixtures in `tests/conftest.py`:

- **SCORM Packages**: Generators for SCORM 1.2 and 2004 manifest files
- **ZIP Files**: Dynamic SCORM package creation for testing
- **Users**: Regular users and superusers
- **Pages**: Wagtail page tree setup (root, home, course pages)
- **Database**: Isolated test database with proper cleanup

## Writing New Tests

### Model Tests

```python
import pytest
from wagtail_lms.models import SCORMPackage

@pytest.mark.django_db
class TestYourModel:
    def test_something(self, scorm_package):
        """Test description."""
        assert scorm_package.title == "Test SCORM Package"
```

### View Tests

```python
import pytest
from django.urls import reverse

@pytest.mark.django_db
class TestYourView:
    def test_view_requires_login(self, client, course_page):
        """Test that view requires authentication."""
        url = reverse('wagtail_lms:your_view', args=[course_page.id])
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login
```

### Integration Tests

```python
import json
import pytest
from django.urls import reverse

@pytest.mark.django_db
class TestYourWorkflow:
    def test_complete_workflow(self, client, user, course_page):
        """Test complete user workflow."""
        client.force_login(user)
        # ... test steps
```

## Test Database

Tests use an in-memory SQLite database configured in `tests/settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
```

Each test runs in a transaction that is rolled back after completion, ensuring test isolation.

## Continuous Integration

GitHub Actions runs the full test suite on every push and pull request. See [`.github/workflows/ci.yml`](https://github.com/dr-rompecabezas/wagtail-lms/blob/main/.github/workflows/ci.yml) for the current matrix of Python, Django, and Wagtail version combinations.

## Known Test Limitations

- **No Browser Tests**: No Selenium/Playwright tests for JavaScript interactions
- **Limited SCORM Packages**: Tests use minimal synthetic SCORM packages

## Contributing Tests

When contributing code, please:

1. Write tests for new features
2. Ensure existing tests pass: `PYTHONPATH=. uv run pytest`
3. Maintain or improve code coverage
4. Follow existing test patterns and naming conventions

See [Contributing Guide](contributing.md) for more details.
