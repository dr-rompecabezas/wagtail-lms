# Release Process

This guide outlines the steps for releasing a new version of Wagtail LMS to PyPI.

## Prerequisites

- Maintainer access to the GitHub repository
- PyPI account with access to the `wagtail-lms` project
- PyPI API token configured (recommended over password authentication)
- `uv` installed and up to date

## Pre-Release Checklist

Before starting the release process, ensure:

- [ ] All intended changes are merged to `main`
- [ ] All tests pass: `uv run pytest`
- [ ] Code quality checks pass: `uv run pre-commit run --all-files`
- [ ] Documentation is up to date
- [ ] CHANGELOG.md is updated with changes for this release
- [ ] No outstanding critical issues

## Release Steps

### 1. Update Version Number

Edit `pyproject.toml` and update the version number:

```toml
[project]
name = "wagtail_lms"
version = "0.2.0"  # Update this line
```

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backward compatible manner
- **PATCH** version for backward compatible bug fixes

### 2. Update CHANGELOG.md

Update the changelog with the release date:

```markdown
## [0.2.0] - 2025-11-15

### Added
- New feature X
- New feature Y

### Fixed
- Bug fix Z

### Changed
- Updated dependency versions
```

Ensure all changes since the last release are documented.

### 3. Commit Version Bump

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 0.2.0"
```

### 4. Run Full Test Suite

Ensure all tests pass before building:

```bash
# Run all tests with coverage
uv run pytest --cov=src/wagtail_lms

# Run pre-commit hooks
uv run pre-commit run --all-files

# Optional: Run tests against different Python versions if using tox
# uv run tox
```

### 5. Build the Package

Clean any previous builds and create distribution files:

```bash
# Remove old builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
uv build
```

This creates files in the `dist/` directory:

- `wagtail_lms-0.2.0.tar.gz` (source distribution)
- `wagtail_lms-0.2.0-py3-none-any.whl` (wheel)

### 6. Test on TestPyPI (Recommended)

Before publishing to the real PyPI, test on TestPyPI:

```bash
# Upload to TestPyPI
uv publish --publish-url https://test.pypi.org/legacy/
```

You'll be prompted for your TestPyPI credentials or API token.

Test the installation from TestPyPI:

```bash
# Create a test environment
uv venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ wagtail-lms

# Test that it imports correctly
python -c "import wagtail_lms; print(wagtail_lms.__version__)"

# Deactivate and remove test environment
deactivate
rm -rf test-env
```

### 7. Publish to PyPI

If TestPyPI testing was successful, publish to the real PyPI:

```bash
uv publish
```

**Using API Token (Recommended):**

Create a PyPI API token at <https://pypi.org/manage/account/token/>

**Option 1: Set environment variables:**

```bash
export UV_PUBLISH_USERNAME=__token__
export UV_PUBLISH_PASSWORD=pypi-YOUR_API_TOKEN_HERE
uv publish
```

**Option 2: Configure in `~/.pypirc`:**

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TESTPYPI_TOKEN_HERE
```

**Option 3: Use keyring (Most Secure):**

```bash
# Store token in system keyring
uv publish --keyring
```

### 8. Create Git Tag

Tag the release in git:

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin main
git push origin v0.2.0
```

### 9. Create GitHub Release

1. Go to <https://github.com/dr-rompecabezas/wagtail-lms/releases>
2. Click "Draft a new release"
3. Select the tag you just created (v0.2.0)
4. Title: "Release 0.2.0"
5. Description: Copy the relevant section from CHANGELOG.md
6. Attach the distribution files from `dist/` (optional)
7. Click "Publish release"

### 10. Verify Installation

Test that the package can be installed from PyPI:

```bash
# Create a fresh virtual environment
uv venv verify-env
source verify-env/bin/activate

# Install from PyPI
pip install wagtail-lms

# Verify version
python -c "import wagtail_lms; print(wagtail_lms.__version__)"

# Clean up
deactivate
rm -rf verify-env
```

### 11. Post-Release Tasks

- [ ] Announce the release on relevant channels (GitHub Discussions, Twitter, etc.)
- [ ] Update documentation if needed
- [ ] Close any resolved issues and milestones on GitHub
- [ ] Prepare the CHANGELOG.md for the next release by adding an "Unreleased" section:

```markdown
## [Unreleased]

### Added

### Fixed

### Changed
```

## Troubleshooting

### Build Fails

If `uv build` fails:

- Ensure `pyproject.toml` is valid TOML syntax
- Check that all required dependencies are specified
- Verify the project structure matches the package configuration

### Upload Fails

If `uv publish` fails:

- Verify your PyPI credentials/token (check environment variables or `~/.pypirc`)
- Ensure the version number hasn't already been published (PyPI doesn't allow overwriting)
- Check that you have maintainer access to the project
- Try using `--username __token__ --password <token>` flags directly

### Version Already Exists

PyPI does not allow re-uploading a version. If you need to fix something:

1. Delete the local `dist/` directory
2. Bump to a new version (e.g., 0.2.1)
3. Rebuild and re-upload

## Automation (Future)

Consider setting up GitHub Actions to automate:

- Running tests on every push
- Publishing to PyPI on tag creation
- Automated changelog generation

Example workflow trigger:

```yaml
on:
  push:
    tags:
      - 'v*'
```

## Resources

- [PyPI Publishing Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [Semantic Versioning](https://semver.org/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [uv Publish Guide](https://docs.astral.sh/uv/guides/publish/)
