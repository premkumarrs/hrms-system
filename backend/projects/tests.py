from datetime import date

from rest_framework.test import APITestCase

from authentication.models import UserProfile
from hrms_test_utils import auth_header, make_employee, make_user
from projects.models import Project, ProjectAllocation


class ProjectScopeTests(APITestCase):

    def setUp(self):
        self.mgr_emp = make_employee("PM01")
        self.team_emp = make_employee("PT01", manager=self.mgr_emp)
        self.other_emp = make_employee("PO01")

        self.project_a = Project.objects.create(
            name="Alpha",
            client="Client A",
            start_date=date(2025, 1, 1),
            status="ACTIVE",
        )
        self.project_b = Project.objects.create(
            name="Beta",
            client="Client B",
            start_date=date(2025, 1, 1),
            status="ACTIVE",
        )
        ProjectAllocation.objects.create(
            project=self.project_a,
            employee=self.team_emp,
            allocated_on=date(2025, 2, 1),
        )
        ProjectAllocation.objects.create(
            project=self.project_b,
            employee=self.other_emp,
            allocated_on=date(2025, 2, 1),
        )

        self.mgr_user = make_user(
            "proj_mgr", UserProfile.ROLE_MANAGER, employee=self.mgr_emp
        )

    def test_manager_sees_team_projects_only(self):
        response = self.client.get("/api/projects/", **auth_header(self.mgr_user))
        self.assertEqual(response.status_code, 200)
        names = {row["name"] for row in response.json()}
        self.assertIn("Alpha", names)
        self.assertNotIn("Beta", names)
