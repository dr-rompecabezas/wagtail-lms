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
# Install the package in development mode
pip install -e .

# Or install with uv
uv pip install -e .
```

### 2. Create Home App Migrations

```bash
cd /path/to/wagtail-lms
PYTHONPATH=. python example_project/manage.py makemigrations home
```

### 3. Run Migrations

```bash
PYTHONPATH=. python example_project/manage.py migrate
```

### 4. Create a Superuser

```bash
PYTHONPATH=. python example_project/manage.py createsuperuser
```

Follow the prompts to create an admin user.

### 5. Start the Development Server

```bash
PYTHONPATH=. python example_project/manage.py runserver
```

The site will be available at `http://localhost:8000`

### 6. Set Up the Home Page

The first time you run the project, Wagtail creates a default "Welcome" page. Replace it with the custom HomePage:

1. Login to Wagtail Admin: <http://localhost:8000/admin/>

2. Go to **Pages** → Click the "Welcome to your new Wagtail site!" page

3. Click the three dots menu → **Delete**

4. Go back to **Pages** → Click **Add child page** at the root level

5. Select **Home Page**

6. Fill in:
   - Title: "Welcome to Wagtail LMS"
   - Body: Add welcome content (optional)

7. Click **Publish**

The home page will now be visible at `http://localhost:8000/`

## Available URLs

- **Home**: <http://localhost:8000/>
- **Wagtail Admin**: <http://localhost:8000/admin/>
- **Django Admin**: <http://localhost:8000/django-admin/>
- **SCORM Packages**: <http://localhost:8000/lms/scorm-packages/>

## Using Wagtail LMS

### Upload a SCORM Package

1. Login to Django Admin: <http://localhost:8000/django-admin/>
2. Navigate to **Wagtail Lms** → **SCORM Packages**
3. Click **Add SCORM Package**
4. Upload a SCORM 1.2 or 2004 ZIP file
5. Add a title and description
6. Save

The package will be automatically extracted and parsed.

### Create a Course

1. Login to Wagtail Admin: <http://localhost:8000/admin/>
2. Navigate to **Pages**
3. Under the Home page, click **Add child page**
4. Select **Course Page**
5. Fill in the course details:
   - Title
   - Description (optional)
   - Select the SCORM package you uploaded
6. Click **Publish**

### Test the Course

1. Visit the course page URL (visible in the Wagtail admin)
2. Click **Enroll in Course** (you need to be logged in)
3. Click **Start Course** to launch the SCORM player
4. The SCORM content will load in an iframe with full API support

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
rm example_project/home/migrations/0001_initial.py
PYTHONPATH=. python example_project/manage.py makemigrations home
PYTHONPATH=. python example_project/manage.py migrate
PYTHONPATH=. python example_project/manage.py createsuperuser
```

### Collect Static Files

```bash
PYTHONPATH=. python example_project/manage.py collectstatic --noinput
```

### Run Django Shell

```bash
PYTHONPATH=. python example_project/manage.py shell
```

### Create Migrations for wagtail-lms

If you're developing wagtail-lms and make model changes:

```bash
PYTHONPATH=. python example_project/manage.py makemigrations wagtail_lms
```

## Testing SCORM Packages

You can find free SCORM test packages here:

- [SCORM Cloud - Sample Courses](https://cloud.scorm.com/sc/guest/SignInForm)
- [Rustici Software - SCORM Sample Content](https://scorm.com/scorm-explained/scorm-resources/scorm-content-examples/)

## Troubleshooting

### Import Errors

If you get import errors for `wagtail_lms`, make sure you installed the package:

```bash
pip install -e .
```

### Database Errors

If migrations fail, try:

```bash
rm example_project/db.sqlite3
python example_project/manage.py migrate
```

### SCORM Package Not Extracting

Check that:

- The ZIP file is a valid SCORM package
- It contains `imsmanifest.xml` at the root
- The `example_project/media/` directory exists and has write permissions

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
