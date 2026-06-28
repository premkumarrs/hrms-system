from django.db import models

from employees.models import Employee


class SalaryRecord(models.Model):
    """A monthly salary record for an employee (payroll placeholder)."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='salary_records'
    )

    # Pay period in YYYY-MM form (e.g. 2026-06).
    period = models.CharField(max_length=7)

    basic_salary = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    allowances = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    deductions = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'period')
        ordering = ['-period']
        indexes = [
            models.Index(fields=['period']),
            models.Index(fields=['employee', '-period']),
        ]

    @property
    def net_salary(self):
        return (self.basic_salary or 0) + (self.allowances or 0) - (self.deductions or 0)

    def __str__(self):
        return f"{self.employee} - {self.period}"
