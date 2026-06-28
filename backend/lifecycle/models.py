from datetime import timedelta

from django.db import models
from employees.models import Employee


class Onboarding(models.Model):
    """Tracks an employee's onboarding progress."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='onboarding'
    )

    joining_date = models.DateField(null=True, blank=True)

    department_assigned = models.BooleanField(default=False)

    designation_assigned = models.BooleanField(default=False)

    documents_submitted = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Onboarding - {self.employee}"


class Resignation(models.Model):
    """Tracks resignation, notice period and exit settlement."""

    EXIT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]

    SETTLEMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSED', 'Processed'),
        ('PAID', 'Paid'),
    ]

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='resignation'
    )

    resignation_date = models.DateField()

    notice_period_days = models.IntegerField(default=30)

    last_working_day = models.DateField(null=True, blank=True)

    reason = models.TextField(blank=True)

    exit_status = models.CharField(
        max_length=20,
        choices=EXIT_STATUS_CHOICES,
        default='PENDING'
    )

    final_settlement_status = models.CharField(
        max_length=20,
        choices=SETTLEMENT_STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def expected_last_working_day(self):
        if self.resignation_date:
            return self.resignation_date + timedelta(
                days=self.notice_period_days
            )
        return None

    def __str__(self):
        return f"Resignation - {self.employee}"
