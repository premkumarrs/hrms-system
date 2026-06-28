from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QDateEdit,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QMessageBox
)

from PyQt6.QtCore import QDate


LEAVE_TYPES = [
    ("CL", "Casual Leave"),
    ("SL", "Sick Leave"),
    ("EL", "Earned Leave"),
]


class LeaveForm(QDialog):
    """Apply / edit dialog for a single leave request.

    Pass ``record`` (a dict from the API) to edit; leave it ``None`` to apply.
    ``employees`` is the list of employee dicts used for the picker.
    """

    def __init__(self, api, employees, record=None, parent=None):

        super().__init__(parent)

        self.api = api

        self.employees = employees

        self.record = record

        self.is_edit = record is not None

        self.setWindowTitle(
            "Edit Leave" if self.is_edit else "Apply Leave"
        )

        self.resize(420, 420)

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

        self.leave_type = QComboBox()
        for value, label in LEAVE_TYPES:
            self.leave_type.addItem(label, value)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate())
        self.start_date.dateChanged.connect(self.update_days)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self.update_days)

        self.days_label = QLabel("1 day")
        self.days_label.setStyleSheet("color: gray;")

        self.reason = QPlainTextEdit()
        self.reason.setFixedHeight(80)

        form.addRow("Employee *", self.employee)
        form.addRow("Leave Type *", self.leave_type)
        form.addRow("Start Date *", self.start_date)
        form.addRow("End Date *", self.end_date)
        form.addRow("Duration", self.days_label)
        form.addRow("Reason *", self.reason)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton(
            "Update" if self.is_edit else "Apply"
        )
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)

        layout.addLayout(buttons)

        self.setLayout(layout)

        self.update_days()

    def update_days(self):

        start = self.start_date.date()
        end = self.end_date.date()

        days = start.daysTo(end) + 1

        if days < 1:
            self.days_label.setText("Invalid range")
        else:
            self.days_label.setText(f"{days} day(s)")

    def populate(self):

        rec = self.record

        index = self.employee.findData(rec.get("employee"))
        if index >= 0:
            self.employee.setCurrentIndex(index)

        type_index = self.leave_type.findData(rec.get("leave_type"))
        if type_index >= 0:
            self.leave_type.setCurrentIndex(type_index)

        if rec.get("start_date"):
            self.start_date.setDate(
                QDate.fromString(rec["start_date"], "yyyy-MM-dd")
            )

        if rec.get("end_date"):
            self.end_date.setDate(
                QDate.fromString(rec["end_date"], "yyyy-MM-dd")
            )

        self.reason.setPlainText(rec.get("reason", "") or "")

        self.update_days()

    def collect_payload(self):

        return {
            "employee": self.employee.currentData(),
            "leave_type": self.leave_type.currentData(),
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date.date().toString("yyyy-MM-dd"),
            "reason": self.reason.toPlainText().strip(),
        }

    def save(self):

        payload = self.collect_payload()

        if payload["employee"] is None:
            QMessageBox.warning(
                self, "Missing Information", "Please select an employee."
            )
            return

        if not payload["reason"]:
            QMessageBox.warning(
                self, "Missing Information", "Please provide a reason."
            )
            return

        if self.is_edit:
            ok, result = self.api.update_leave(self.record["id"], payload)
        else:
            ok, result = self.api.create_leave(payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Save Failed", str(result))
