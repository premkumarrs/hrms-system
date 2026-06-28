from datetime import date

from rest_framework.test import APITestCase

from authentication.models import AuditLog, UserProfile
from hrms_test_utils import auth_header, make_employee, make_user
from leaves.models import Leave
from payroll.models import SalaryRecord


class PayrollAPITests(APITestCase):

    def setUp(self):
        self.employee = make_employee('PY01')
        self.hr_user = make_user('hr_pay', UserProfile.ROLE_HR)
        self.emp_user = make_user(
            'emp_pay', UserProfile.ROLE_EMPLOYEE, employee=self.employee
        )

    def test_hr_can_create_salary_record(self):
        response = self.client.post(
            '/api/salaries/',
            {
                'employee': self.employee.id,
                'period': '2026-06',
                'basic_salary': '50000.00',
                'allowances': '5000.00',
                'deductions': '2000.00',
            },
            format='json',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SalaryRecord.objects.count(), 1)
        self.assertTrue(AuditLog.objects.filter(action='payroll_create').exists())

    def test_employee_cannot_create_payroll(self):
        response = self.client.post(
            '/api/salaries/',
            {
                'employee': self.employee.id,
                'period': '2026-06',
                'basic_salary': '50000.00',
            },
            format='json',
            **auth_header(self.emp_user),
        )
        self.assertEqual(response.status_code, 403)

    def test_payslip_download(self):
        record = SalaryRecord.objects.create(
            employee=self.employee,
            period='2026-06',
            basic_salary=50000,
            allowances=5000,
            deductions=2000,
        )
        response = self.client.get(
            f'/api/salaries/{record.id}/payslip/',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_duplicate_period_rejected(self):
        SalaryRecord.objects.create(
            employee=self.employee,
            period='2026-06',
            basic_salary=50000,
        )
        response = self.client.post(
            '/api/salaries/',
            {
                'employee': self.employee.id,
                'period': '2026-06',
                'basic_salary': '40000.00',
            },
            format='json',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 400)


class LeaveApprovalAuditTests(APITestCase):

    def setUp(self):
        self.mgr_emp = make_employee('LM01')
        self.team_emp = make_employee('LT01', manager=self.mgr_emp)
        self.mgr_user = make_user(
            'leave_mgr', UserProfile.ROLE_MANAGER, employee=self.mgr_emp
        )
        self.leave = Leave.objects.create(
            employee=self.team_emp,
            leave_type='CL',
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 2),
            reason='Personal',
            status='PENDING',
        )

    def test_approve_writes_audit(self):
        response = self.client.post(
            f'/api/leaves/{self.leave.id}/approve/',
            {},
            format='json',
            **auth_header(self.mgr_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action='leave_approved').exists())
