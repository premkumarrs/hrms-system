from django.test import TestCase
from rest_framework.test import APITestCase

from authentication.models import UserProfile
from documents.letter_service import (
    LETTER_APPOINTMENT,
    LETTER_OFFER,
    LETTER_EXPERIENCE,
    generate_letter_document,
)
from documents.models import DocumentCategory, EmployeeDocument
from hrms_test_utils import auth_header, make_employee, make_user


class LetterServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        for name in ("Offer Letters", "Appointment Letters", "HR Documents"):
            DocumentCategory.objects.get_or_create(name=name)

    def setUp(self):
        self.employee = make_employee("DOC01")

    def test_offer_letter_creates_document(self):
        document = generate_letter_document(self.employee, LETTER_OFFER)
        self.assertEqual(document.employee_id, self.employee.id)
        self.assertEqual(document.category.name, "Offer Letters")
        self.assertTrue(document.file.name.endswith(".pdf"))
        self.assertTrue(document.title.startswith("Offer Letter"))

    def test_appointment_letter_creates_document(self):
        document = generate_letter_document(self.employee, LETTER_APPOINTMENT)
        self.assertEqual(document.category.name, "Appointment Letters")

    def test_experience_letter_pdf_bytes(self):
        document = generate_letter_document(self.employee, LETTER_EXPERIENCE)
        document.file.open("rb")
        content = document.file.read(4)
        document.file.close()
        self.assertEqual(content, b"%PDF")


class LetterGenerateAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        for name in ("Offer Letters", "Appointment Letters", "HR Documents"):
            DocumentCategory.objects.get_or_create(name=name)
        cls.employee = make_employee("DOC02")
        cls.hr_user = make_user("hr_doc", UserProfile.ROLE_HR)
        cls.employee_user = make_user(
            "emp_doc", UserProfile.ROLE_EMPLOYEE, employee=cls.employee
        )

    def test_hr_can_generate_offer_letter(self):
        response = self.client.post(
            "/api/documents/generate/",
            {
                "employee": self.employee.id,
                "letter_type": "offer",
            },
            format="json",
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(EmployeeDocument.objects.count(), 1)

    def test_employee_cannot_generate_letter(self):
        response = self.client.post(
            "/api/documents/generate/",
            {
                "employee": self.employee.id,
                "letter_type": "offer",
            },
            format="json",
            **auth_header(self.employee_user),
        )
        self.assertEqual(response.status_code, 403)

    def test_download_generated_letter(self):
        create = self.client.post(
            "/api/documents/generate/",
            {
                "employee": self.employee.id,
                "letter_type": "appointment",
            },
            format="json",
            **auth_header(self.hr_user),
        )
        doc_id = create.json()["id"]
        response = self.client.get(
            f"/api/documents/{doc_id}/download/",
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
