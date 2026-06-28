from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QDateEdit,
    QSpinBox,
    QCheckBox,
    QPlainTextEdit,
    QPushButton,
    QMessageBox
)

from PyQt6.QtCore import QDate


EXIT_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("IN_PROGRESS", "In Progress"),
    ("COMPLETED", "Completed"),
]

SETTLEMENT_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("PROCESSED", "Processed"),
    ("PAID", "Paid"),
]


class ResignationForm(QDialog):
    """Add / edit dialog for a resignation / exit record."""

    def __init__(self, api, employees, record=None, parent=None):

        super().__init__(parent)

        self.api = api
        self.employees = employees
        self.record = record
        self.is_edit = record is not None

        self.setWindowTitle(
            "Edit Resignation" if self.is_edit else "Add Resignation"
        )

        self.resize(460, 480)

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

        self.resignation_date = QDateEdit()
        self.resignation_date.setCalendarPopup(True)
        self.resignation_date.setDisplayFormat("yyyy-MM-dd")
        self.resignation_date.setDate(QDate.currentDate())

        self.notice_period_days = QSpinBox()
        self.notice_period_days.setRange(0, 365)
        self.notice_period_days.setValue(30)

        self.lwd_enabled = QCheckBox("Set last working day")
        self.last_working_day = QDateEdit()
        self.last_working_day.setCalendarPopup(True)
        self.last_working_day.setDisplayFormat("yyyy-MM-dd")
        self.last_working_day.setDate(QDate.currentDate())
        self.last_working_day.setEnabled(False)
        self.lwd_enabled.toggled.connect(self.last_working_day.setEnabled)

        lwd_row = QHBoxLayout()
        lwd_row.addWidget(self.lwd_enabled)
        lwd_row.addWidget(self.last_working_day)

        self.exit_status = QComboBox()
        for value, label in EXIT_STATUS_CHOICES:
            self.exit_status.addItem(label, value)

        self.settlement_status = QComboBox()
        for value, label in SETTLEMENT_STATUS_CHOICES:
            self.settlement_status.addItem(label, value)

        self.reason = QPlainTextEdit()
        self.reason.setFixedHeight(70)

        form.addRow("Employee *", self.employee)
        form.addRow("Resignation Date *", self.resignation_date)
        form.addRow("Notice Period (days)", self.notice_period_days)
        form.addRow("Last Working Day", lwd_row)
        form.addRow("Exit Status", self.exit_status)
        form.addRow("Settlement Status", self.settlement_status)
        form.addRow("Reason", self.reason)

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

        if rec.get("resignation_date"):
            self.resignation_date.setDate(
                QDate.fromString(rec["resignation_date"], "yyyy-MM-dd")
            )

        self.notice_period_days.setValue(
            int(rec.get("notice_period_days") or 30)
        )

        if rec.get("last_working_day"):
            self.lwd_enabled.setChecked(True)
            self.last_working_day.setEnabled(True)
            self.last_working_day.setDate(
                QDate.fromString(rec["last_working_day"], "yyyy-MM-dd")
            )

        exit_index = self.exit_status.findData(rec.get("exit_status"))
        if exit_index >= 0:
            self.exit_status.setCurrentIndex(exit_index)

        settle_index = self.settlement_status.findData(
            rec.get("final_settlement_status")
        )
        if settle_index >= 0:
            self.settlement_status.setCurrentIndex(settle_index)

        self.reason.setPlainText(rec.get("reason", "") or "")

    def collect_payload(self):

        payload = {
            "employee": self.employee.currentData(),
            "resignation_date": self.resignation_date.date().toString("yyyy-MM-dd"),
            "notice_period_days": self.notice_period_days.value(),
            "exit_status": self.exit_status.currentData(),
            "final_settlement_status": self.settlement_status.currentData(),
            "reason": self.reason.toPlainText().strip(),
        }

        if self.lwd_enabled.isChecked():
            payload["last_working_day"] = (
                self.last_working_day.date().toString("yyyy-MM-dd")
            )
        else:
            payload["last_working_day"] = None

        return payload

    def save(self):

        payload = self.collect_payload()

        if payload["employee"] is None:
            QMessageBox.warning(
                self, "Missing Information", "Please select an employee."
            )
            return

        if self.is_edit:
            ok, result = self.api.update_resignation(self.record["id"], payload)
        else:
            ok, result = self.api.create_resignation(payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Save Failed", str(result))
