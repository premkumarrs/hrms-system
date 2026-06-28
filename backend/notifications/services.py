"""Notification creation helpers and event generators."""

from datetime import date

from .models import Notification


def notify(title, message, notification_type=Notification.TYPE_GENERAL,
           recipient=None, employee=None, event_date=None):
    """Create a single notification (best-effort)."""

    return Notification.objects.create(
        recipient=recipient,
        employee=employee,
        notification_type=notification_type,
        title=title,
        message=message,
        event_date=event_date,
    )


def _recipient_for_employee(employee):
    """Resolve a User linked to an employee via UserProfile, or None."""

    if employee is None:
        return None

    profile = employee.user_profiles.first()
    return profile.user if profile else None


def notify_leave_decision(leave, approved):
    """Notify the employee that their leave was approved / rejected."""

    employee = leave.employee
    recipient = _recipient_for_employee(employee)

    if approved:
        title = "Leave Approved"
        ntype = Notification.TYPE_LEAVE_APPROVED
    else:
        title = "Leave Rejected"
        ntype = Notification.TYPE_LEAVE_REJECTED

    message = (
        f"Your {leave.get_leave_type_display()} "
        f"({leave.start_date} to {leave.end_date}) was "
        f"{'approved' if approved else 'rejected'}."
    )

    notify(
        title=title,
        message=message,
        notification_type=ntype,
        recipient=recipient,
        employee=employee,
    )


def notify_permission_decision(permission, approved):
    """Notify the employee that their permission was approved / rejected."""

    employee = permission.employee
    recipient = _recipient_for_employee(employee)

    if approved:
        title = "Permission Approved"
        ntype = Notification.TYPE_PERMISSION_APPROVED
    else:
        title = "Permission Rejected"
        ntype = Notification.TYPE_PERMISSION_REJECTED

    message = (
        f"Your permission request on {permission.date} "
        f"({permission.from_time}–{permission.to_time}) was "
        f"{'approved' if approved else 'rejected'}."
    )

    notify(
        title=title,
        message=message,
        notification_type=ntype,
        recipient=recipient,
        employee=employee,
    )


def _manager_recipients():
    """Users in Manager or HR groups who should receive pending alerts."""

    from django.contrib.auth import get_user_model

    from authentication.groups import GROUP_HR, GROUP_MANAGER

    User = get_user_model()
    return User.objects.filter(
        groups__name__in=(GROUP_HR, GROUP_MANAGER)
    ).distinct()


def _pending_counts_for_manager(manager_user):
    """Pending leave/permission counts visible to a manager's team scope."""

    from authentication.rbac import get_team_employee_ids
    from leaves.models import Leave, Permission

    team_ids = get_team_employee_ids(manager_user)
    if team_ids is None:
        leaves = Leave.objects.filter(status='PENDING').count()
        permissions = Permission.objects.filter(status='PENDING').count()
        return leaves, permissions

    if not team_ids:
        return 0, 0

    leaves = Leave.objects.filter(
        status='PENDING', employee_id__in=team_ids
    ).count()
    permissions = Permission.objects.filter(
        status='PENDING', employee_id__in=team_ids
    ).count()
    return leaves, permissions


def generate_event_notifications():
    """Create today's birthday / anniversary / pending-approval alerts.

    Idempotent: uses get_or_create keyed on type + employee + event_date so
    repeated calls in the same day do not duplicate entries.
    """

    from employees.models import Employee

    today = date.today()
    created = 0

    # Birthdays
    birthdays = Employee.objects.filter(
        status='ACTIVE',
        date_of_birth__month=today.month,
        date_of_birth__day=today.day,
    ).prefetch_related('user_profiles__user')
    for emp in birthdays:
        _, made = Notification.objects.get_or_create(
            notification_type=Notification.TYPE_BIRTHDAY,
            employee=emp,
            event_date=today,
            defaults={
                "title": "Birthday Today",
                "message": f"{emp.first_name} {emp.last_name} has a birthday today.",
            },
        )
        created += int(made)

        birthday_user = _recipient_for_employee(emp)
        if birthday_user:
            _, made = Notification.objects.get_or_create(
                notification_type=Notification.TYPE_BIRTHDAY,
                recipient=birthday_user,
                event_date=today,
                defaults={
                    "title": "Happy Birthday!",
                    "message": "Wishing you a wonderful birthday from HRMS.",
                    "employee": emp,
                },
            )
            created += int(made)

    # Work anniversaries
    anniversaries = Employee.objects.filter(
        status='ACTIVE',
        joining_date__month=today.month,
        joining_date__day=today.day,
    ).exclude(joining_date=today).prefetch_related('user_profiles__user')
    for emp in anniversaries:
        years = today.year - emp.joining_date.year
        _, made = Notification.objects.get_or_create(
            notification_type=Notification.TYPE_ANNIVERSARY,
            employee=emp,
            event_date=today,
            defaults={
                "title": "Work Anniversary",
                "message": (
                    f"{emp.first_name} {emp.last_name} completes "
                    f"{years} year(s) today."
                ),
            },
        )
        created += int(made)

        anniversary_user = _recipient_for_employee(emp)
        if anniversary_user:
            _, made = Notification.objects.get_or_create(
                notification_type=Notification.TYPE_ANNIVERSARY,
                recipient=anniversary_user,
                event_date=today,
                defaults={
                    "title": "Work Anniversary",
                    "message": (
                        f"Congratulations on {years} year(s) with the organization."
                    ),
                    "employee": emp,
                },
            )
            created += int(made)

    # Pending approval alerts — one per manager/HR user with scoped counts.
    for user in _manager_recipients():
        pending_leaves, pending_permissions = _pending_counts_for_manager(user)
        total_pending = pending_leaves + pending_permissions
        if not total_pending:
            continue

        _, made = Notification.objects.get_or_create(
            notification_type=Notification.TYPE_PENDING,
            recipient=user,
            event_date=today,
            defaults={
                "title": "Pending Approvals",
                "message": (
                    f"{pending_leaves} leave and {pending_permissions} "
                    "permission request(s) in your scope await approval."
                ),
            },
        )
        created += int(made)

    return created
