"""Audit trail for security-sensitive HRMS actions."""

import json
import logging

from .models import AuditLog

logger = logging.getLogger('hrms.audit')


def get_client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def snapshot_model(instance, fields=None):
    """Serialize selected model fields for before/after audit diffs."""

    if instance is None:
        return None

    data = {}
    for field in instance._meta.fields:
        if fields and field.name not in fields:
            continue
        value = getattr(instance, field.name)
        if hasattr(value, 'isoformat'):
            value = value.isoformat()
        elif hasattr(value, 'pk'):
            value = value.pk
        data[field.name] = value
    return data


def log_audit(
    request,
    action,
    target=None,
    *,
    target_model=None,
    target_id=None,
    target_repr=None,
    changes=None,
    user=None,
    username=None,
):
    """Persist an audit log entry (best-effort; never blocks business logic)."""

    try:
        actor = user
        if actor is None and request is not None and getattr(request, 'user', None):
            if request.user.is_authenticated:
                actor = request.user

        if target is not None:
            target_model = target_model or f'{target._meta.app_label}.{target._meta.model_name}'
            target_id = str(target.pk)
            target_repr = target_repr or str(target)

        changes_json = None
        if changes is not None:
            changes_json = json.loads(json.dumps(changes, default=str))

        AuditLog.objects.create(
            user=actor,
            username=username or (actor.username if actor else ''),
            action=action,
            target_model=target_model or '',
            target_id=target_id or '',
            target_repr=target_repr or '',
            changes=changes_json,
            ip_address=get_client_ip(request),
        )
        logger.info(
            "audit action=%s user=%s target=%s:%s",
            action,
            username or (actor.username if actor else '-'),
            target_model,
            target_id,
        )
    except Exception:
        logger.exception("Failed to write audit log for action %s", action)
