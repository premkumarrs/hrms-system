import os

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QCheckBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
    QMessageBox
)

from PyQt6.QtCore import Qt, QDate

from leave_form import LeaveForm
from permission_form import PermissionForm
from leave_window import LeaveBalanceDialog
from ui_helpers import loading, show_list_load_error


class _SimpleTable(QWidget):
    """A read-only table tab with a loader callback."""

    def __init__(self, columns, loader):

        super().__init__()

        self.loader = loader

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(self.table)

        self.setLayout(layout)

    def fill(self, rows):

        self.table.setRowCount(len(rows))

        for r, values in enumerate(rows):
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))

    def refresh(self):
        self.loader()


class SelfServiceWindow(QWidget):

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.profile = None

        self.employee_id = None

        self.setWindowTitle("Employee Self Service")

        self.resize(1100, 660)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Employee Self Service")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.profile = self.api.get_my_profile()

        if not self.profile:
            note = QLabel(
                "No employee profile is linked to your account.\n"
                "Ask HR to link your user to an employee record."
            )
            note.setStyleSheet("font-size: 16px; color: gray; margin-top: 40px;")
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(note)
            self.setLayout(layout)
            return

        self.employee_id = self.profile.get("id")

        self.tabs = QTabWidget()

        self.tabs.addTab(self.build_profile_tab(), "My Profile")
        self.tabs.addTab(self.build_attendance_tab(), "My Attendance")
        self.tabs.addTab(self.build_leaves_tab(), "My Leaves")
        self.tabs.addTab(self.build_permissions_tab(), "My Permissions")
        self.tabs.addTab(self.build_documents_tab(), "My Documents")
        self.tabs.addTab(self.build_projects_tab(), "My Projects")
        self.tabs.addTab(self.build_payslips_tab(), "My Payslips")

        layout.addWidget(self.tabs)

        self.setLayout(layout)

        self.reload_all()

    # ------------------------------------------------------------------
    # Profile tab (view + update personal details)
    # ------------------------------------------------------------------

    def build_profile_tab(self):

        page = QWidget()
        layout = QVBoxLayout()

        name = f"{self.profile.get('first_name', '')} {self.profile.get('last_name', '')}".strip()
        heading = QLabel(f"{name}  ({self.profile.get('employee_code', '')})")
        heading.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(heading)

        # Read-only org info.
        info = QLabel(
            f"Department: {self.profile.get('department_name') or '-'}    "
            f"Designation: {self.profile.get('designation_title') or '-'}    "
            f"Branch: {self.profile.get('branch') or '-'}    "
            f"Status: {self.profile.get('status') or '-'}"
        )
        info.setStyleSheet("color: #9aa0c0;")
        layout.addWidget(info)

        form = QFormLayout()

        self.email_input = QLineEdit(self.profile.get("email", "") or "")
        self.phone_input = QLineEdit(self.profile.get("phone", "") or "")

        self.dob_enabled = QCheckBox("Set date of birth")
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setDisplayFormat("yyyy-MM-dd")
        self.dob_input.setDate(QDate(2000, 1, 1))
        self.dob_input.setEnabled(False)
        self.dob_enabled.toggled.connect(self.dob_input.setEnabled)

        if self.profile.get("date_of_birth"):
            self.dob_enabled.setChecked(True)
            self.dob_input.setEnabled(True)
            self.dob_input.setDate(
                QDate.fromString(self.profile["date_of_birth"], "yyyy-MM-dd")
            )

        dob_row = QHBoxLayout()
        dob_row.addWidget(self.dob_enabled)
        dob_row.addWidget(self.dob_input)

        self.address_input = QPlainTextEdit(self.profile.get("address", "") or "")
        self.address_input.setFixedHeight(80)

        form.addRow("Email", self.email_input)
        form.addRow("Phone", self.phone_input)
        form.addRow("Date of Birth", dob_row)
        form.addRow("Address", self.address_input)

        layout.addLayout(form)

        save_button = QPushButton("Update Personal Details")
        save_button.clicked.connect(self.save_profile)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(save_button)
        layout.addLayout(button_row)

        layout.addStretch()

        page.setLayout(layout)
        return page

    def save_profile(self):

        payload = {
            "email": self.email_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "address": self.address_input.toPlainText().strip(),
        }

        if self.dob_enabled.isChecked():
            payload["date_of_birth"] = self.dob_input.date().toString("yyyy-MM-dd")
        else:
            payload["date_of_birth"] = None

        ok, result = self.api.update_my_profile(payload)

        if ok:
            self.profile = result
            QMessageBox.information(
                self, "Saved", "Your details have been updated."
            )
        else:
            QMessageBox.critical(self, "Update Failed", str(result))

    # ------------------------------------------------------------------
    # Attendance tab
    # ------------------------------------------------------------------

    def build_attendance_tab(self):

        page = QWidget()
        layout = QVBoxLayout()

        self.today_status_label = QLabel("Loading today's attendance...")
        self.today_status_label.setStyleSheet("color: #9aa0c0; padding: 8px;")
        layout.addWidget(self.today_status_label)

        button_row = QHBoxLayout()
        self.check_in_button = QPushButton("Check In")
        self.check_in_button.clicked.connect(self.check_in_today)
        button_row.addWidget(self.check_in_button)

        self.check_out_button = QPushButton("Check Out")
        self.check_out_button.clicked.connect(self.check_out_today)
        button_row.addWidget(self.check_out_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.attendance_table = _SimpleTable(
            ["Date", "Check In", "Check Out", "Hours", "Late", "Status"],
            self.load_attendance
        )
        layout.addWidget(self.attendance_table)

        page.setLayout(layout)
        return page

    def _today_iso(self):
        return QDate.currentDate().toString("yyyy-MM-dd")

    def refresh_today_attendance(self):
        records = self.api.get_attendance({
            "employee": self.employee_id,
            "date": self._today_iso(),
        })
        record = records[0] if records else None

        if record is None:
            self.today_status_label.setText(
                "Today: Not checked in yet."
            )
            self.check_in_button.setEnabled(True)
            self.check_out_button.setEnabled(False)
            return

        check_in = (record.get("check_in") or "")[:5] or "-"
        check_out = (record.get("check_out") or "")[:5] if record.get("check_out") else "-"
        status = record.get("status_display") or record.get("status") or "-"

        self.today_status_label.setText(
            f"Today: Check In {check_in} · Check Out {check_out} · Status {status}"
        )

        has_check_in = bool(record.get("check_in"))
        has_check_out = bool(record.get("check_out"))
        self.check_in_button.setEnabled(not has_check_in)
        self.check_out_button.setEnabled(has_check_in and not has_check_out)

    def check_in_today(self):
        ok, result = self.api.attendance_check_in(self.employee_id)
        if ok:
            QMessageBox.information(self, "Checked In", "Check-in recorded for today.")
            self.refresh_today_attendance()
            self.load_attendance()
        else:
            QMessageBox.critical(self, "Check-In Failed", str(result))

    def check_out_today(self):
        ok, result = self.api.attendance_check_out(self.employee_id)
        if ok:
            QMessageBox.information(self, "Checked Out", "Check-out recorded for today.")
            self.refresh_today_attendance()
            self.load_attendance()
        else:
            QMessageBox.critical(self, "Check-Out Failed", str(result))

    def load_attendance(self):

        with loading(self):
            records = self.api.get_attendance({"employee": self.employee_id})

        if show_list_load_error(self, self.api, "attendance records"):
            return

        rows = [
            [
                rec.get("date", ""),
                (rec.get("check_in") or "")[:5],
                (rec.get("check_out") or "-")[:5] if rec.get("check_out") else "-",
                rec.get("working_hours", ""),
                "Yes" if rec.get("late_entry") else "No",
                rec.get("status_display") or rec.get("status", ""),
            ]
            for rec in records
        ]

        self.attendance_table.fill(rows)

    # ------------------------------------------------------------------
    # Leaves tab (view + apply)
    # ------------------------------------------------------------------

    def build_leaves_tab(self):

        page = QWidget()
        layout = QVBoxLayout()

        button_row = QHBoxLayout()
        apply_button = QPushButton("Apply Leave")
        apply_button.clicked.connect(self.apply_leave)
        balance_button = QPushButton("View Leave Balance")
        balance_button.clicked.connect(self.show_leave_balance)
        button_row.addWidget(apply_button)
        button_row.addWidget(balance_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.leaves_table = _SimpleTable(
            ["Type", "Start", "End", "Days", "Status", "Approved By"],
            self.load_leaves
        )
        layout.addWidget(self.leaves_table)

        page.setLayout(layout)
        return page

    def load_leaves(self):

        with loading(self):
            records = self.api.get_leaves({"employee": self.employee_id})

        if show_list_load_error(self, self.api, "leave requests"):
            return

        rows = [
            [
                rec.get("leave_type_display") or rec.get("leave_type", ""),
                rec.get("start_date", ""),
                rec.get("end_date", ""),
                rec.get("number_of_days", ""),
                rec.get("status_display") or rec.get("status", ""),
                rec.get("approved_by_name") or "-",
            ]
            for rec in records
        ]

        self.leaves_table.fill(rows)

    def apply_leave(self):

        # Restrict the picker to the current employee only.
        form = LeaveForm(self.api, [self.profile], parent=self)

        if form.exec():
            self.load_leaves()

    def show_leave_balance(self):

        balance = self.api.get_leave_balance(self.employee_id)
        if not balance:
            QMessageBox.warning(
                self, "Unavailable", "Could not load leave balance."
            )
            return

        name = (
            f"{self.profile.get('first_name', '')} "
            f"{self.profile.get('last_name', '')}"
        ).strip()
        LeaveBalanceDialog(name, balance, parent=self).exec()

    # ------------------------------------------------------------------
    # Permissions tab (view + apply)
    # ------------------------------------------------------------------

    def build_permissions_tab(self):

        page = QWidget()
        layout = QVBoxLayout()

        button_row = QHBoxLayout()
        apply_button = QPushButton("Apply Permission")
        apply_button.clicked.connect(self.apply_permission)
        button_row.addWidget(apply_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.permissions_table = _SimpleTable(
            ["Date", "From", "To", "Status", "Approved By"],
            self.load_permissions
        )
        layout.addWidget(self.permissions_table)

        page.setLayout(layout)
        return page

    def load_permissions(self):

        with loading(self):
            records = self.api.get_permissions({"employee": self.employee_id})

        if show_list_load_error(self, self.api, "permission requests"):
            return

        rows = [
            [
                rec.get("date", ""),
                (rec.get("from_time") or "")[:5],
                (rec.get("to_time") or "")[:5],
                rec.get("status_display") or rec.get("status", ""),
                rec.get("approved_by_name") or "-",
            ]
            for rec in records
        ]

        self.permissions_table.fill(rows)

    def apply_permission(self):

        form = PermissionForm(self.api, [self.profile], parent=self)

        if form.exec():
            self.load_permissions()

    # ------------------------------------------------------------------
    # Documents tab (view + download)
    # ------------------------------------------------------------------

    def build_documents_tab(self):

        page = QWidget()
        layout = QVBoxLayout()

        button_row = QHBoxLayout()
        download_button = QPushButton("Download Selected")
        download_button.clicked.connect(self.download_document)
        button_row.addWidget(download_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.documents_table = _SimpleTable(
            ["Category", "Title", "File", "Uploaded"],
            self.load_documents
        )
        layout.addWidget(self.documents_table)

        page.setLayout(layout)
        return page

    def load_documents(self):

        with loading(self):
            self.documents = self.api.get_documents({"employee": self.employee_id})

        if show_list_load_error(self, self.api, "documents"):
            return

        rows = [
            [
                doc.get("category_name") or "-",
                doc.get("title", ""),
                doc.get("file_name", ""),
                (doc.get("uploaded_at", "") or "")[:10],
            ]
            for doc in self.documents
        ]

        self.documents_table.fill(rows)

    def download_document(self):

        row = self.documents_table.table.currentRow()

        if row < 0 or row >= len(self.documents):
            QMessageBox.information(
                self, "No Selection", "Please select a document to download."
            )
            return

        doc = self.documents[row]
        suggested = doc.get("file_name") or f"document_{doc['id']}"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Document As", suggested
        )

        if not save_path:
            return

        ok, error = self.api.download_document(doc["id"], save_path)

        if ok:
            QMessageBox.information(
                self, "Downloaded",
                f"Saved to:\n{os.path.basename(save_path)}"
            )
        else:
            QMessageBox.critical(self, "Download Failed", str(error))

    # ------------------------------------------------------------------
    # Projects tab
    # ------------------------------------------------------------------

    def build_projects_tab(self):

        page = QWidget()
        layout = QVBoxLayout()

        note = QLabel(
            "You may update your role, responsibilities, and notes on active "
            "assignments. Project allocation changes are managed by HR."
        )
        note.setStyleSheet("color: #9aa0c0;")
        layout.addWidget(note)

        button_row = QHBoxLayout()
        self.edit_project_button = QPushButton("Edit Selected Assignment")
        self.edit_project_button.clicked.connect(self.edit_project_details)
        button_row.addWidget(self.edit_project_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.projects_table = _SimpleTable(
            ["Project", "Role", "Responsibilities", "Allocated", "Released", "Active"],
            self.load_projects
        )
        layout.addWidget(self.projects_table)

        page.setLayout(layout)
        return page

    def load_projects(self):

        with loading(self):
            self.project_records = self.api.get_employee_allocations(
                self.employee_id, current_only=False
            )

        if show_list_load_error(self, self.api, "project assignments"):
            return

        rows = [
            [
                alloc.get("project_name", ""),
                alloc.get("role", ""),
                (alloc.get("responsibilities") or "")[:40] or "-",
                alloc.get("allocated_on", ""),
                alloc.get("released_on") or "-",
                "Yes" if alloc.get("is_active") else "No",
            ]
            for alloc in self.project_records
        ]

        self.projects_table.fill(rows)

    def edit_project_details(self):
        row = self.projects_table.table.currentRow()
        if row < 0 or row >= len(self.project_records):
            QMessageBox.information(
                self, "No Selection", "Select an active project assignment to edit."
            )
            return

        alloc = self.project_records[row]
        if not alloc.get("is_active"):
            QMessageBox.warning(
                self,
                "Not Editable",
                "Only active project assignments can be updated.",
            )
            return

        from project_self_form import ProjectSelfUpdateForm

        form = ProjectSelfUpdateForm(alloc, parent=self)
        if not form.exec():
            return

        ok, result = self.api.update_allocation_self(
            alloc["id"], form.get_payload()
        )
        if ok:
            QMessageBox.information(self, "Saved", "Project details updated.")
            self.load_projects()
        else:
            QMessageBox.critical(self, "Update Failed", str(result))

    # ------------------------------------------------------------------
    # Payslips tab
    # ------------------------------------------------------------------

    def build_payslips_tab(self):

        page = QWidget()
        layout = QVBoxLayout()

        button_row = QHBoxLayout()
        download_button = QPushButton("Download Selected Payslip")
        download_button.clicked.connect(self.download_payslip)
        button_row.addWidget(download_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.payslips_table = _SimpleTable(
            ["Period", "Basic", "Allowances", "Deductions", "Net Salary"],
            self.load_payslips
        )
        layout.addWidget(self.payslips_table)

        page.setLayout(layout)
        return page

    def load_payslips(self):

        with loading(self):
            self.payslip_records = self.api.get_employee_salary_history(
                self.employee_id
            )

        if show_list_load_error(self, self.api, "payslip records"):
            return

        rows = [
            [
                rec.get("period", ""),
                str(rec.get("basic_salary", "")),
                str(rec.get("allowances", "")),
                str(rec.get("deductions", "")),
                str(rec.get("net_salary", "")),
            ]
            for rec in self.payslip_records
        ]

        self.payslips_table.fill(rows)

    def download_payslip(self):

        row = self.payslips_table.table.currentRow()
        if row < 0 or row >= len(self.payslip_records):
            QMessageBox.information(
                self, "No Selection", "Select a payslip record to download."
            )
            return

        record = self.payslip_records[row]
        code = self.profile.get("employee_code", "employee")
        default_name = f"payslip_{code}_{record.get('period', 'period')}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Payslip", default_name, "PDF (*.pdf)"
        )
        if not save_path:
            return

        ok, error = self.api.download_payslip(record["id"], save_path)
        if ok:
            QMessageBox.information(
                self, "Downloaded", f"Payslip saved to:\n{save_path}"
            )
        else:
            QMessageBox.critical(self, "Download Failed", str(error))

    # ------------------------------------------------------------------

    def reload_all(self):
        if hasattr(self, "refresh_today_attendance"):
            self.refresh_today_attendance()
        self.load_attendance()
        self.load_leaves()
        self.load_permissions()
        self.load_documents()
        self.load_projects()
        if hasattr(self, "load_payslips"):
            self.load_payslips()
