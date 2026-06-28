from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QPlainTextEdit,
    QCheckBox,
    QPushButton,
    QLabel,
    QMessageBox
)

from PyQt6.QtCore import QDate


STATUS_CHOICES = [
    ("ACTIVE", "Active"),
    ("INACTIVE", "Inactive"),
    ("RESIGNED", "Resigned"),
]


class EmployeeForm(QDialog):
    """Add / edit dialog for a single employee.

    Pass ``employee`` (a dict from the API) to edit; leave it ``None`` to add.
    """

    def __init__(self, api, employee=None, parent=None):

        super().__init__(parent)

        self.api = api

        self.employee = employee

        self.is_edit = employee is not None

        self.setWindowTitle(
            "Edit Employee" if self.is_edit else "Add Employee"
        )

        self.resize(460, 640)

        self.departments = self.api.get_departments()

        self.designations = self.api.get_designations()

        self.build_ui()

        if self.is_edit:
            self.populate()

    def build_ui(self):

        layout = QVBoxLayout()

        form = QFormLayout()

        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.employee_code = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        self.branch = QLineEdit()

        # Date of birth is optional; the checkbox controls whether it is sent.
        self.dob_enabled = QCheckBox("Set date of birth")
        self.date_of_birth = QDateEdit()
        self.date_of_birth.setCalendarPopup(True)
        self.date_of_birth.setDisplayFormat("yyyy-MM-dd")
        self.date_of_birth.setDate(QDate(2000, 1, 1))
        self.date_of_birth.setEnabled(False)
        self.dob_enabled.toggled.connect(self.date_of_birth.setEnabled)

        dob_row = QHBoxLayout()
        dob_row.addWidget(self.dob_enabled)
        dob_row.addWidget(self.date_of_birth)

        self.joining_date = QDateEdit()
        self.joining_date.setCalendarPopup(True)
        self.joining_date.setDisplayFormat("yyyy-MM-dd")
        self.joining_date.setDate(QDate.currentDate())

        self.address = QPlainTextEdit()
        self.address.setFixedHeight(70)

        self.department = QComboBox()
        self.department.addItem("-- None --", None)
        for dept in self.departments:
            self.department.addItem(dept["name"], dept["id"])

        self.designation = QComboBox()
        self.designation.addItem("-- None --", None)
        for desig in self.designations:
            self.designation.addItem(desig["title"], desig["id"])

        self.status = QComboBox()
        for value, label in STATUS_CHOICES:
            self.status.addItem(label, value)

        form.addRow("First Name *", self.first_name)
        form.addRow("Last Name *", self.last_name)
        form.addRow("Employee Code *", self.employee_code)
        form.addRow("Email *", self.email)
        form.addRow("Phone", self.phone)
        form.addRow("Branch", self.branch)
        form.addRow("Date of Birth", dob_row)
        form.addRow("Joining Date *", self.joining_date)
        form.addRow("Address", self.address)
        form.addRow("Department", self.department)
        form.addRow("Designation", self.designation)
        form.addRow("Status", self.status)

        layout.addLayout(form)

        hint = QLabel("* required fields")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint)

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

        emp = self.employee

        self.first_name.setText(emp.get("first_name", ""))
        self.last_name.setText(emp.get("last_name", ""))
        self.employee_code.setText(emp.get("employee_code", ""))
        self.email.setText(emp.get("email", ""))
        self.phone.setText(emp.get("phone", ""))
        self.branch.setText(emp.get("branch", "") or "")
        self.address.setPlainText(emp.get("address", "") or "")

        if emp.get("date_of_birth"):
            self.dob_enabled.setChecked(True)
            self.date_of_birth.setEnabled(True)
            self.date_of_birth.setDate(
                QDate.fromString(emp["date_of_birth"], "yyyy-MM-dd")
            )

        if emp.get("joining_date"):
            self.joining_date.setDate(
                QDate.fromString(emp["joining_date"], "yyyy-MM-dd")
            )

        self._select_by_data(self.department, emp.get("department"))
        self._select_by_data(self.designation, emp.get("designation"))
        self._select_by_data(self.status, emp.get("status"))

    def _select_by_data(self, combo, value):

        index = combo.findData(value)

        if index >= 0:
            combo.setCurrentIndex(index)

    def collect_payload(self):

        payload = {
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "employee_code": self.employee_code.text().strip(),
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "branch": self.branch.text().strip(),
            "address": self.address.toPlainText().strip(),
            "joining_date": self.joining_date.date().toString("yyyy-MM-dd"),
            "department": self.department.currentData(),
            "designation": self.designation.currentData(),
            "status": self.status.currentData(),
        }

        if self.dob_enabled.isChecked():
            payload["date_of_birth"] = (
                self.date_of_birth.date().toString("yyyy-MM-dd")
            )
        else:
            payload["date_of_birth"] = None

        return payload

    def validate(self, payload):

        missing = []

        if not payload["first_name"]:
            missing.append("First Name")

        if not payload["last_name"]:
            missing.append("Last Name")

        if not payload["employee_code"]:
            missing.append("Employee Code")

        if not payload["email"]:
            missing.append("Email")

        if missing:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please fill in:\n- " + "\n- ".join(missing)
            )
            return False

        return True

    def save(self):

        payload = self.collect_payload()

        if not self.validate(payload):
            return

        if self.is_edit:
            ok, result = self.api.update_employee(
                self.employee["id"],
                payload
            )
        else:
            ok, result = self.api.create_employee(payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Save Failed",
                str(result)
            )
