from django.conf import settings
from django.db import models


class Notification(models.Model):
    """An in-app notification.

    ``recipient`` null means a broadcast notification visible to everyone
    (used for birthdays, anniversaries and pending-approval alerts).
    """

    TYPE_LEAVE_APPROVED = 'LEAVE_APPROVED'
    TYPE_LEAVE_REJECTED = 'LEAVE_REJECTED'
    TYPE_PERMISSION_APPROVED = 'PERMISSION_APPROVED'
    TYPE_PERMISSION_REJECTED = 'PERMISSION_REJECTED'
    TYPE_BIRTHDAY = 'BIRTHDAY'
    TYPE_ANNIVERSARY = 'ANNIVERSARY'
    TYPE_PENDING = 'PENDING_APPROVAL'
    TYPE_GENERAL = 'GENERAL'

    TYPE_CHOICES = [
        (TYPE_LEAVE_APPROVED, 'Leave Approved'),
        (TYPE_LEAVE_REJECTED, 'Leave Rejected'),
        (TYPE_PERMISSION_APPROVED, 'Permission Approved'),
        (TYPE_PERMISSION_REJECTED, 'Permission Rejected'),
        (TYPE_BIRTHDAY, 'Birthday'),
        (TYPE_ANNIVERSARY, 'Work Anniversary'),
        (TYPE_PENDING, 'Pending Approval'),
        (TYPE_GENERAL, 'General'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default=TYPE_GENERAL
    )

    title = models.CharField(max_length=200)

    message = models.TextField(blank=True)

    # Used to de-duplicate recurring event notifications (birthday/anniversary).
    event_date = models.DateField(null=True, blank=True)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} - {self.title}"
