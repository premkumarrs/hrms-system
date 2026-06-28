"""Backup PostgreSQL database (and optionally media) for HRMS."""

import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a PostgreSQL dump using pg_dump (requires pg_dump on PATH)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=str(settings.BASE_DIR / "backups"),
            help="Directory for backup files",
        )
        parser.add_argument(
            "--include-media",
            action="store_true",
            help="Also copy the media folder into the backup directory",
        )

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sql_path = output_dir / f"hrms_db_{stamp}.sql"

        env = os.environ.copy()
        if db.get("PASSWORD"):
            env["PGPASSWORD"] = db["PASSWORD"]

        cmd = [
            "pg_dump",
            "-h", db.get("HOST", "localhost"),
            "-p", str(db.get("PORT", "5432")),
            "-U", db.get("USER", "postgres"),
            "-d", db.get("NAME", "hrms_db"),
            "-F", "p",
            "-f", str(sql_path),
        ]

        try:
            subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise CommandError(
                "pg_dump not found. Install PostgreSQL client tools or use "
                "scripts/backup_postgres.ps1 / scripts/backup_postgres.sh"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise CommandError(f"pg_dump failed: {exc.stderr or exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Database backup: {sql_path}"))

        if options["include_media"]:
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists():
                import shutil

                dest = output_dir / f"media_{stamp}"
                shutil.copytree(media_root, dest)
                self.stdout.write(self.style.SUCCESS(f"Media backup: {dest}"))
