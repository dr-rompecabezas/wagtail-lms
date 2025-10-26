# Contributing to Wagtail LMS

Thank you for your interest in contributing to Wagtail LMS! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.13+ (only version tested)
- [uv](https://github.com/astral-sh/uv) package manager
- Git

### Getting Started

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/wagtail-lms.git
cd wagtail-lms
```

2. **Install all dependencies**

```bash
# Install core package + dev tools (ruff, pre-commit) + testing tools (pytest)
uv sync --group dev --extra testing
```

This installs:
- Core dependencies (Django, Wagtail)
- Dev tools (ruff, pre-commit)
- Testing tools (pytest, pytest-django, pytest-cov)

3. **Install pre-commit hooks**

```bash
uv run pre-commit install
```

This will automatically run code quality checks before each commit.

4. **Verify your setup**

```bash
# Run the test suite
PYTHONPATH=. uv run pytest

# Run code quality checks
uv run ruff check .
uv run ruff format --check .
```

## Development Workflow

### Making Changes

1. **Create a feature branch**

```bash
git checkout -b feature/amazing-feature
```

Use descriptive branch names:
- `feature/add-xapi-support`
- `fix/preview-mode-error`
- `docs/update-installation-guide`

2. **Make your changes**

- Write tests for new features
- Update documentation as needed
- Follow the existing code style

3. **Run tests**

```bash
# Run all tests
PYTHONPATH=. uv run pytest

# Run with coverage
PYTHONPATH=. uv run pytest --cov=src/wagtail_lms

# Run specific test file
PYTHONPATH=. uv run pytest tests/test_models.py -v
```

4. **Check code quality**

```bash
# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Run all pre-commit checks
uv run pre-commit run --all-files
```

### Testing Your Changes

Test your changes with the example project:

```bash
cd example_project

# Set up database (if needed)
PYTHONPATH=. python manage.py migrate

# Run the development server
PYTHONPATH=. python manage.py runserver
```

Visit http://localhost:8000 and test your changes in a real environment.

### Committing Changes

```bash
# Stage your changes
git add .

# Commit (pre-commit hooks will run automatically)
git commit -m "Add amazing feature"
```

**Commit message guidelines:**
- Use present tense ("Add feature" not "Added feature")
- Be descriptive but concise
- Reference issues when applicable: "Fix #123: Resolve preview error"

### Submitting a Pull Request

1. **Push your changes**

```bash
git push origin feature/amazing-feature
```

2. **Open a Pull Request** on GitHub

- Provide a clear description of the changes
- Reference any related issues
- Include screenshots for UI changes
- Describe how you tested the changes

3. **Address review feedback**

- Make requested changes in new commits
- Push to the same branch (PR updates automatically)
- Respond to comments

## Code Style Guidelines

### Python Code

- Follow PEP 8 (enforced by ruff)
- Maximum line length: flexible (E501 ignored)
- Use type hints where helpful
- Write docstrings for public functions/classes

### Django/Wagtail Patterns

- Follow Django best practices (enforced by ruff DJ rules)
- Use Wagtail's conventions for page models
- Keep views simple and focused
- Use Django's class-based views appropriately

### Testing

- Write tests for all new features
- Aim for 80%+ code coverage
- Use pytest fixtures from `tests/conftest.py`
- Name tests descriptively: `test_scorm_package_extraction`

## Project Structure

```
wagtail-lms/
├── src/wagtail_lms/     # Main package code
│   ├── models.py        # Django models
│   ├── views.py         # Views and SCORM API
│   ├── urls.py          # URL routing
│   └── templates/       # Django templates
├── tests/               # Test suite
│   ├── conftest.py      # Pytest fixtures
│   ├── test_models.py   # Model tests
│   ├── test_views.py    # View tests
│   └── test_integration.py
├── example_project/     # Example Wagtail site
└── docs/               # Documentation
```

## Getting Help

- **Questions?** Open a [Discussion](https://github.com/dr-rompecabezas/wagtail-lms/discussions)
- **Bug reports?** Open an [Issue](https://github.com/dr-rompecabezas/wagtail-lms/issues)
- **Security concerns?** Email the maintainers privately

## Development Tips

### Dependency Management

The project uses `uv.lock` to ensure consistent dependency versions:

```bash
# After pulling changes, sync to locked versions
uv sync --group dev --extra testing

# If you update dependencies in pyproject.toml
uv lock  # Update the lock file
```

### Running Example Project

```bash
cd example_project

# Fresh setup
rm db.sqlite3  # Remove old database
PYTHONPATH=. python manage.py migrate
PYTHONPATH=. python manage.py createsuperuser

# Run server
PYTHONPATH=. python manage.py runserver
```

### Debugging Tests

```bash
# Run with verbose output
PYTHONPATH=. uv run pytest -v

# Run specific test
PYTHONPATH=. uv run pytest tests/test_models.py::TestSCORMPackage::test_extraction -v

# Stop on first failure
PYTHONPATH=. uv run pytest -x

# Drop into debugger on failure
PYTHONPATH=. uv run pytest --pdb
```

## Code of Conduct

Please be respectful and constructive. We're all here to build something useful together.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
