# Release Process

This guide outlines the steps for releasing a new version of Wagtail LMS to PyPI.

## Prerequisites

- Maintainer access to the GitHub repository
- PyPI trusted publishing configured for the repository (see [Setup](#pypi-trusted-publishing-setup) below)
- Read the Docs versioning configured for release tags (see [Read the Docs Versioning Setup](#read-the-docs-versioning-setup-one-time))
- `uv` installed and up to date (for local testing)

## PyPI Trusted Publishing Setup

Wagtail LMS uses PyPI's [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) with GitHub Actions. This eliminates the need for API tokens and is more secure.

**One-time setup for maintainers (requires two steps):**

### Step 1: Configure PyPI Trusted Publisher

1. Go to <https://pypi.org/manage/project/wagtail-lms/settings/publishing/>
2. Add a new "pending publisher" with:
   - **PyPI Project Name**: `wagtail-lms`
   - **Owner**: `dr-rompecabezas`
   - **Repository name**: `wagtail-lms`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`
3. Repeat for TestPyPI at <https://test.pypi.org/manage/project/wagtail-lms/settings/publishing/>
   - Use environment name: `testpypi`

### Step 2: Create GitHub Environments

1. Go to <https://github.com/dr-rompecabezas/wagtail-lms/settings/environments>
2. Create the `pypi` environment:
   - Click "New environment"
   - Name: `pypi`
   - **Recommended**: Add yourself as a "Required reviewer" for manual approval before publishing
   - **Uncheck** "Prevent self-review" (only needed with multiple maintainers)
   - **Enable** "Allow administrators to bypass configured protection rules"
   - Click "Save protection rules"
3. Create the `testpypi` environment:
   - Click "New environment"
   - Name: `testpypi`
   - Leave protection rules empty (no approval needed for testing)
   - Click "Save protection rules"

Once configured, GitHub Actions can publish to PyPI without any API tokens. The `pypi` environment will require your manual approval for extra safety.

## Read the Docs Versioning Setup (One-Time)

This project starts versioned documentation releases at `v0.10.0` and does not backfill older tags.

1. Go to the Read the Docs project admin for Wagtail LMS.
2. Add an automation rule for tags with this regex:

   ```text
   ^v(?:0\.(?:1[0-9]|[2-9][0-9])\.[0-9]+|[1-9][0-9]*\.[0-9]+\.[0-9]+)$
   ```

3. Configure the rule to activate matching versions automatically.
4. Keep pre-`v0.10.0` tags inactive/hidden.
5. After `v0.10.0` is built, set the default documentation version to `stable` (recommended) and keep `latest` tracking `main`.

## Pre-Release Checklist

Before starting the release process, ensure:

- [ ] All intended changes are merged to `main`
- [ ] GitHub Actions CI is passing on `main` branch
- [ ] Documentation is up to date
- [ ] CHANGELOG.md is updated with changes for this release
- [ ] Read the Docs versioning rule for `v0.10.0+` is configured
- [ ] No outstanding critical issues

**Note**: GitHub Actions automatically runs tests and quality checks on every push. Ensure the CI badge shows passing before proceeding.

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

### 3. Commit and Push Version Bump

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 0.2.0"
git push origin main
```

### 4. Wait for CI to Pass

After pushing to `main`, wait for the CI workflow to complete successfully. You can monitor it at:

<https://github.com/dr-rompecabezas/wagtail-lms/actions>

Ensure all jobs (pre-commit, lint, and test) pass before proceeding.

### 5. Create GitHub Release

Creating a GitHub Release will automatically trigger the publish workflow that builds and uploads the package to PyPI.

**Using the GitHub web interface:**

1. Go to <https://github.com/dr-rompecabezas/wagtail-lms/releases>
2. Click "Draft a new release"
3. Click "Choose a tag" and type `v0.2.0` (create new tag on publish)
4. Set the target to `main` branch
5. Release title: "Release 0.2.0" or "Version 0.2.0"
6. Description: Copy the relevant section from CHANGELOG.md
7. Click "Publish release"

**Or using the GitHub CLI:**

```bash
gh release create v0.2.0 \
  --title "Release 0.2.0" \
  --notes-file <(sed -n '/## \[0.2.0\]/,/## \[/p' CHANGELOG.md | sed '$d')
```

**What happens next:**

- GitHub automatically creates the `v0.2.0` tag
- The `publish.yml` workflow is triggered automatically
- The workflow builds the package
- **If you configured required reviewers**: You'll need to manually approve the deployment to the `pypi` environment
- After approval (or if no approval required), the package is published to PyPI via trusted publishing
- You can monitor the workflow at: <https://github.com/dr-rompecabezas/wagtail-lms/actions>

### 6. Approve and Monitor the Publish Workflow

After creating the release, the publish workflow will start:

1. Go to <https://github.com/dr-rompecabezas/wagtail-lms/actions>
2. Look for the "Publish to PyPI" workflow run
3. **If you see "Waiting for approval"**:
   - Click on the workflow run
   - Click the "Review deployments" button
   - Check the `pypi` environment
   - Click "Approve and deploy"
4. Wait for the workflow to complete successfully (usually takes 1-2 minutes after approval)
5. If it fails, check the logs and troubleshoot (see [Troubleshooting](#troubleshooting) below)

### 7. Verify Read the Docs Version

After the release tag is created (for example, `v0.10.0`), verify docs versioning in Read the Docs:

1. Open the Read the Docs "Versions" page for the project.
2. Confirm the new tag version exists and its build is successful.
3. Confirm the version is active/public.
4. For the first versioned release (`v0.10.0`), confirm:
   - `stable` points to `v0.10.0`
   - `latest` still points to `main`
   - Default version is `stable`

### 8. Verify Installation

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

### 9. Post-Release Tasks

- [ ] Verify the package appears on PyPI: <https://pypi.org/project/wagtail-lms/>
- [ ] Announce the release on relevant channels (GitHub Discussions, social media, etc.)
- [ ] Update documentation if needed
- [ ] Close any resolved issues and milestones on GitHub
- [ ] Prepare the CHANGELOG.md for the next release by adding an "Unreleased" section:

```bash
git checkout main
git pull
# Edit CHANGELOG.md to add Unreleased section
git add CHANGELOG.md
git commit -m "Prepare CHANGELOG for next release"
git push origin main
```

Example unreleased section:

```markdown
## [Unreleased]

### Added

### Fixed

### Changed
```

## Troubleshooting

### CI Tests Fail

If the CI workflow fails on the `main` branch:

1. Check the workflow logs at <https://github.com/dr-rompecabezas/wagtail-lms/actions>
2. Fix the failing tests or linting issues
3. Push the fixes to `main`
4. Wait for CI to pass before creating the release

### Publish Workflow Fails

If the publish workflow fails after creating a release:

1. Check the workflow logs for the specific error
2. Common issues:
   - **Trusted publishing not configured**: Ensure PyPI trusted publishing is set up (see [Setup](#pypi-trusted-publishing-setup))
   - **GitHub environments not created**: Ensure both `pypi` and `testpypi` environments exist in GitHub repository settings. See [Step 2: Create GitHub Environments](#step-2-create-github-environments)
   - **Version already exists**: PyPI doesn't allow overwriting versions. You'll need to bump to a new version (e.g., 0.2.1), update CHANGELOG, commit, and create a new release
   - **Build errors**: Check that `pyproject.toml` is valid and the package structure is correct

### Version Already Exists on PyPI

PyPI does not allow re-uploading a version. If you need to fix something after publishing:

1. Bump to a new patch version (e.g., 0.2.0 → 0.2.1)
2. Update CHANGELOG.md with the fix
3. Commit and push to `main`
4. Create a new release with the new version tag

### Testing on TestPyPI Before Release

To test the build process before creating an official release, you can manually trigger the TestPyPI workflow:

1. Go to <https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/publish.yml>
2. Click "Run workflow"
3. Select the `main` branch
4. Click "Run workflow"

This will build and publish to TestPyPI without creating a release.

## Quick Reference

For experienced maintainers, here's the TL;DR:

```bash
# 1. Update version in pyproject.toml and CHANGELOG.md
# 2. Commit and push
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 0.2.0"
git push origin main

# 3. Wait for CI to pass, then create release
gh release create v0.2.0 \
  --title "Release 0.2.0" \
  --notes-file <(sed -n '/## \[0.2.0\]/,/## \[/p' CHANGELOG.md | sed '$d')

# 4. Approve deployment in GitHub Actions (if required reviewers configured)
# 5. Verify Read the Docs version build for the new tag
# 6. Monitor publish workflow and verify on PyPI
# 7. Update CHANGELOG.md with [Unreleased] section
```

## Resources

- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions Publishing to PyPI](https://docs.github.com/en/actions/deployment/deploying-to-your-cloud-provider/deploying-to-pypi)
- [Semantic Versioning](https://semver.org/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [GitHub CLI - Creating Releases](https://cli.github.com/manual/gh_release_create)
- [Read the Docs - Versioning](https://docs.readthedocs.io/en/stable/versions.html)
- [Read the Docs - Automation Rules](https://docs.readthedocs.io/en/stable/automation-rules.html)
