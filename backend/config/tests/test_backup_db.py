"""Tests for the backup_db management command."""

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase


class BackupDbCommandTests(TestCase):

    @patch("config.management.commands.backup_db.subprocess.run")
    def test_backup_creates_sql_file(self, mock_run):
        output_dir = Path(settings.BASE_DIR) / "backups" / "test_run"
        output_dir.mkdir(parents=True, exist_ok=True)

        out = StringIO()
        call_command("backup_db", "--output-dir", str(output_dir), stdout=out)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "pg_dump")
        self.assertIn("hrms_db_", cmd[-1])
        self.assertIn("Database backup:", out.getvalue())

    @patch(
        "config.management.commands.backup_db.subprocess.run",
        side_effect=FileNotFoundError,
    )
    def test_missing_pg_dump_raises_command_error(self, _mock_run):
        with self.assertRaises(CommandError) as ctx:
            call_command("backup_db")
        self.assertIn("pg_dump not found", str(ctx.exception))


class BackupScriptPresenceTests(SimpleTestCase):

    def test_backup_and_restore_scripts_exist(self):
        root = Path(__file__).resolve().parents[3]
        scripts = root / "scripts"
        self.assertTrue((scripts / "backup_postgres.ps1").is_file())
        self.assertTrue((scripts / "backup_postgres.sh").is_file())
        self.assertTrue((scripts / "restore_postgres.ps1").is_file())
