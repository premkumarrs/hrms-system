from django.core.management.base import BaseCommand

from authentication.groups import sync_all_profiles


class Command(BaseCommand):
    help = "Synchronize Django auth Groups with UserProfile roles."

    def handle(self, *args, **options):
        count = sync_all_profiles()
        self.stdout.write(
            self.style.SUCCESS(f"Synchronized {count} user profile(s).")
        )
