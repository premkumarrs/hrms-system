import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger("hrms.client.api")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_URL = os.getenv("HRMS_API_URL", "http://127.0.0.1:8000/api").strip().rstrip("/") or "http://127.0.0.1:8000/api"

logger.info("HRMS API base URL: %s", BASE_URL)


class APIService:

    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.current_user = None
        self.role = None
        self.permissions = None
        self.session_expired = False
        self.on_session_expired = None
        self.last_error = None
        self.last_list_ok = True

    def login(self, username, password):

        url = f"{BASE_URL}/token/"
        logger.info("Login POST %s", url)

        try:
            response = requests.post(
                url,
                json={
                    "username": username,
                    "password": password
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.exception("Login request failed")
            self.last_error = f"Network error: {exc}"
            return False

        logger.info(
            "Login response status=%s body=%s",
            response.status_code,
            response.text[:500],
        )

        if response.status_code == 200:
            try:
                data = response.json()
            except ValueError:
                logger.exception("Login response was not valid JSON")
                self.last_error = "Invalid response from server."
                return False

            self.access_token = data["access"]
            self.refresh_token = data.get("refresh")
            self.session_expired = False

            if not self.fetch_me():
                self.logout()
                self.last_error = (
                    "Login succeeded but user profile could not be loaded."
                )
                return False

            return True

        self.last_error = (
            self._extract_error(response)
            or f"Login failed (HTTP {response.status_code})."
        )
        return False

    def logout(self):
        """Discard tokens and cached user context."""

        self.access_token = None
        self.refresh_token = None
        self.current_user = None
        self.role = None
        self.permissions = None
        self.session_expired = False

    def refresh_access_token(self):
        """Exchange the refresh token for a new access token."""

        if not self.refresh_token:
            return False

        url = f"{BASE_URL}/token/refresh/"

        try:
            response = requests.post(
                url,
                json={"refresh": self.refresh_token}
            )
        except requests.RequestException:
            return False

        if response is not None and response.status_code == 200:
            data = response.json()
            self.access_token = data["access"]
            if data.get("refresh"):
                self.refresh_token = data["refresh"]
            self.session_expired = False
            return True

        return False

    def _notify_session_expired(self):
        """Mark session expired and invoke the UI callback once."""

        if self.session_expired:
            return

        self.session_expired = True
        self.access_token = None

        if self.on_session_expired:
            self.on_session_expired()

    def _api_call(self, method, url, **kwargs):
        """Authorized HTTP call with automatic token refresh on 401."""

        if self.session_expired:
            return None

        headers = kwargs.get("headers")
        if headers is None:
            kwargs["headers"] = self.get_headers()

        try:
            response = requests.request(method, url, **kwargs)
        except requests.RequestException as exc:
            self.last_error = "Network error. Could not reach the server."
            logger.warning("API %s %s failed: %s", method, url, exc)
            return None

        if response is not None and response.status_code == 401 and self.refresh_token:
            if self.refresh_access_token():
                kwargs["headers"] = self.get_headers()
                try:
                    response = requests.request(method, url, **kwargs)
                except requests.RequestException as exc:
                    self.last_error = "Network error. Could not reach the server."
                    logger.warning("API retry %s %s failed: %s", method, url, exc)
                    return None
            else:
                self._notify_session_expired()
                return response

        if response is not None and response.status_code == 401:
            self._notify_session_expired()

        return response

    def fetch_me(self):
        """Load the current user's role and permission flags."""

        url = f"{BASE_URL}/me/"

        response = self._api_call("GET", url)

        if response is not None and response.status_code == 200:
            data = response.json()
            self.current_user = data
            self.role = data.get("role")
            self.permissions = data.get("permissions")
            return data

        return None

    def can(self, permission):
        """Return True if the current user is allowed the given permission."""

        if not self.permissions:
            return False

        return bool(self.permissions.get(permission, False))

    def get_my_profile(self):
        """Self-service: the linked employee's own profile, or None."""

        url = f"{BASE_URL}/me/profile/"

        response = self._api_call("GET", url)

        if response is not None and response.status_code == 200:
            return response.json()

        return None

    def update_my_profile(self, payload):
        """Self-service: update own contact details (partial)."""

        url = f"{BASE_URL}/me/profile/"

        response = self._api_call(
            "PATCH",
            url,
            json=payload
        )

        return self._handle_write(response, expected=200)

    def get_headers(self):

        return {
            "Authorization": f"Bearer {self.access_token}"
        }

    def get_dashboard_stats(self):

        url = f"{BASE_URL}/dashboard/stats/"

        response = self._api_call("GET", url)

        if response is not None and response.status_code == 200:
            return response.json()

        return None

    def get_dashboard_analytics(self):
        """Trend data for dashboard and analytics charts."""

        url = f"{BASE_URL}/dashboard/analytics/"

        response = self._api_call("GET", url)

        if response is not None and response.status_code == 200:
            return response.json()

        return None

    def get_dashboard_insights(self):
        """Pending approvals, upcoming events, recent notifications."""

        url = f"{BASE_URL}/dashboard/insights/"

        response = self._api_call("GET", url)

        if response is not None and response.status_code == 200:
            return response.json()

        return None

    def get_report(self, report_path, filters=None):
        """Fetch a report; returns {title, columns, rows} or None."""

        url = f"{BASE_URL}/reports/{report_path}/"

        response = self._api_call(
            "GET",
            url,
            params=filters or {}
        )

        if response is not None and response.status_code == 200:
            return response.json()

        return None

    # ------------------------------------------------------------------
    # Employees
    # ------------------------------------------------------------------

    def get_employees(self, search=None, ordering=None, department=None):

        url = f"{BASE_URL}/employees/"

        params = {}

        if search:
            params["search"] = search

        if ordering:
            params["ordering"] = ordering

        if department:
            params["department"] = department

        response = self._api_call("GET", url, params=params)

        return self._list(response)

    def create_employee(self, payload):

        url = f"{BASE_URL}/employees/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    def update_employee(self, employee_id, payload):

        url = f"{BASE_URL}/employees/{employee_id}/"

        response = self._api_call("PUT", url, json=payload)

        return self._handle_write(response, expected=200)

    def delete_employee(self, employee_id):
        return self._delete("employees", employee_id)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_departments(self, search=None):
        params = {"search": search} if search else {}
        return self._list("departments", params)

    def create_department(self, payload):
        return self._create("departments", payload)

    def update_department(self, department_id, payload):
        return self._update("departments", department_id, payload)

    def delete_department(self, department_id):
        return self._delete("departments", department_id)

    def get_designations(self, search=None):
        params = {"search": search} if search else {}
        return self._list("designations", params)

    def create_designation(self, payload):
        return self._create("designations", payload)

    def update_designation(self, designation_id, payload):
        return self._update("designations", designation_id, payload)

    def delete_designation(self, designation_id):
        return self._delete("designations", designation_id)

    def download_joining_letter(self, onboarding_id, save_path):
        """Download joining letter PDF for an onboarding record."""
        url = f"{BASE_URL}/onboardings/{onboarding_id}/joining-letter/"
        return self._download_stream(url, save_path)

    # ------------------------------------------------------------------
    # Attendance
    # ------------------------------------------------------------------

    def get_attendance(self, filters=None):

        url = f"{BASE_URL}/attendance/"

        response = self._api_call("GET", url, params=filters or {})

        return self._list(response)

    def create_attendance(self, payload):

        url = f"{BASE_URL}/attendance/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    def update_attendance(self, attendance_id, payload):

        url = f"{BASE_URL}/attendance/{attendance_id}/"

        response = self._api_call("PUT", url, json=payload)

        return self._handle_write(response, expected=200)

    def delete_attendance(self, attendance_id):
        return self._delete("attendance", attendance_id)

    def attendance_check_in(self, employee_id):

        url = f"{BASE_URL}/attendance/check-in/"

        response = self._api_call(
            "POST",
            url,
            json={"employee": employee_id}
        )

        return self._handle_write(response, expected=201)

    def attendance_check_out(self, employee_id):

        url = f"{BASE_URL}/attendance/check-out/"

        response = self._api_call(
            "POST",
            url,
            json={"employee": employee_id}
        )

        return self._handle_write(response, expected=200)

    def get_attendance_summary(self, employee_id=None, ref_date=None):

        url = f"{BASE_URL}/attendance/summary/"

        params = {}

        if employee_id:
            params["employee"] = employee_id

        if ref_date:
            params["date"] = ref_date

        response = self._api_call("GET", url, params=params)

        return self._json(response)

    def get_attendance_report(
        self, start=None, end=None, ref_date=None, employee_id=None
    ):

        url = f"{BASE_URL}/attendance/report/"

        params = {}

        if start:
            params["start"] = start

        if end:
            params["end"] = end

        if ref_date:
            params["date"] = ref_date

        if employee_id:
            params["employee"] = employee_id

        response = self._api_call("GET", url, params=params)

        return self._json(response)

    # ------------------------------------------------------------------
    # Leaves
    # ------------------------------------------------------------------

    def get_leaves(self, filters=None):

        url = f"{BASE_URL}/leaves/"

        response = self._api_call("GET", url, params=filters or {})

        return self._list(response)

    def create_leave(self, payload):

        url = f"{BASE_URL}/leaves/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    def update_leave(self, leave_id, payload):

        url = f"{BASE_URL}/leaves/{leave_id}/"

        response = self._api_call("PUT", url, json=payload)

        return self._handle_write(response, expected=200)

    def delete_leave(self, leave_id):
        return self._delete("leaves", leave_id)

    def approve_leave(self, leave_id, approved_by=None):
        return self._post_action(
            f"leaves/{leave_id}/approve/",
            approved_by=approved_by,
        )

    def reject_leave(self, leave_id, approved_by=None):
        return self._post_action(
            f"leaves/{leave_id}/reject/",
            approved_by=approved_by,
        )

    def get_leave_balance(self, employee_id, year=None):

        url = f"{BASE_URL}/leaves/balance/"

        params = {"employee": employee_id}

        if year:
            params["year"] = year

        response = self._api_call("GET", url, params=params)

        return self._json(response)

    # ------------------------------------------------------------------
    # Permissions (short time-off requests)
    # ------------------------------------------------------------------

    def get_permissions(self, filters=None):

        url = f"{BASE_URL}/permissions/"

        response = self._api_call("GET", url, params=filters or {})

        return self._list(response)

    def create_permission(self, payload):

        url = f"{BASE_URL}/permissions/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    def approve_permission(self, permission_id, approved_by=None):
        return self._post_action(
            f"permissions/{permission_id}/approve/",
            approved_by=approved_by,
        )

    def reject_permission(self, permission_id, approved_by=None):
        return self._post_action(
            f"permissions/{permission_id}/reject/",
            approved_by=approved_by,
        )

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def get_projects(self, filters=None):
        return self._list("projects", filters)

    def create_project(self, payload):

        url = f"{BASE_URL}/projects/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    def update_project(self, project_id, payload):

        url = f"{BASE_URL}/projects/{project_id}/"

        response = self._api_call("PUT", url, json=payload)

        return self._handle_write(response, expected=200)

    def delete_project(self, project_id):
        return self._delete("projects", project_id)

    def get_project_allocations(self, project_id):

        url = f"{BASE_URL}/projects/{project_id}/allocations/"

        response = self._api_call("GET", url)

        if response is not None and response.status_code == 200:
            return response.json()

        return []

    def allocate_employee(self, project_id, payload):

        url = f"{BASE_URL}/projects/{project_id}/allocate/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    # ------------------------------------------------------------------
    # Project allocations
    # ------------------------------------------------------------------

    def release_allocation(self, allocation_id, released_on=None):

        url = f"{BASE_URL}/allocations/{allocation_id}/release/"

        response = self._api_call(
            "POST",
            url,
            json={"released_on": released_on} if released_on else {}
        )

        return self._handle_write(response, expected=200)

    def update_allocation_self(self, allocation_id, payload):

        url = f"{BASE_URL}/allocations/{allocation_id}/self-update/"

        response = self._api_call("PATCH", url, json=payload)

        return self._handle_write(response, expected=200)

    def get_employee_allocations(self, employee_id, current_only=False):

        endpoint = "current" if current_only else "history"

        url = f"{BASE_URL}/allocations/{endpoint}/"

        response = self._api_call(
            "GET",
            url,
            params={"employee": employee_id}
        )

        if response is not None and response.status_code == 200:
            return response.json()

        return []

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def get_document_categories(self):

        url = f"{BASE_URL}/document-categories/"

        response = self._api_call("GET", url)

        if response is not None and response.status_code == 200:
            return self._parse_list(response)

        return []

    def get_documents(self, filters=None):
        return self._list("documents", filters)

    def generate_letter(self, payload):
        """Generate an HR letter PDF and store it as an employee document."""

        url = f"{BASE_URL}/documents/generate/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    def upload_document(self, employee_id, title, file_path, category_id=None):

        url = f"{BASE_URL}/documents/"

        data = {
            "employee": employee_id,
            "title": title,
        }

        if category_id:
            data["category"] = category_id

        try:
            with open(file_path, "rb") as handle:
                files = {"file": handle}

                response = self._api_call(
                    "POST",
                    url,
                    data=data,
                    files=files
                )
        except OSError as exc:
            return False, f"Could not read file: {exc}"

        return self._handle_write(response, expected=201)

    def download_document(self, document_id, save_path):
        url = f"{BASE_URL}/documents/{document_id}/download/"
        return self._download_stream(url, save_path)

    def delete_document(self, document_id):
        return self._delete("documents", document_id)

    # ------------------------------------------------------------------
    # Lifecycle: Onboarding
    # ------------------------------------------------------------------

    def get_onboardings(self, filters=None):
        return self._list("onboardings", filters)

    def get_onboarding_document_checklist(self, onboarding_id):

        url = f"{BASE_URL}/onboardings/{onboarding_id}/document-checklist/"

        response = self._api_call("GET", url)

        return self._json(response)

    def create_onboarding(self, payload):

        url = f"{BASE_URL}/onboardings/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    def update_onboarding(self, onboarding_id, payload):

        url = f"{BASE_URL}/onboardings/{onboarding_id}/"

        response = self._api_call("PUT", url, json=payload)

        return self._handle_write(response, expected=200)

    def delete_onboarding(self, onboarding_id):
        return self._delete("onboardings", onboarding_id)

    # ------------------------------------------------------------------
    # Lifecycle: Resignation / Exit
    # ------------------------------------------------------------------

    def get_resignations(self, filters=None):
        return self._list("resignations", filters)

    def create_resignation(self, payload):

        url = f"{BASE_URL}/resignations/"

        response = self._api_call("POST", url, json=payload)

        return self._handle_write(response, expected=201)

    def update_resignation(self, resignation_id, payload):

        url = f"{BASE_URL}/resignations/{resignation_id}/"

        response = self._api_call("PUT", url, json=payload)

        return self._handle_write(response, expected=200)

    def delete_resignation(self, resignation_id):
        return self._delete("resignations", resignation_id)

    # ------------------------------------------------------------------
    # Employee detail records (education / bank / id proof / emergency)
    # ------------------------------------------------------------------

    def _create(self, path, payload):
        response = self._api_call(
            "POST",
            f"{BASE_URL}/{path}/",
            json=payload
        )
        return self._handle_write(response, expected=201)

    def _update(self, path, item_id, payload):
        response = self._api_call(
            "PUT",
            f"{BASE_URL}/{path}/{item_id}/",
            json=payload
        )
        return self._handle_write(response, expected=200)

    def _delete(self, path, item_id):
        response = self._api_call(
            "DELETE",
            f"{BASE_URL}/{path}/{item_id}/"
        )
        if response is not None and response.status_code in (200, 204):
            return True, None
        return False, self._extract_error(response)

    # Education
    def get_education(self, employee_id):
        return self._list("education", {"employee": employee_id})

    def create_education(self, payload):
        return self._create("education", payload)

    def update_education(self, item_id, payload):
        return self._update("education", item_id, payload)

    def delete_education(self, item_id):
        return self._delete("education", item_id)

    # Bank details
    def get_bank_details(self, employee_id):
        return self._list("bank-details", {"employee": employee_id})

    def create_bank_details(self, payload):
        return self._create("bank-details", payload)

    def update_bank_details(self, item_id, payload):
        return self._update("bank-details", item_id, payload)

    def delete_bank_details(self, item_id):
        return self._delete("bank-details", item_id)

    # ID proofs
    def get_id_proofs(self, employee_id):
        return self._list("id-proofs", {"employee": employee_id})

    def create_id_proof(self, payload):
        return self._create("id-proofs", payload)

    def update_id_proof(self, item_id, payload):
        return self._update("id-proofs", item_id, payload)

    def delete_id_proof(self, item_id):
        return self._delete("id-proofs", item_id)

    # Emergency contacts
    def get_emergency_contacts(self, employee_id):
        return self._list("emergency-contacts", {"employee": employee_id})

    def create_emergency_contact(self, payload):
        return self._create("emergency-contacts", payload)

    def update_emergency_contact(self, item_id, payload):
        return self._update("emergency-contacts", item_id, payload)

    def delete_emergency_contact(self, item_id):
        return self._delete("emergency-contacts", item_id)

    # ------------------------------------------------------------------
    # Permissions (extra write ops)
    # ------------------------------------------------------------------

    def update_permission(self, permission_id, payload):
        return self._update("permissions", permission_id, payload)

    def delete_permission(self, permission_id):
        return self._delete("permissions", permission_id)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def get_notifications(self, unread=False):
        params = {"unread": "true"} if unread else {}
        return self._list("notifications", params)

    def get_unread_count(self):
        response = self._api_call(
            "GET",
            f"{BASE_URL}/notifications/unread-count/"
        )
        if response is not None and response.status_code == 200:
            return response.json().get("unread", 0)
        return 0

    def mark_notification_read(self, notification_id):
        response = self._api_call(
            "POST",
            f"{BASE_URL}/notifications/{notification_id}/mark-read/"
        )
        return self._handle_write(response, expected=200)

    def mark_all_notifications_read(self):
        response = self._api_call(
            "POST",
            f"{BASE_URL}/notifications/mark-all-read/"
        )
        return self._handle_write(response, expected=200)

    def generate_notifications(self):
        response = self._api_call(
            "POST",
            f"{BASE_URL}/notifications/generate/"
        )
        return self._handle_write(response, expected=201)

    # ------------------------------------------------------------------
    # Payroll
    # ------------------------------------------------------------------

    def get_salaries(self, filters=None):
        return self._list("salaries", filters)

    def create_salary(self, payload):
        return self._create("salaries", payload)

    def update_salary(self, salary_id, payload):
        return self._update("salaries", salary_id, payload)

    def delete_salary(self, salary_id):
        return self._delete("salaries", salary_id)

    def download_payslip(self, salary_id, save_path):
        """Download payslip PDF for a salary record."""
        url = f"{BASE_URL}/salaries/{salary_id}/payslip/"
        return self._download_stream(url, save_path)

    def get_employee_salary_history(self, employee_id):
        """All salary records for one employee (payslip history)."""

        return self._list("salaries", {"employee": employee_id})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _post_action(self, path, approved_by=None, expected=200):
        """POST to an action endpoint (approve/reject, etc.)."""

        url = f"{BASE_URL}/{path.lstrip('/')}"
        payload = {"approved_by": approved_by} if approved_by else {}
        response = self._api_call("POST", url, json=payload)
        return self._handle_write(response, expected=expected)

    def _ok(self, response, codes=(200,)):
        return response is not None and response.status_code in codes

    def _json(self, response, default=None):
        if not self._ok(response):
            return default
        try:
            return response.json()
        except ValueError:
            return default

    def _parse_list(self, response):
        data = self._json(response, default=[])
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data if isinstance(data, list) else []

    def _download_stream(self, url, save_path):
        """Stream a binary response to disk."""

        response = self._api_call("GET", url, stream=True)

        if response is None or response.status_code != 200:
            return False, self._extract_error(response)

        try:
            with open(save_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        handle.write(chunk)
        except OSError as exc:
            return False, f"Could not save file: {exc}"

        return True, None

    def _list(self, path_or_response, params=None):
        """Fetch a list from an API path, or parse a list from a response."""

        if isinstance(path_or_response, str):
            response = self._api_call(
                "GET",
                f"{BASE_URL}/{path_or_response}/",
                params=params or {},
            )
            if not self._ok(response):
                self.last_list_ok = False
                return []
            self.last_list_ok = True
            return self._parse_list(response)

        if not path_or_response or not self._ok(path_or_response):
            self.last_list_ok = False
            return []

        self.last_list_ok = True
        return self._parse_list(path_or_response)

    def _handle_write(self, response, expected):

        if response is None:
            message = self.last_error or "Session expired or network error."
            return False, message

        if response.status_code == expected:
            return True, response.json()

        return False, self._extract_error(response)

    def _extract_error(self, response):

        if response is None:
            return self.last_error or "Session expired or network error."

        try:
            data = response.json()
        except ValueError:
            return f"Request failed (HTTP {response.status_code})"

        if isinstance(data, dict):

            messages = []

            for field, errors in data.items():

                if isinstance(errors, list):
                    joined = ", ".join(str(e) for e in errors)
                else:
                    joined = str(errors)

                messages.append(f"{field}: {joined}")

            return "\n".join(messages)

        return str(data)
