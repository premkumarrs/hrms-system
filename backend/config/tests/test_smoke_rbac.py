"""API smoke tests for HR, Manager, and Employee role workflows."""

from datetime import date

from rest_framework.test import APITestCase

from authentication.models import UserProfile
from hrms_test_utils import auth_header, make_employee, make_user


class RoleSmokeTests(APITestCase):
    """Verify core endpoints respond for each primary role."""

    @classmethod
    def setUpTestData(cls):
        cls.hr = make_user("smoke_hr", UserProfile.ROLE_HR)
        mgr_emp = make_employee("SMGR")
        cls.manager = make_user(
            "smoke_mgr", UserProfile.ROLE_MANAGER, employee=mgr_emp
        )
        emp = make_employee("SEMP", manager=mgr_emp)
        cls.emp_id = emp.id
        cls.employee = make_user(
            "smoke_emp", UserProfile.ROLE_EMPLOYEE, employee=emp
        )

    def _get_ok(self, user, path):
        response = self.client.get(path, **auth_header(user))
        self.assertIn(response.status_code, (200, 201), f"{path} -> {response.status_code}")

    def test_hr_core_endpoints(self):
        for path in (
            "/api/me/",
            "/api/dashboard/stats/",
            "/api/dashboard/insights/",
            "/api/employees/",
            "/api/attendance/",
            "/api/leaves/",
            "/api/salaries/",
            "/api/documents/",
            "/api/reports/attendance/",
        ):
            self._get_ok(self.hr, path)

    def test_manager_team_endpoints(self):
        for path in (
            "/api/me/",
            "/api/dashboard/stats/",
            "/api/attendance/",
            "/api/leaves/",
            "/api/projects/",
            "/api/allocations/",
        ):
            self._get_ok(self.manager, path)

    def test_employee_self_service_endpoints(self):
        for path in (
            "/api/me/",
            "/api/me/profile/",
            "/api/attendance/",
            "/api/leaves/",
            "/api/notifications/",
            "/api/notifications/unread-count/",
            "/api/salaries/",
            "/api/documents/",
        ):
            self._get_ok(self.employee, path)

    def test_login_issues_token(self):
        response = self.client.post(
            "/api/token/",
            {"username": "smoke_hr", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_hr_employee_crud_flow(self):
        create = self.client.post(
            "/api/employees/",
            {
                "first_name": "Smoke",
                "last_name": "Test",
                "employee_code": "SMK01",
                "email": "smk01@example.com",
                "phone": "9000000099",
                "joining_date": "2024-01-01",
                "status": "ACTIVE",
            },
            format="json",
            **auth_header(self.hr),
        )
        self.assertEqual(create.status_code, 201)
        emp_id = create.json()["id"]

        read = self.client.get(f"/api/employees/{emp_id}/", **auth_header(self.hr))
        self.assertEqual(read.status_code, 200)

        update = self.client.patch(
            f"/api/employees/{emp_id}/",
            {"phone": "9000000100"},
            format="json",
            **auth_header(self.hr),
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["phone"], "9000000100")

        delete = self.client.delete(
            f"/api/employees/{emp_id}/",
            **auth_header(self.hr),
        )
        self.assertEqual(delete.status_code, 204)

    def test_hr_leave_approval_flow(self):
        emp = make_employee("SMKLV")
        leave = self.client.post(
            "/api/leaves/",
            {
                "employee": emp.id,
                "leave_type": "CL",
                "start_date": "2026-07-01",
                "end_date": "2026-07-02",
                "reason": "Smoke test leave",
            },
            format="json",
            **auth_header(self.hr),
        )
        self.assertEqual(leave.status_code, 201)
        leave_id = leave.json()["id"]

        approve = self.client.post(
            f"/api/leaves/{leave_id}/approve/",
            format="json",
            **auth_header(self.hr),
        )
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.json()["status"], "APPROVED")

    def test_employee_leave_request_flow(self):
        response = self.client.post(
            "/api/leaves/",
            {
                "employee": self.emp_id,
                "leave_type": "CL",
                "start_date": "2026-08-01",
                "end_date": "2026-08-01",
                "reason": "Personal",
            },
            format="json",
            **auth_header(self.employee),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "PENDING")
