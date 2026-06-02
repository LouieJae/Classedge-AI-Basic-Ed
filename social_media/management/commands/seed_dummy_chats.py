"""
Seed dummy Chat messages so the inbox UI has something to show.

Usage:
    python manage.py seed_dummy_chats              # seeds chats for *every* user with at least one Friend
    python manage.py seed_dummy_chats --user louie # seeds only for the user with that username
    python manage.py seed_dummy_chats --clear      # delete the dummy chats this command produced
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from django.db.models import Q

from social_media.models import Chat, Friend


User = get_user_model()

DUMMY_LINES = [
    "Hey, did you see today's announcement?",
    "Don't forget about the meeting tomorrow at 10am.",
    "Could you share your notes from last week?",
    "Thanks for the help earlier — really appreciated it.",
    "Are you free this afternoon for a quick chat?",
    "Just submitted my work, fingers crossed!",
    "How was your weekend?",
    "Reminder: deadline is Friday — let me know if you need anything.",
    "I uploaded the file to the shared folder, can you take a look?",
    "Welcome aboard! Let me know if you have any questions.",
    "Good luck with the exam tomorrow!",
    "Did the lecture make sense? I'm a bit lost on the last part.",
    "Thanks again, talk soon.",
    "Catch up later when you're free?",
    "Just wanted to check in — hope all is well.",
]

# A small marker we attach to messages we create so --clear can remove them safely.
SEED_MARKER = "  ⟪dummy⟫"


class Command(BaseCommand):
    help = "Create dummy Chat messages between friends so the inbox has data."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Username of the user to seed for (defaults to all users with friends).")
        parser.add_argument("--clear", action="store_true", help="Delete dummy chats previously seeded by this command.")
        parser.add_argument("--per-friend", type=int, default=8, help="Messages per friend (default 8).")

    def handle(self, *args, **opts):
        if opts["clear"]:
            qs = Chat.objects.filter(message__endswith=SEED_MARKER)
            n = qs.count()
            qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {n} dummy chat messages."))
            return

        username = opts.get("user")
        per_friend = opts["per_friend"]

        if username:
            try:
                target_users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"No user with username '{username}'"))
                return
        else:
            # Anyone with at least one accepted friendship is fair game.
            from_ids = Friend.objects.filter(status="accepted").values_list("from_user_id", flat=True)
            to_ids = Friend.objects.filter(status="accepted").values_list("to_user_id", flat=True)
            target_users = list(User.objects.filter(Q(id__in=from_ids) | Q(id__in=to_ids)).distinct())

        if not target_users:
            self.stdout.write(self.style.WARNING(
                "No users with friends found. Make a friend in the Discover page first, then re-run."
            ))
            return

        total_created = 0
        for user in target_users:
            # Friendship can be stored in either direction — gather both.
            friend_ids = set(
                Friend.objects.filter(from_user=user, status="accepted").values_list("to_user_id", flat=True)
            ) | set(
                Friend.objects.filter(to_user=user, status="accepted").values_list("from_user_id", flat=True)
            )
            if not friend_ids:
                continue
            friends = list(User.objects.filter(id__in=friend_ids))
            now = timezone.now()
            for friend in friends:
                for i in range(per_friend):
                    # Alternate sender/receiver so threads feel like real conversations.
                    if i % 2 == 0:
                        sender, receiver = friend, user
                    else:
                        sender, receiver = user, friend
                    text = random.choice(DUMMY_LINES) + SEED_MARKER
                    minutes_ago = (per_friend - i) * random.randint(15, 90)
                    Chat.objects.create(
                        sender=sender,
                        receiver=receiver,
                        message=text,
                        is_read=(sender == user),  # outgoing = read; incoming = unread
                        created_at=now - timedelta(minutes=minutes_ago),
                    )
                    total_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {total_created} dummy chat messages across {len(target_users)} user(s)."
        ))
        self.stdout.write("Run 'python manage.py seed_dummy_chats --clear' later to remove them.")
