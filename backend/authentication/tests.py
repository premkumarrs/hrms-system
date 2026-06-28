from django.test import TestCase
from django.contrib.auth.models import Group

from authentication.groups import GROUP_HR, GROUP_MANAGER, GROUP_EMPLOYEE, ensure_hrms_groups
from authentication.models import UserProfile
from authentication.permissions import get_role, user_in_group
from hrms_test_utils import make_employee, make_user


class GroupAuthorizationTests(TestCase):

    def setUp(self):
        self.emp = make_employee("E001")
        self.hr_user = make_user("hr1", UserProfile.ROLE_HR)
        self.mgr_emp = make_employee("M001")
        self.mgr_user = make_user("mgr1", UserProfile.ROLE_MANAGER, employee=self.mgr_emp)
        self.emp_user = make_user("emp1", UserProfile.ROLE_EMPLOYEE, employee=self.emp)

    def test_groups_created(self):
        ensure_hrms_groups()
        names = set(Group.objects.values_list("name", flat=True))
        self.assertIn(GROUP_HR, names)
        self.assertIn(GROUP_MANAGER, names)
        self.assertIn(GROUP_EMPLOYEE, names)

    def test_profile_sync_assigns_group(self):
        self.assertTrue(user_in_group(self.hr_user, GROUP_HR))
        self.assertTrue(user_in_group(self.mgr_user, GROUP_MANAGER))
        self.assertTrue(user_in_group(self.emp_user, GROUP_EMPLOYEE))

    def test_get_role_from_groups(self):
        self.assertEqual(get_role(self.hr_user), UserProfile.ROLE_HR)
        self.assertEqual(get_role(self.mgr_user), UserProfile.ROLE_MANAGER)
        self.assertEqual(get_role(self.emp_user), UserProfile.ROLE_EMPLOYEE)
