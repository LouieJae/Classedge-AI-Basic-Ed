from django.core.management.base import BaseCommand

from module.models.module import Module
from activity.models.activity_model import Activity
from rag_tutor.tasks import index_content


class Command(BaseCommand):
    help = "Re-index all modules and activities for a subject into the RAG vector store."

    def add_arguments(self, parser):
        parser.add_argument("subject_id", type=int)

    def handle(self, *args, **options):
        subject_id = options["subject_id"]

        modules = Module.objects.filter(subject_id=subject_id)
        activities = Activity.objects.filter(subject_id=subject_id)

        count = 0
        for m in modules:
            if m.description:
                index_content("module", m.pk)
                count += 1
                self.stdout.write(f"  Indexed module: {m.file_name}")

        for a in activities:
            if a.activity_instruction:
                index_content("activity", a.pk)
                count += 1
                self.stdout.write(f"  Indexed activity: {a.activity_name}")

        self.stdout.write(self.style.SUCCESS(f"Done. Indexed {count} items for subject {subject_id}."))
