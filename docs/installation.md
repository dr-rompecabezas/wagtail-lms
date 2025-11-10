# Installation Guide

## Requirements

**Supported versions:**

- **Python:** 3.11, 3.12, 3.13
- **Django:** 4.2 (LTS), 5.0, 5.1, 5.2 (LTS)
- **Wagtail:** 6.0, 6.1, 6.2, 6.3, 7.0 (LTS), 7.1

All combinations are tested in CI. See our [GitHub Actions workflow](https://github.com/dr-rompecabezas/wagtail-lms/actions/workflows/ci.yml) for the full compatibility matrix.

## Step-by-Step Installation

### 1. Install the package

```bash
pip install wagtail-lms
```

### 2. Configure Django Settings

Add `wagtail_lms` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    'home',
    'search',

    'wagtail_lms',  # Add this

    'wagtail.contrib.forms',
    # ... other Wagtail apps
]
```

### 3. Configure URLs

In your project's `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path('lms/', include('wagtail_lms.urls')),
    # ...
]
```

### 4. Run Migrations

```bash
python manage.py migrate wagtail_lms
```

### 5. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 6. Configure Media Files

Ensure your media settings are configured:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

In development, add to `urls.py`:

```python
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 7. Test the Installation

Start your development server:

```bash
python manage.py runserver
```

Visit:

- Admin: `http://localhost:8000/admin/`
- Django Admin: `http://localhost:8000/django-admin/`

## Next Steps

- **Try the Example Project**: See [example_project/README.md](../example_project/README.md) for a complete setup guide
- **Create Your First Course**: Upload a SCORM package via Django Admin, then create a Course Page in Wagtail Admin
- **Learn More**: Check out the [Testing Guide](testing.md) and [Roadmap](roadmap.md)
