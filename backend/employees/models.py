from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Designation(models.Model):
    title = models.CharField(max_length=100)

    def __str__(self):
        return self.title


class Employee(models.Model):

    EMPLOYMENT_STATUS = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('RESIGNED', 'Resigned'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    employee_code = models.CharField(
        max_length=20,
        unique=True
    )

    email = models.EmailField(unique=True)

    phone = models.CharField(max_length=15)

    branch = models.CharField(
        max_length=100,
        blank=True
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    joining_date = models.DateField()

    address = models.TextField(
        blank=True
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True
    )

    designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True
    )

    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS,
        default='ACTIVE'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['department']),
            models.Index(fields=['branch']),
        ]

    def __str__(self):
        return f"{self.employee_code} - {self.first_name} {self.last_name}"
    
class Education(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='education'
    )

    degree = models.CharField(max_length=100)

    institution = models.CharField(max_length=200)

    university = models.CharField(max_length=200, blank=True)

    year_of_passing = models.IntegerField()

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.employee} - {self.degree}"


class BankDetails(models.Model):

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='bank_details'
    )

    bank_name = models.CharField(max_length=100)

    branch = models.CharField(max_length=100, blank=True)

    account_number = models.CharField(max_length=50)

    ifsc_code = models.CharField(max_length=20)

    pan_number = models.CharField(max_length=20, blank=True)

    aadhaar_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.employee.first_name


class IDProof(models.Model):
    """Government ID proofs for an employee."""

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='id_proof'
    )

    aadhaar_number = models.CharField(max_length=20, blank=True)

    pan_number = models.CharField(max_length=20, blank=True)

    passport_number = models.CharField(max_length=30, blank=True)

    driving_license = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"ID Proof - {self.employee}"


class EmergencyContact(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )

    contact_name = models.CharField(max_length=100)

    relationship = models.CharField(max_length=50)

    phone = models.CharField(max_length=15)

    address = models.TextField(blank=True)

    def __str__(self):
        return self.contact_name