from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QDateEdit,
    QCheckBox,
    QPlainTextEdit,
    QPushButton,
    QMessageBox
)

from PyQt6.QtCore import QDate


STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("IN_PROGRESS", "In Progress"),
    ("COMPLETED", "Completed"),
]


class OnboardingForm(QDialog):
    """Add / edit dialog for an employee onboarding record."""

    def __init__(self, api, employees, record=None, parent=None):

        super().__init__(parent)

        self.api = api
        self.employees = employees
        self.record = record
        self.is_edit = record is not None

        self.setWindowTitle(
            "Edit Onboarding" if self.is_edit else "Add Onboarding"
        )

        self.resize(440, 420)

        self.build_ui()

        if self.is_edit:
            self.populate()

    def build_ui(self):

        layout = QVBoxLayout()

        form = QFormLayout()

        self.employee = QComboBox()
        for emp in self.employees:
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            label = f"{name} ({emp.get('employee_code', '')})"
            self.employee.addItem(label, emp["id"])

        self.joining_date = QDateEdit()
        self.joining_date.setCalendarPopup(True)
        self.joining_date.setDisplayFormat("yyyy-MM-dd")
        self.joining_date.setDate(QDate.currentDate())

        self.department_assigned = QCheckBox("Department assigned")
        self.designation_assigned = QCheckBox("Designation assigned")
        self.documents_submitted = QCheckBox("Joining documents submitted")

        self.status = QComboBox()
        for value, label in STATUS_CHOICES:
            self.status.addItem(label, value)

        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(80)

        form.addRow("Employee *", self.employee)
        form.addRow("Joining Date", self.joining_date)
        form.addRow("", self.department_assigned)
        form.addRow("", self.designation_assigned)
        form.addRow("", self.documents_submitted)
        form.addRow("Status", self.status)
        form.addRow("Notes", self.notes)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton(
            "Update" if self.is_edit else "Create"
        )
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)

        layout.addLayout(buttons)

        self.setLayout(layout)

    def populate(self):

        rec = self.record

        index = self.employee.findData(rec.get("employee"))
        if index >= 0:
            self.employee.setCurrentIndex(index)

        if rec.get("joining_date"):
            self.joining_date.setDate(
                QDate.fromString(rec["joining_date"], "yyyy-MM-dd")
            )

        self.department_assigned.setChecked(
            bool(rec.get("department_assigned"))
        )
        self.designation_assigned.setChecked(
            bool(rec.get("designation_assigned"))
        )
        self.documents_submitted.setChecked(
            bool(rec.get("documents_submitted"))
        )

        status_index = self.status.findData(rec.get("status"))
        if status_index >= 0:
            self.status.setCurrentIndex(status_index)

        self.notes.setPlainText(rec.get("notes", "") or "")

    def collect_payload(self):

        return {
            "employee": self.employee.currentData(),
            "joining_date": self.joining_date.date().toString("yyyy-MM-dd"),
            "department_assigned": self.department_assigned.isChecked(),
            "designation_assigned": self.designation_assigned.isChecked(),
            "documents_submitted": self.documents_submitted.isChecked(),
            "status": self.status.currentData(),
            "notes": self.notes.toPlainText().strip(),
        }

    def save(self):

        payload = self.collect_payload()

        if payload["employee"] is None:
            QMessageBox.warning(
                self, "Missing Information", "Please select an employee."
            )
            return

        if self.is_edit:
            ok, result = self.api.update_onboarding(self.record["id"], payload)
        else:
            ok, result = self.api.create_onboarding(payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Save Failed", str(result))
