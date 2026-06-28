from django.db import models
from employees.models import Employee


class Project(models.Model):

    PROJECT_STATUS = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
    ]

    name = models.CharField(max_length=200)

    client = models.CharField(max_length=200)

    start_date = models.DateField()

    end_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=PROJECT_STATUS,
        default='ACTIVE'
    )

    description = models.TextField(
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.name


class ProjectAllocation(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE
    )

    allocated_on = models.DateField()

    released_on = models.DateField(
        null=True,
        blank=True
    )

    role = models.CharField(max_length=100)

    responsibilities = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'released_on']),
            models.Index(fields=['project', 'released_on']),
        ]

    def __str__(self):
        return f"{self.employee} -> {self.project}"