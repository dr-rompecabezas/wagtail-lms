# Wagtail LMS Example Project

This is a minimal Wagtail project configured to demonstrate and test the `wagtail-lms` package.

## Purpose

This example project serves multiple purposes:

1. **Testing** - Validate that wagtail-lms works correctly when installed as a package
2. **Development** - Test new features and bug fixes in a real environment
3. **Documentation** - Provide a working reference for developers using wagtail-lms
4. **Demonstration** - Show how to integrate wagtail-lms into a Wagtail project

## Quick Start

**Note**: All commands should be run from the root of the `wagtail-lms` repository and require `PYTHONPATH=.` to ensure Python can find the `example_project` module.

### 1. Install Dependencies

From the root of the `wagtail-lms` repository:

```bash
# Creates a virtual environment and installs all dependencies
uv sync
```

### 2. Run Migrations

```bash
PYTHONPATH=. uv run python example_project/manage.py migrate
```

### 3. Create a Superuser

```bash
PYTHONPATH=. uv run python example_project/manage.py createsuperuser
```

Follow the prompts to create an admin user.

### 4. Start the Development Server

```bash
PYTHONPATH=. uv run python example_project/manage.py runserver
```

The site will be available at `http://localhost:8000`

### 5. Set Up the Home Page

Replace Wagtail's default welcome page with the example project `HomePage`:

```bash
PYTHONPATH=. uv run python example_project/manage.py setup_pages
```

The home page will now be visible at `http://localhost:8000/`

## Available URLs

- **Home**: <http://localhost:8000/>
- **Wagtail Admin**: <http://localhost:8000/admin/>
- **Django Admin**: <http://localhost:8000/django-admin/>
- **SCORM Packages**: <http://localhost:8000/lms/scorm-packages/>

## Using Wagtail LMS

### SCORM Courses

#### Upload a SCORM Package

1. Login to Django Admin: <http://localhost:8000/django-admin/>
2. Navigate to **Wagtail Lms** → **SCORM Packages**
3. Click **Add SCORM Package**
4. Upload a SCORM 1.2 or 2004 ZIP file
5. Add a title (required) and description (optional)
6. Save

The package will be automatically extracted and parsed.

#### Create a Course

1. Login to Wagtail Admin: <http://localhost:8000/admin/>
2. Navigate to **Pages**
3. Under the Home page, click **Add child page**
4. Select **Course Page**
5. Fill in the course details:
   - Title (required)
   - Description (optional)
   - Select the SCORM package you uploaded
6. Click **Publish**

#### Test the Course

1. Visit the course page URL (visible in the Wagtail admin)
2. Click **Enroll in Course** (you need to be logged in)
3. Click **Start Course** to launch the SCORM player
4. The SCORM content will load in an iframe with full API support

---

### H5P Lessons

H5P activities are reusable snippets that can be embedded inside a
long-scroll **LessonPage** alongside rich text, images, and other blocks.
A course can have multiple lessons; each lesson can contain multiple H5P
activities. Learner progress is tracked via xAPI statements.

#### 1. Upload an H5P Activity

> **Important: your `.h5p` file must be self-contained (includes library files).**
> h5p-standalone renders H5P content by loading library JavaScript files bundled
> inside the package (e.g. `H5P.InteractiveVideo-1.27/`). These are present in
> packages exported from an H5P editor but **not** in "Reuse" downloads from H5P.org.
>
> ✅ Works: **Download** from the H5P.org editor on your own authored content
> ✅ Works: **Export** from Moodle, WordPress, or Drupal with the H5P plugin
> ❌ Does not work: clicking **Reuse** on an H5P.org example page

1. Login to Wagtail Admin: <http://localhost:8000/admin/>
2. Navigate to **LMS** → **H5P Activities**
3. Click **Add H5P Activity**
4. Enter a title and upload a self-contained `.h5p` file
5. Save — the package is extracted and ready for use in lessons

> Alternatively, upload via Django Admin at **Wagtail Lms** → **H5P
> Activities**.

#### 2. Create a Course (if you haven't already)

1. In the Wagtail Admin, navigate to **Pages**
2. Under the Home page, click **Add child page** → **Course Page**
3. Fill in title and description (no SCORM package needed for H5P-only
   courses)
4. Publish

#### 3. Create a Lesson under the Course

1. Navigate to the Course page in the Wagtail page tree
2. Click **Add child page** → **Lesson Page**
3. Fill in:
   - **Title** (required)
   - **Intro** — optional introductory rich text shown above the body
   - **Body** — click **+** to add blocks:
     - **Paragraph** — rich text block for headings, text, images, etc.
     - **H5P Activity** — choose an H5P Activity snippet from the library
4. Publish

#### 4. Test the Lesson

1. Visit the lesson URL (visible in the Wagtail admin page tree)
2. Unenrolled users are redirected to the parent Course page to enroll
3. After enrolling, the lesson loads with all H5P activities lazy-loading
   as you scroll
