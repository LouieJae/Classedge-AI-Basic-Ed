import inspect

from django.test import SimpleTestCase

from accounts.services import department_access
from accounts.views import department_admin
from accounts.views import registrar
from accounts.views import coil_admin
from accounts.views import academic_director
from calendars.services import department_filter


PUBLIC_MODULES = [department_access, department_admin, department_filter, registrar, coil_admin, academic_director]


class ClassedgeLMSLabelTests(SimpleTestCase):
    def test_every_public_function_is_labeled(self):
        missing = []
        for mod in PUBLIC_MODULES:
            for name, obj in inspect.getmembers(mod, inspect.isfunction):
                if name.startswith("_"):
                    continue
                if obj.__module__ != mod.__name__:
                    # Imported symbol, not owned by this module
                    continue
                doc = inspect.getdoc(obj) or ""
                if "[Classedge LMS]" not in doc:
                    missing.append(f"{mod.__name__}.{name}")
        self.assertFalse(missing, f"Missing [Classedge LMS] label: {missing}")
