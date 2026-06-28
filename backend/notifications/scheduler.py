"""Reusable notification scheduler service for HRMS.

This module is the single entry point for time-based notification generation.
It is intentionally decoupled from HTTP views so notifications are not
triggered by dashboard page loads.

Scheduling options
------------------
Run manually::

    python manage.py generate_notifications

Run on a schedule with the OS scheduler:

* **Linux/macOS (cron)** — daily at 08:00::

      0 8 * * * cd /path/to/hrms-system/backend && venv/bin/python manage.py generate_notifications

* **Windows Task Scheduler** — create a daily task that runs::

      backend\\venv\\Scripts\\python.exe manage.py generate_notifications

See ``docs/SCHEDULER.md`` for full setup instructions.
"""

from .services import generate_event_notifications


def run_scheduled_notifications():
    """Generate today's birthday, anniversary, and pending-approval alerts.

    Idempotent: safe to call multiple times per day (see ``services``).
    Returns the number of new notification rows created.
    """

    return generate_event_notifications()