4. Complete an H5P activity — xAPI statements are sent to the server and
   stored under **LMS** → **H5P Attempts** in the Wagtail admin

#### Reviewing Learner Progress

- **Wagtail Admin** → **LMS** → **H5P Attempts** — per-user, per-activity
  completion and score summary
- **Django Admin** → **Wagtail Lms** → **H5P Xapi Statements** — full raw
  xAPI statement log for debugging

## Project Structure

```text
example_project/
├── manage.py              # Django management script
├── README.md              # This file
├── db.sqlite3             # SQLite database (created after migrate)
├── media/                 # Uploaded files (SCORM packages, etc.)
├── static_collected/      # Collected static files (after collectstatic)
├── example_project/       # Main project directory
│   ├── __init__.py
│   ├── settings.py        # Django settings
│   ├── urls.py            # URL configuration
│   ├── wsgi.py            # WSGI entry point
│   ├── asgi.py            # ASGI entry point
│   ├── templates/         # Project-level templates
│   │   └── base.html      # Base template
│   └── static/            # Project static files (source)
├── home/                  # Home app
│   ├── models.py          # HomePage model
│   ├── templates/
│   └── migrations/
└── search/                # Search functionality
    ├── views.py
    └── templates/
```

## Common Tasks

### Reset the Database

```bash
rm example_project/db.sqlite3
PYTHONPATH=. uv run python example_project/manage.py migrate
PYTHONPATH=. uv run python example_project/manage.py setup_pages
PYTHONPATH=. uv run python example_project/manage.py createsuperuser
```

### Collect Static Files

```bash
PYTHONPATH=. uv run python example_project/manage.py collectstatic --noinput
```

### Run Django Shell

```bash
PYTHONPATH=. uv run python example_project/manage.py shell
```

### Create Migrations for wagtail-lms

If you're developing wagtail-lms and make model changes:

```bash
PYTHONPATH=. uv run python example_project/manage.py makemigrations wagtail_lms
```

## Testing Content Packages

### SCORM Packages

You can find free SCORM test packages here:

- [SCORM Cloud - Sample Courses](https://cloud.scorm.com/sc/guest/SignInForm)
- [Rustici Software - SCORM Sample Content](https://scorm.com/scorm-explained/scorm-resources/scorm-content-examples/)

### H5P Activities

You can find free H5P content here:

- [H5P.org - Example Content](https://h5p.org/content-types-and-applications) — click any activity type, then **Download** to get a `.h5p` file
- [H5P Hub](https://h5p.org/h5p-hub) — curated content library (requires free account)

## Troubleshooting

### Import Errors

If you get import errors for `wagtail_lms`, make sure you installed the package:

```bash
uv sync
```

### Database Errors

If migrations fail, try:

```bash
rm example_project/db.sqlite3
uv run python example_project/manage.py migrate
```

### SCORM Package Not Extracting

Check that:

- The ZIP file is a valid SCORM package
- It contains `imsmanifest.xml` at the root
- The `example_project/media/` directory exists and has write permissions

### H5P Activity Not Extracting

Check that:

- The file has a `.h5p` extension (it is a ZIP file internally)
- It contains `h5p.json` at the root
- The `example_project/media/` directory exists and has write permissions

### H5P Activity Shows "Could not load activity."

This almost always means the `.h5p` file is a **content-only "Reuse" export** that
does not include library JavaScript files. h5p-standalone needs the library files to
render the activity. The server log will contain a warning like:

```
H5P package '...' contains no library files.
```

Use a self-contained package instead — see the upload note in the H5P section above.

### H5P Activity Not Rendering

- Open the browser console for JavaScript errors
- Confirm static files are collected: `uv run python example_project/manage.py collectstatic --noinput`
- The `h5p-standalone` vendor bundles must be present under
  `src/wagtail_lms/static/wagtail_lms/vendor/h5p-standalone/`

### LessonPage "Add child page" Not Appearing

- The **Lesson Page** option only appears under a **Course Page**
- Confirm the Course Page is published before adding lessons

### Files Appearing in Project Root

If you see `media/` or `static/` directories in the project root instead of in `example_project/`, this means the settings weren't correctly configured. The fixed settings point to:

- `MEDIA_ROOT`: `example_project/media/`
- `STATIC_ROOT`: `example_project/static_collected/`

### Template Not Found

Make sure `APP_DIRS` is `True` in settings and the app is in `INSTALLED_APPS`.

## Development Workflow

When developing features for wagtail-lms:

1. Make changes to the code in `src/wagtail_lms/`
2. Test in this example project
3. If you changed models, create migrations
4. Run tests: `pytest`
5. Check code quality: `ruff check .`

## Notes

- This is a development/demo project - **DO NOT use in production**
- The SECRET_KEY is intentionally insecure for development
- DEBUG mode is enabled
- SQLite is used for simplicity (use PostgreSQL in production)

## License

This example project has the same license as wagtail-lms (MIT).
