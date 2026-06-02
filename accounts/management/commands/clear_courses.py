from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Course, Profile


class Command(BaseCommand):
    help = 'Clear all courses from the database. Profiles with course references will have their course set to NULL.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting',
        )

    def handle(self, *args, **options):
        # Count courses before deletion
        course_count = Course.objects.count()
        
        if course_count == 0:
            self.stdout.write(self.style.WARNING('No courses found in the database.'))
            return

        # Show what will be deleted
        self.stdout.write(self.style.WARNING(f'\nFound {course_count} course(s) to delete:'))
        for course in Course.objects.all()[:10]:  # Show first 10
            self.stdout.write(f'  - {course.name} (ID: {course.id})')
        
        if course_count > 10:
            self.stdout.write(f'  ... and {course_count - 10} more')

        # Count affected profiles
        affected_profiles = Profile.objects.filter(course__isnull=False).count()
        if affected_profiles > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n{affected_profiles} profile(s) have course references that will be set to NULL.'
                )
            )

        # Confirm deletion
        if not options['confirm']:
            self.stdout.write(self.style.WARNING('\nThis action cannot be undone!'))
            confirm = input('Are you sure you want to delete all courses? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Perform deletion in a transaction
        try:
            with transaction.atomic():
                # Django will automatically set Profile.course to NULL because of on_delete=SET_NULL
                deleted_count = Course.objects.all().delete()[0]
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Successfully deleted {deleted_count} course(s).'
                    )
                )
                
                if affected_profiles > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {affected_profiles} profile(s) updated (course set to NULL).'
                        )
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Error deleting courses: {str(e)}')
            )
            raise
