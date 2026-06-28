"""Shared test helpers for HRMS API tests."""

from datetime import date

from django.contrib.auth.models import User

from authentication.groups import ensure_hrms_groups, sync_profile_groups
from authentication.models import UserProfile
from employees.models import Department, Employee


def make_employee(code, manager=None, **kwargs):
    defaults = {
        "first_name": "Test",
        "last_name": code,
        "employee_code": code,
        "email": f"{code.lower()}@example.com",
        "phone": "9999999999",
        "joining_date": date(2024, 1, 1),
        "status": "ACTIVE",
    }
    defaults.update(kwargs)
    if manager:
        defaults["manager"] = manager
    return Employee.objects.create(**defaults)


def make_user(username, role, employee=None, password="testpass123"):
    ensure_hrms_groups()
    user = User.objects.create_user(username=username, password=password)
    profile = UserProfile.objects.create(
        user=user,
        role=role,
        employee=employee,
    )
    sync_profile_groups(profile)
    return user


def auth_header(user):
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}
