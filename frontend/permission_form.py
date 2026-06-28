from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QDateEdit,
    QTimeEdit,
    QPlainTextEdit,
    QPushButton,
    QMessageBox
)

from PyQt6.QtCore import QDate, QTime


class PermissionForm(QDialog):
    """Apply / edit dialog for a short time-off permission request."""

    def __init__(self, api, employees, record=None, parent=None):

        super().__init__(parent)

        self.api = api
        self.employees = employees
        self.record = record
        self.is_edit = record is not None

        self.setWindowTitle(
            "Edit Permission" if self.is_edit else "Apply Permission"
        )
        self.resize(420, 360)

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

        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setDate(QDate.currentDate())

        self.from_time = QTimeEdit()
        self.from_time.setDisplayFormat("HH:mm")
        self.from_time.setTime(QTime(10, 0))

        self.to_time = QTimeEdit()
        self.to_time.setDisplayFormat("HH:mm")
        self.to_time.setTime(QTime(11, 0))

        self.reason = QPlainTextEdit()
        self.reason.setFixedHeight(80)

        form.addRow("Employee *", self.employee)
        form.addRow("Date *", self.date)
        form.addRow("From *", self.from_time)
        form.addRow("To *", self.to_time)
        form.addRow("Reason *", self.reason)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        self.save_button = QPushButton("Update" if self.is_edit else "Apply")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)

        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def populate(self):

        rec = self.record

        index = self.employee.findData(rec.get("employee"))
        if index >= 0:
            self.employee.setCurrentIndex(index)

        if rec.get("date"):
            self.date.setDate(QDate.fromString(rec["date"], "yyyy-MM-dd"))

        if rec.get("from_time"):
            self.from_time.setTime(
                QTime.fromString(rec["from_time"][:5], "HH:mm")
            )

        if rec.get("to_time"):
            self.to_time.setTime(
                QTime.fromString(rec["to_time"][:5], "HH:mm")
            )

        self.reason.setPlainText(rec.get("reason", "") or "")

    def collect_payload(self):
        return {
            "employee": self.employee.currentData(),
            "date": self.date.date().toString("yyyy-MM-dd"),
            "from_time": self.from_time.time().toString("HH:mm"),
            "to_time": self.to_time.time().toString("HH:mm"),
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
            ok, result = self.api.update_permission(self.record["id"], payload)
        else:
            ok, result = self.api.create_permission(payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Save Failed", str(result))
