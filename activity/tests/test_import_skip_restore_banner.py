from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import CustomUser
from activity.models import Activity, ActivityType, QuizType
from subject.models import Subject


CSV_BODY = (
    b'"What is 2 + 2?","1","3","4","5","6","4"\n'
    b'"Capital of France?","1","Berlin","Madrid","Paris","Rome","Paris"\n'
)


class ImportSkipsRestoreBannerTests(TestCase):
    """Bulk-importing MC questions should set a one-shot session flag that
    suppresses the autosave "Restore" banner on the next render of the
    quiz-type editor. The flag must be consumed on read so a second visit
    behaves normally."""

    def setUp(self):
        self.client = Client()
        # The quiz-type editor is gated by a `quiztype.add_quiztype` permission
        # whose app_label doesn't map to a real installed app, so in practice
        # only superusers (which bypass permission checks) can reach it.
        self.teacher = CustomUser.objects.create_superuser(
            username="teacher_import", email="ti@x.com", password="pw"
        )
        self.client.force_login(self.teacher)

        self.subject = Subject.objects.create(subject_name="Math")
        atype = ActivityType.objects.create(name="Quiz")
        self.activity = Activity.objects.create(
            activity_name="MC Import Test",
            activity_type=atype,
            subject=self.subject,
            max_score=0,
        )
        self.qt = QuizType.objects.get_or_create(name="Multiple Choice")[0]

    def _import_csv(self):
        csv = SimpleUploadedFile(
            "questions.csv", CSV_BODY, content_type="text/csv"
        )
        return self.client.post(
            reverse("add_question", args=[self.activity.id, self.qt.id]),
            {"csv_file": csv},
        )

    @patch(
        "activity.views.quiz_type_views.check_activity_access",
        return_value=(True, None),
    )
    def test_csv_import_sets_skip_restore_flag(self, _):
        resp = self._import_csv()
        self.assertEqual(resp.status_code, 302)

        # Server-side: session flag is set after import.
        self.assertTrue(
            self.client.session.get(f"qc_skip_restore_{self.activity.id}")
        )

        # First render: flag arrives in template context, then is cleared.
        resp = self.client.get(reverse("add_quiz_type", args=[self.activity.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["skip_restore_banner"])
        self.assertNotIn(
            f"qc_skip_restore_{self.activity.id}", self.client.session
        )
        # Imported questions made it into the session payload that drives
        # the editor.
        self.assertEqual(len(resp.context["questions"]), 2)

    @patch(
        "activity.views.quiz_type_views.check_activity_access",
        return_value=(True, None),
    )
    def test_flag_is_one_shot(self, _):
        self._import_csv()
        # Consume once.
        self.client.get(reverse("add_quiz_type", args=[self.activity.id]))
        # Second visit: no longer flagged, so the JS banner logic runs normally.
        resp = self.client.get(reverse("add_quiz_type", args=[self.activity.id]))
        self.assertFalse(resp.context["skip_restore_banner"])

    @patch(
        "activity.views.quiz_type_views.check_activity_access",
        return_value=(True, None),
    )
    def test_visit_without_import_has_no_flag(self, _):
        resp = self.client.get(reverse("add_quiz_type", args=[self.activity.id]))
        self.assertFalse(resp.context["skip_restore_banner"])
