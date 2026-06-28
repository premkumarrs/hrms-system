from datetime import date, time

from rest_framework.test import APITestCase

from authentication.models import UserProfile
from hrms_test_utils import auth_header, make_employee, make_user


class DashboardReportTests(APITestCase):

    def setUp(self):
        self.hr_user = make_user('hr_reports', UserProfile.ROLE_HR)
        self.employee = make_employee('RP01')

    def test_dashboard_stats(self):
        response = self.client.get(
            '/api/dashboard/stats/',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_employees', response.json())

    def test_attendance_report(self):
        from attendance.models import Attendance

        Attendance.objects.create(
            employee=self.employee,
            date=date.today(),
            check_in=time(9, 0),
            status='PRESENT',
        )
        response = self.client.get(
            '/api/reports/attendance/',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['title'], 'Attendance Report')
        self.assertGreaterEqual(len(body['rows']), 1)

    def test_payroll_report(self):
        from payroll.models import SalaryRecord

        SalaryRecord.objects.create(
            employee=self.employee,
            period='2026-06',
            basic_salary=10000,
        )
        response = self.client.get(
            '/api/reports/payroll/?period=2026-06',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['title'].startswith('Payroll Summary'))

    def test_dashboard_insights(self):
        response = self.client.get(
            '/api/dashboard/insights/',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn('pending_leaves', body)
        self.assertIn('upcoming_birthdays', body)
        self.assertIn('recent_notifications', body)

    def test_openapi_schema(self):
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, 200)
