from rest_framework.test import APITestCase

from authentication.models import UserProfile
from employees.models import BankDetails
from hrms_test_utils import auth_header, make_employee, make_user


class EmployeeChildRecordScopeTests(APITestCase):

    def setUp(self):
        self.emp_a = make_employee("EA01")
        self.emp_b = make_employee("EB01")
        BankDetails.objects.create(
            employee=self.emp_a,
            bank_name="Bank A",
            account_number="111",
            ifsc_code="IFSC0001",
        )
        BankDetails.objects.create(
            employee=self.emp_b,
            bank_name="Bank B",
            account_number="222",
            ifsc_code="IFSC0002",
        )
        self.emp_user = make_user("empa", UserProfile.ROLE_EMPLOYEE, employee=self.emp_a)

    def test_employee_cannot_list_other_bank_details(self):
        response = self.client.get(
            "/api/bank-details/",
            **auth_header(self.emp_user),
        )
        self.assertEqual(response.status_code, 200)
        ids = {row["employee"] for row in response.json()}
        self.assertEqual(ids, {self.emp_a.id})

    def test_employee_sees_only_own_bank_with_filter(self):
        response = self.client.get(
            f"/api/bank-details/?employee={self.emp_a.id}",
            **auth_header(self.emp_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_employee_cannot_access_other_employee_record(self):
        response = self.client.get(
            f"/api/employees/{self.emp_b.id}/",
            **auth_header(self.emp_user),
        )
        self.assertEqual(response.status_code, 404)
