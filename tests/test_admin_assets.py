from django.test import override_settings

from wagtail_lms.wagtail_hooks import global_admin_css, global_admin_js


@override_settings(STATIC_URL="/s/")
def test_admin_css_uses_static_url_prefix():
    html = global_admin_css()
    assert '<link rel="stylesheet" href="/s/wagtail_lms/css/scorm-admin.css">' in html


@override_settings(STATIC_URL="/static/alt/")
def test_admin_js_uses_static_url_prefix():
    html = global_admin_js()
    assert '<script src="/static/alt/wagtail_lms/js/scorm-admin.js"></script>' in html
