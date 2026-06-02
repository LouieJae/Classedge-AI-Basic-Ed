"""[Classedge LMS] Enforce the '[Classedge LMS]' label on all instructor_grading public functions."""
import inspect

from django.test import TestCase

from gradebookcomponent.views import instructor_grading
from gradebookcomponent.services import access, grades, queue, override, csv_export


LABEL = "[Classedge LMS]"


class FunctionLabelTest(TestCase):
    def _check(self, module):
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            if obj.__module__ != module.__name__:
                continue  # skip re-exports
            doc = inspect.getdoc(obj) or ""
            src = inspect.getsource(obj)[:400]
            self.assertTrue(
                LABEL in doc or LABEL in src,
                f"{module.__name__}.{name} missing '{LABEL}' label",
            )

    def test_views(self):
        self._check(instructor_grading)

    def test_services(self):
        for mod in [access, grades, queue, override, csv_export]:
            self._check(mod)
