from datetime import date

from rest_framework.test import APITestCase

from authentication.models import UserProfile
from hrms_test_utils import auth_header, make_employee, make_user
from lifecycle.models import Onboarding, Resignation


class LifecycleAPITests(APITestCase):

    def setUp(self):
        self.employee = make_employee('LC01')
        self.hr_user = make_user('hr_lc', UserProfile.ROLE_HR)

    def test_create_onboarding(self):
        response = self.client.post(
            '/api/onboardings/',
            {'employee': self.employee.id, 'status': 'PENDING'},
            format='json',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Onboarding.objects.count(), 1)

    def test_create_resignation(self):
        response = self.client.post(
            '/api/resignations/',
            {
                'employee': self.employee.id,
                'resignation_date': '2026-06-01',
                'notice_period_days': 30,
            },
            format='json',
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 201)
        resignation = Resignation.objects.get(employee=self.employee)
        self.assertEqual(resignation.notice_period_days, 30)
