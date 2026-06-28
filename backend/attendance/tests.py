from datetime import date, time

from rest_framework.test import APITestCase

from attendance.models import Attendance
from authentication.models import UserProfile
from hrms_test_utils import auth_header, make_employee, make_user


class AttendanceScopeTests(APITestCase):

    def setUp(self):
        self.emp_a = make_employee("AA01")
        self.emp_b = make_employee("AB01")
        Attendance.objects.create(
            employee=self.emp_a,
            date=date.today(),
            check_in=time(9, 0),
            status="PRESENT",
        )
        Attendance.objects.create(
            employee=self.emp_b,
            date=date.today(),
            check_in=time(9, 0),
            status="PRESENT",
        )
        self.emp_user = make_user("att_emp", UserProfile.ROLE_EMPLOYEE, employee=self.emp_a)

    def test_list_scoped_to_self(self):
        response = self.client.get("/api/attendance/", **auth_header(self.emp_user))
        self.assertEqual(response.status_code, 200)
        employee_ids = {row["employee"] for row in response.json()}
        self.assertEqual(employee_ids, {self.emp_a.id})

    def test_summary_scoped_to_self(self):
        response = self.client.get(
            "/api/attendance/summary/",
            **auth_header(self.emp_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["present"], 1)

    def test_report_scoped_to_self(self):
        response = self.client.get(
            "/api/attendance/report/",
            **auth_header(self.emp_user),
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["employee"], self.emp_a.id)

    def test_duplicate_attendance_same_day_allowed_by_api(self):
        """Document current behavior: duplicate day records are not blocked at API."""
        Attendance.objects.create(
            employee=self.emp_a,
            date=date.today(),
            check_in=time(10, 0),
            status="HALF_DAY",
        )
        response = self.client.get("/api/attendance/", **auth_header(self.emp_user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
