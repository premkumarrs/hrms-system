"""Audit UserProfile roles against Django auth group membership."""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from authentication.groups import GROUP_EMPLOYEE, GROUP_HR, GROUP_MANAGER
from authentication.models import UserProfile


ROLE_GROUP = {
    UserProfile.ROLE_HR: GROUP_HR,
    UserProfile.ROLE_MANAGER: GROUP_MANAGER,
    UserProfile.ROLE_EMPLOYEE: GROUP_EMPLOYEE,
}


class Command(BaseCommand):
    help = "Report UserProfile ↔ Django group mismatches and orphaned profiles."

    def handle(self, *args, **options):
        issues = 0

        for profile in UserProfile.objects.select_related('user', 'employee'):
            user = profile.user
            expected = ROLE_GROUP.get(profile.role)
            if not expected:
                issues += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Profile {profile.pk}: unknown role {profile.role!r} "
                        f"for user {user.username}"
                    )
                )
                continue

            if not user.groups.filter(name=expected).exists():
                issues += 1
                groups = list(user.groups.values_list('name', flat=True))
                self.stdout.write(
                    self.style.ERROR(
                        f"MISMATCH user={user.username} role={profile.role} "
                        f"expected_group={expected} actual_groups={groups}"
                    )
                )

            if profile.role == UserProfile.ROLE_EMPLOYEE and profile.employee is None:
                issues += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Employee role without linked employee: {user.username}"
                    )
                )

        users_with_groups = set(
            Group.objects.filter(
                name__in=(GROUP_HR, GROUP_MANAGER, GROUP_EMPLOYEE)
            ).values_list('user', flat=True)
        )
        profile_users = set(UserProfile.objects.values_list('user_id', flat=True))
        for user_id in users_with_groups - profile_users:
            issues += 1
            self.stdout.write(
                self.style.WARNING(
                    f"User id={user_id} has HRMS group but no UserProfile"
                )
            )

        if issues == 0:
            self.stdout.write(self.style.SUCCESS("Permission audit passed — no issues."))
        else:
            self.stdout.write(
                self.style.WARNING(f"Permission audit found {issues} issue(s).")
            )
            self.stdout.write("Run: python manage.py sync_hrms_groups")
