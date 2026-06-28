"""Role resolution and DRF permission classes for HRMS RBAC.

Authorization is enforced through Django auth Groups (HR, Manager, Employee)
kept in sync with ``UserProfile.role`` via signals. DRF permission classes
check group membership; queryset scoping is applied in viewsets via ``rbac``.
"""

from django.core.exceptions import ObjectDoesNotExist

from rest_framework.permissions import BasePermission, SAFE_METHODS

from .groups import GROUP_EMPLOYEE, GROUP_HR, GROUP_MANAGER
from .models import UserProfile


ROLE_HR = UserProfile.ROLE_HR
ROLE_MANAGER = UserProfile.ROLE_MANAGER
ROLE_EMPLOYEE = UserProfile.ROLE_EMPLOYEE


def get_profile(user):
    try:
        return user.profile
    except (AttributeError, ObjectDoesNotExist):
        return None


def user_in_group(user, group_name):
    """Return True when the user belongs to the named Django auth group."""

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return group_name == GROUP_HR

    return user.groups.filter(name=group_name).exists()


def get_role(user):
    """Resolve HRMS role from Django groups (primary) or UserProfile (fallback)."""

    if not user or not user.is_authenticated:
        return None

    if user.is_superuser or user_in_group(user, GROUP_HR):
        return ROLE_HR

    if user_in_group(user, GROUP_MANAGER):
        return ROLE_MANAGER

    if user_in_group(user, GROUP_EMPLOYEE):
        return ROLE_EMPLOYEE

    profile = get_profile(user)
    if profile and profile.role:
        return profile.role

    return ROLE_EMPLOYEE


def get_permissions(role):
    """Build the permission flag map exposed to the frontend."""

    is_hr = role == ROLE_HR
    is_manager = role == ROLE_MANAGER

    return {
        "full_access": is_hr,
        "manage_employees": is_hr,
        "manage_departments": is_hr,
        "manage_designations": is_hr,
        "manage_attendance": is_hr or is_manager,
        "approve_leave": is_hr or is_manager,
        "manage_projects": is_hr,
        "view_projects": is_hr or is_manager,
        "manage_documents": is_hr,
        "manage_lifecycle": is_hr,
        "view_payroll": is_hr or is_manager,
        "view_reports": is_hr or is_manager,
        "view_directory": True,
        "view_team": is_hr or is_manager,
    }


class IsHROrReadOnly(BasePermission):
    """Read for any authenticated user; writes restricted to the HR group."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return user_in_group(request.user, GROUP_HR)


class IsManagerOrHR(BasePermission):
    """Allows only Manager or HR group members (used for approvals)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return (
            user_in_group(request.user, GROUP_HR)
            or user_in_group(request.user, GROUP_MANAGER)
        )


class IsHROrManagerOrReadOnly(BasePermission):
    """Read for any authenticated user; writes restricted to HR and Manager groups."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return (
            user_in_group(request.user, GROUP_HR)
            or user_in_group(request.user, GROUP_MANAGER)
        )


def get_linked_employee_id(user):
    """Return the employee PK linked to this user, or None."""

    profile = get_profile(user)
    if profile and profile.employee_id:
        return profile.employee_id
    return None
