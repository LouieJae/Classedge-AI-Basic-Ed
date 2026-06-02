# central_content/tests/test_settings.py
import importlib
import os

from django.test import SimpleTestCase


class CentralSettingsTests(SimpleTestCase):
    def test_central_settings_module_imports(self):
        os.environ["DJANGO_SETTINGS_MODULE"] = "lms.settings_central"
        module = importlib.import_module("lms.settings_central")
        self.assertEqual(module.ROOT_URLCONF, "central_content.urls")
        self.assertIn("central.classedge.app", module.ALLOWED_HOSTS)
        self.assertIsNone(module.SESSION_COOKIE_DOMAIN)
        self.assertEqual(module.SESSION_COOKIE_NAME, "central_sessionid")
