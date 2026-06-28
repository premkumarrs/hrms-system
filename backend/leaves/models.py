from django.db import models
from employees.models import Employee


class Leave(models.Model):

    LEAVE_TYPES = [
        ('CL', 'Casual Leave'),
        ('SL', 'Sick Leave'),
        ('EL', 'Earned Leave'),
    ]

    LEAVE_STATUS = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )

    leave_type = models.CharField(
        max_length=10,
        choices=LEAVE_TYPES
    )

    start_date = models.DateField()

    end_date = models.DateField()

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=LEAVE_STATUS,
        default='PENDING'
    )

    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['leave_type']),
        ]

    @property
    def number_of_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    def __str__(self):
        return f"{self.employee} - {self.leave_type}"


class Permission(models.Model):
    """Short-duration time-off request within a single working day."""

    PERMISSION_STATUS = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='permission_requests'
    )

    date = models.DateField()

    from_time = models.TimeField()

    to_time = models.TimeField()

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=PERMISSION_STATUS,
        default='PENDING'
    )

    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_permissions'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.from_time}-{self.to_time})"