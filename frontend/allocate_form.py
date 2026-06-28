from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QDateEdit,
    QPushButton,
    QMessageBox
)

from PyQt6.QtCore import QDate


class AllocateForm(QDialog):
    """Allocate an employee to a given project."""

    def __init__(self, api, project, employees, parent=None):

        super().__init__(parent)

        self.api = api

        self.project = project

        self.employees = employees

        self.setWindowTitle("Allocate Employee")

        self.resize(420, 240)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout()

        heading = QLabel(f"Project: {self.project.get('name', '')}")
        heading.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(heading)

        form = QFormLayout()

        self.employee = QComboBox()
        for emp in self.employees:
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            label = f"{name} ({emp.get('employee_code', '')})"
            self.employee.addItem(label, emp["id"])

        self.role = QLineEdit()
        self.role.setPlaceholderText("e.g. Developer, Lead, QA")

        self.allocated_on = QDateEdit()
        self.allocated_on.setCalendarPopup(True)
        self.allocated_on.setDisplayFormat("yyyy-MM-dd")
        self.allocated_on.setDate(QDate.currentDate())

        form.addRow("Employee *", self.employee)
        form.addRow("Role *", self.role)
        form.addRow("Allocated On *", self.allocated_on)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Allocate")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)

        layout.addLayout(buttons)

        self.setLayout(layout)

    def save(self):

        employee_id = self.employee.currentData()
        role = self.role.text().strip()

        if employee_id is None:
            QMessageBox.warning(
                self, "Missing Information", "Please select an employee."
            )
            return

        if not role:
            QMessageBox.warning(
                self, "Missing Information", "Please provide a role."
            )
            return

        payload = {
            "employee": employee_id,
            "role": role,
            "allocated_on": self.allocated_on.date().toString("yyyy-MM-dd"),
        }

        ok, result = self.api.allocate_employee(self.project["id"], payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Allocation Failed", str(result))
