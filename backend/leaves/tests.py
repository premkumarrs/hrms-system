from datetime import date

from django.test import TestCase
from rest_framework.test import APITestCase

from authentication.models import UserProfile
from hrms_test_utils import auth_header, make_employee, make_user
from leaves.models import Leave
from leaves import services


class LeaveBalanceUnitTests(TestCase):

    def setUp(self):
        self.employee = make_employee("LV01")

    def test_pending_reserves_balance(self):
        Leave.objects.create(
            employee=self.employee,
            leave_type="CL",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
            status="PENDING",
            reason="Trip",
        )
        ok, _ = services.validate_leave_balance(
            self.employee, "CL", date(2026, 6, 10), date(2026, 6, 20)
        )
        self.assertFalse(ok)

    def test_exclude_current_pending_on_update(self):
        leave = Leave.objects.create(
            employee=self.employee,
            leave_type="CL",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 3),
            status="PENDING",
            reason="Trip",
        )
        ok, _ = services.validate_leave_balance(
            self.employee,
            "CL",
            date(2026, 7, 1),
            date(2026, 7, 4),
            exclude_leave_id=leave.pk,
        )
        self.assertTrue(ok)


class LeaveAPIScopeTests(APITestCase):

    def setUp(self):
        self.emp_a = make_employee("LA01")
        self.emp_b = make_employee("LB01")
        self.emp_user = make_user(
            "leave_emp", UserProfile.ROLE_EMPLOYEE, employee=self.emp_a
        )
        Leave.objects.create(
            employee=self.emp_b,
            leave_type="CL",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 2),
            status="APPROVED",
            reason="Other",
        )

    def test_employee_cannot_list_other_leaves(self):
        Leave.objects.create(
            employee=self.emp_a,
            leave_type="CL",
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 11),
            status="APPROVED",
            reason="Own",
        )
        response = self.client.get("/api/leaves/", **auth_header(self.emp_user))
        self.assertEqual(response.status_code, 200)
        employee_ids = {row["employee"] for row in response.json()}
        self.assertIn(self.emp_a.id, employee_ids)
        self.assertNotIn(self.emp_b.id, employee_ids)
