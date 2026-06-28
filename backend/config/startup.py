"""Startup validation for production deployments."""

import logging
import sys

from django.conf import settings
from django.db import connection

logger = logging.getLogger('hrms.startup')


def run_startup_checks():
    """Log configuration issues at process start (non-fatal in development)."""

    argv = sys.argv
    skip_db = any(
        cmd in argv
        for cmd in (
            'makemigrations', 'migrate', 'test', 'shell',
            'collectstatic', 'check',
        )
    )

    issues = []

    if settings.SECRET_KEY.startswith('django-insecure') and not settings.DEBUG:
        issues.append('SECRET_KEY is still using the development default.')

    if not settings.DEBUG and not settings.ALLOWED_HOSTS:
        issues.append('ALLOWED_HOSTS is empty in production.')

    if not skip_db:
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception as exc:
            issues.append(f'Database unreachable at startup: {exc}')

    media_root = settings.MEDIA_ROOT
    if media_root and not media_root.exists():
        try:
            media_root.mkdir(parents=True, exist_ok=True)
            logger.info('Created media directory at %s', media_root)
        except OSError as exc:
            issues.append(f'Cannot create MEDIA_ROOT ({media_root}): {exc}')

    for issue in issues:
        if settings.DEBUG:
            logger.warning('Startup check: %s', issue)
        else:
            logger.error('Startup check: %s', issue)

    if issues and not settings.DEBUG:
        for issue in issues:
            print(f'HRMS startup error: {issue}', file=sys.stderr)
