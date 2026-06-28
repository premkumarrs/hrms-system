"""Queryset scoping helpers for HR / Manager / Employee RBAC."""

from employees.models import Employee

from .groups import GROUP_EMPLOYEE, GROUP_HR, GROUP_MANAGER
from .permissions import get_linked_employee_id, user_in_group


def get_role(user):
    """Resolve role from Django groups (synced from UserProfile)."""

    if not user or not user.is_authenticated:
        return None

    if user.is_superuser or user_in_group(user, GROUP_HR):
        return GROUP_HR

    if user_in_group(user, GROUP_MANAGER):
        return GROUP_MANAGER

    if user_in_group(user, GROUP_EMPLOYEE):
        return GROUP_EMPLOYEE

    # Unsynced accounts: fall back to linked profile role string.
    from .permissions import get_profile

    profile = get_profile(user)
    if profile and profile.role:
        return profile.role

    return GROUP_EMPLOYEE


def get_team_employee_ids(user):
    """Return employee PKs visible to this user, or None for unrestricted (HR)."""

    role = get_role(user)

    if role == GROUP_HR:
        return None

    linked = get_linked_employee_id(user)

    if role == GROUP_EMPLOYEE:
        return [linked] if linked else []

    if role == GROUP_MANAGER:
        if not linked:
            return []
        team_ids = list(
            Employee.objects.filter(manager_id=linked).values_list('id', flat=True)
        )
        team_ids.append(linked)
        return team_ids

    return []


def filter_employees_for_user(queryset, user):
    """Restrict an Employee queryset to the caller's visibility scope."""

    team_ids = get_team_employee_ids(user)
    if team_ids is None:
        return queryset
    if not team_ids:
        return queryset.none()
    return queryset.filter(id__in=team_ids)


def filter_by_employee_scope(queryset, user, field_name='employee_id'):
    """Restrict a queryset with an employee FK to the caller's scope."""

    team_ids = get_team_employee_ids(user)
    if team_ids is None:
        return queryset
    if not team_ids:
        return queryset.none()
    return queryset.filter(**{f'{field_name}__in': team_ids})


def filter_projects_for_user(queryset, user):
    """HR: all projects; Manager/Employee: projects with team/self allocations."""

    team_ids = get_team_employee_ids(user)
    if team_ids is None:
        return queryset

    if not team_ids:
        return queryset.none()

    from projects.models import ProjectAllocation

    project_ids = (
        ProjectAllocation.objects
        .filter(employee_id__in=team_ids)
        .values_list('project_id', flat=True)
        .distinct()
    )
    return queryset.filter(id__in=project_ids)


def user_can_access_employee(user, employee_id):
    """Return True if the user may access the given employee record."""

    if employee_id is None:
        return False

    team_ids = get_team_employee_ids(user)
    if team_ids is None:
        return True
    return employee_id in team_ids
