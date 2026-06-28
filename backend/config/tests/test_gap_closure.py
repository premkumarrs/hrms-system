"""Tests for gap-closure features."""

from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from authentication.groups import ensure_hrms_groups, sync_profile_groups
from authentication.models import UserProfile
from config.cycle import cycle_period_label, get_cycle_range
from documents.models import DocumentCategory, EmployeeDocument
from hrms_test_utils import auth_header, make_employee, make_user
from lifecycle.models import Onboarding
from lifecycle.onboarding_checklist import compute_document_checklist, sync_onboarding_document_status
from leaves.models import Permission
from notifications.models import Notification
from projects.models import Project, ProjectAllocation


class CycleUtilityTests(APITestCase):

    def test_cycle_range_26_to_25(self):
        ref = date(2026, 6, 10)
        start, end = get_cycle_range(ref)
        self.assertEqual(start, date(2026, 5, 26))
        self.assertEqual(end, date(2026, 6, 25))
        self.assertEqual(cycle_period_label(ref), "2026-06")


class ProjectSelfUpdateTests(APITestCase):

    def setUp(self):
        self.employee = make_employee("SS01")
        self.other = make_employee("SS02")
        self.project = Project.objects.create(
            name="HRMS",
            client="Internal",
            start_date=date(2025, 1, 1),
            status="ACTIVE",
        )
        self.allocation = ProjectAllocation.objects.create(
            employee=self.employee,
            project=self.project,
            allocated_on=date(2025, 2, 1),
            role="Developer",
        )
        self.emp_user = make_user(
            "emp_ss", UserProfile.ROLE_EMPLOYEE, employee=self.employee
        )

    def test_employee_can_self_update_active_allocation(self):
        response = self.client.patch(
            f"/api/allocations/{self.allocation.id}/self-update/",
            {
                "role": "Senior Developer",
                "responsibilities": "API maintenance",
                "notes": "Primary backend contact",
            },
            format="json",
            **auth_header(self.emp_user),
        )
        self.assertEqual(response.status_code, 200)
        self.allocation.refresh_from_db()
        self.assertEqual(self.allocation.role, "Senior Developer")

    def test_employee_cannot_update_other_allocation(self):
        other_alloc = ProjectAllocation.objects.create(
            employee=self.other,
            project=self.project,
            allocated_on=date(2025, 2, 1),
            role="QA",
        )
        response = self.client.patch(
            f"/api/allocations/{other_alloc.id}/self-update/",
            {"role": "Hacker"},
            format="json",
            **auth_header(self.emp_user),
        )
        self.assertEqual(response.status_code, 404)


class PermissionNotificationTests(APITestCase):

    def setUp(self):
        ensure_hrms_groups()
        self.mgr_emp = make_employee("PM01")
        self.employee = make_employee("PN01", manager=self.mgr_emp)
        self.mgr_user = make_user(
            "mgr_pn", UserProfile.ROLE_MANAGER, employee=self.mgr_emp
        )
        self.emp_user = User.objects.create_user(
            username="emp_pn", password="testpass123"
        )
        profile = UserProfile.objects.create(
            user=self.emp_user,
            role=UserProfile.ROLE_EMPLOYEE,
            employee=self.employee,
        )
        sync_profile_groups(profile)
        self.permission = Permission.objects.create(
            employee=self.employee,
            date=date(2026, 8, 1),
            from_time="10:00",
            to_time="12:00",
            reason="Personal",
            status="PENDING",
        )

    def test_permission_approve_notifies_employee(self):
        response = self.client.post(
            f"/api/permissions/{self.permission.id}/approve/",
            {},
            format="json",
            **auth_header(self.mgr_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Notification.objects.filter(
                notification_type=Notification.TYPE_PERMISSION_APPROVED,
                recipient=self.emp_user,
            ).exists()
        )


class OnboardingChecklistTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        for name in ("Offer Letters", "Appointment Letters", "HR Documents"):
            DocumentCategory.objects.get_or_create(name=name)

    def setUp(self):
        self.employee = make_employee("OB01")
        self.onboarding = Onboarding.objects.create(employee=self.employee)
        self.hr_user = make_user("hr_ob", UserProfile.ROLE_HR)

    def test_checklist_endpoint(self):
        response = self.client.get(
            f"/api/onboardings/{self.onboarding.id}/document-checklist/",
            **auth_header(self.hr_user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_count"], 4)
        self.assertFalse(response.json()["is_complete"])

    def test_upload_syncs_onboarding_status(self):
        offer_cat = DocumentCategory.objects.get(name="Offer Letters")
        appt_cat = DocumentCategory.objects.get(name="Appointment Letters")
        hr_cat = DocumentCategory.objects.get(name="HR Documents")

        for cat, title in (
            (offer_cat, "Offer Letter - OB01"),
            (appt_cat, "Appointment Letter - OB01"),
            (hr_cat, "PAN ID Proof"),
            (hr_cat, "Bank Account Proof"),
        ):
            EmployeeDocument.objects.create(
                employee=self.employee,
                category=cat,
                title=title,
                file="employee_documents/test.pdf",
            )

        checklist = sync_onboarding_document_status(self.onboarding)
        self.onboarding.refresh_from_db()
        self.assertTrue(checklist["is_complete"])
        self.assertTrue(self.onboarding.documents_submitted)
