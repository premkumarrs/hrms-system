"""Health and readiness endpoints for monitoring."""

import logging

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger('hrms.health')


def _database_ok():
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """Liveness probe — application is running."""

    return Response({
        "status": "ok",
        "service": "hrms-api",
        "timestamp": timezone.now().isoformat(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_ready(request):
    """Readiness probe — database connectivity and critical settings."""

    db_ok = _database_ok()
    issues = []

    if not db_ok:
        issues.append("database_unreachable")

    if not settings.DEBUG and not settings.ALLOWED_HOSTS:
        issues.append("allowed_hosts_empty")

    status_label = "ok" if db_ok and not issues else "degraded"
    code = 200 if db_ok else 503

    return Response(
        {
            "status": status_label,
            "database": db_ok,
            "debug": settings.DEBUG,
            "issues": issues,
            "timestamp": timezone.now().isoformat(),
        },
        status=code,
    )
