from django.db import models
from employees.models import Employee


class DocumentCategory(models.Model):

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Document categories"

    def __str__(self):
        return self.name


class EmployeeDocument(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    title = models.CharField(max_length=200)

    file = models.FileField(upload_to='employee_documents/')

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['employee', '-uploaded_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.employee} - {self.title}"
