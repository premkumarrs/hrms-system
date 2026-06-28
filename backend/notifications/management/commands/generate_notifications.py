from django.core.management.base import BaseCommand

from notifications.scheduler import run_scheduled_notifications


class Command(BaseCommand):
    help = (
        "Generate today's birthday, work anniversary, and pending-approval "
        "notifications (idempotent)."
    )

    def handle(self, *args, **options):
        created = run_scheduled_notifications()
        self.stdout.write(
            self.style.SUCCESS(f"Created {created} notification(s).")
        )
