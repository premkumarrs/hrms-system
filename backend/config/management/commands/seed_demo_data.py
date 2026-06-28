"""Seed demo departments, employees, and sample HR records for demos."""

from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from authentication.groups import ensure_hrms_groups, sync_profile_groups
from authentication.models import UserProfile
from employees.models import Department, Designation, Employee


class Command(BaseCommand):
    help = "Create demo departments, employees, and HR/Manager/Employee login users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="demo1234",
            help="Password for demo users (default: demo1234)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        ensure_hrms_groups()

        dept, _ = Department.objects.get_or_create(name="Engineering")
        hr_dept, _ = Department.objects.get_or_create(name="Human Resources")
        Designation.objects.get_or_create(title="Software Engineer")
        mgr_title, _ = Designation.objects.get_or_create(title="Team Lead")
        hr_title, _ = Designation.objects.get_or_create(title="HR Executive")

        today = date.today()
        manager = self._ensure_employee(
            "MGR01", "Demo", "Manager", dept, mgr_title,
            joining_date=date(2020, 3, 15),
            date_of_birth=date(1988, 6, 10),
        )
        employee = self._ensure_employee(
            "EMP01", "Demo", "Employee", dept,
            Designation.objects.get(title="Software Engineer"),
            manager=manager,
            joining_date=date(2022, 1, 10),
            date_of_birth=date(1995, today.month, min(today.day + 3, 28)),
        )
        hr_emp = self._ensure_employee(
            "HR01", "Demo", "HR", hr_dept, hr_title,
            joining_date=date(2019, 8, 1),
            date_of_birth=date(1990, 2, 20),
        )

        self._ensure_user("hr_demo", UserProfile.ROLE_HR, hr_emp, password)
        self._ensure_user("mgr_demo", UserProfile.ROLE_MANAGER, manager, password)
        self._ensure_user("emp_demo", UserProfile.ROLE_EMPLOYEE, employee, password)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("  hr_demo / mgr_demo / emp_demo")
        self.stdout.write(f"  password: {password}")

    def _ensure_employee(self, code, first, last, department, designation, **extra):
        employee, created = Employee.objects.get_or_create(
            employee_code=code,
            defaults={
                "first_name": first,
                "last_name": last,
                "email": f"{code.lower()}@demo.hrms",
                "phone": "9000000001",
                "department": department,
                "designation": designation,
                "joining_date": extra.pop("joining_date", date.today()),
                "status": "ACTIVE",
                **extra,
            },
        )
        action = "Created" if created else "Using existing"
        self.stdout.write(f"  {action} employee {code}")
        return employee

    def _ensure_user(self, username, role, employee, password):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@demo.hrms"},
        )
        if created:
            user.set_password(password)
            user.save()
        profile, _ = UserProfile.objects.update_or_create(
            user=user,
            defaults={"role": role, "employee": employee},
        )
        sync_profile_groups(profile)
        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action} user {username} ({role})")
