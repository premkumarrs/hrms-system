"""Synchronize Django auth Groups with UserProfile roles."""

from django.contrib.auth.models import Group

from .models import UserProfile

GROUP_HR = 'HR'
GROUP_MANAGER = 'Manager'
GROUP_EMPLOYEE = 'Employee'

ROLE_TO_GROUP = {
    UserProfile.ROLE_HR: GROUP_HR,
    UserProfile.ROLE_MANAGER: GROUP_MANAGER,
    UserProfile.ROLE_EMPLOYEE: GROUP_EMPLOYEE,
}

ALL_GROUPS = (GROUP_HR, GROUP_MANAGER, GROUP_EMPLOYEE)


def ensure_hrms_groups():
    """Create HRMS role groups if they do not exist."""

    for name in ALL_GROUPS:
        Group.objects.get_or_create(name=name)


def sync_profile_groups(profile):
    """Assign exactly one Django group matching the profile role."""

    ensure_hrms_groups()

    group_name = ROLE_TO_GROUP.get(profile.role, GROUP_EMPLOYEE)
    target = Group.objects.get(name=group_name)

    user = profile.user
    user.groups.set([target])


def sync_all_profiles():
    """Sync groups for every UserProfile (management command helper)."""

    ensure_hrms_groups()
    count = 0
    for profile in UserProfile.objects.select_related('user').all():
        sync_profile_groups(profile)
        count += 1
    return count
