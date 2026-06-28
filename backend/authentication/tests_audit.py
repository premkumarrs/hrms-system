from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from authentication.models import AuditLog, UserProfile
from authentication.groups import ensure_hrms_groups, sync_profile_groups
from hrms_test_utils import auth_header, make_user


class LoginAuditTests(APITestCase):

    def setUp(self):
        ensure_hrms_groups()
        self.user = User.objects.create_user(username='audit_user', password='testpass123')
        profile = UserProfile.objects.create(user=self.user, role=UserProfile.ROLE_HR)
        sync_profile_groups(profile)

    def test_successful_login_creates_audit(self):
        response = self.client.post(
            '/api/token/',
            {'username': 'audit_user', 'password': 'testpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(action='login_success', username='audit_user').exists()
        )

    def test_failed_login_creates_audit(self):
        response = self.client.post(
            '/api/token/',
            {'username': 'audit_user', 'password': 'wrong'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertTrue(
            AuditLog.objects.filter(action='login_failed', username='audit_user').exists()
        )


class EmployeeAuditTests(APITestCase):

    def setUp(self):
        self.hr_user = make_user('hr_audit', UserProfile.ROLE_HR)

    def test_employee_create_writes_audit(self):
        payload = {
            'first_name': 'New',
            'last_name': 'Hire',
            'employee_code': 'NH01',
            'email': 'nh01@example.com',
            'phone': '9000000001',
            'joining_date': '2024-01-01',
            'status': 'ACTIVE',
        }
        response = self.client.post(
            '/api/employees/',
            payload,
            format='json',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(AuditLog.objects.filter(action='employee_create').exists())
