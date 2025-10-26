"""
Wagtail LMS - A Learning Management System extension for Wagtail
"""

from importlib.metadata import version

default_app_config = "wagtail_lms.apps.WagtailLmsConfig"

# Version is managed in pyproject.toml - this reads it dynamically
try:
    __version__ = version("wagtail_lms")
except Exception:
    __version__ = "unknown"

__author__ = "Felipe Villegas"
__email__ = "felavid@gmail.com"
