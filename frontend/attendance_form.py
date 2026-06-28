from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QDateEdit,
    QTimeEdit,
    QCheckBox,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QMessageBox
)

from PyQt6.QtCore import QDate, QTime


STATUS_CHOICES = [
    ("PRESENT", "Present"),
    ("ABSENT", "Absent"),
    ("HALF_DAY", "Half Day"),
    ("LEAVE", "Leave"),
]


class AttendanceForm(QDialog):
    """Add / edit dialog for a single attendance record.

    Pass ``record`` (a dict from the API) to edit; leave it ``None`` to add.
    ``employees`` is the list of employee dicts used for the picker.
    """

    def __init__(self, api, employees, record=None, parent=None):

        super().__init__(parent)

        self.api = api

        self.employees = employees

        self.record = record

        self.is_edit = record is not None

        self.setWindowTitle(
            "Edit Attendance" if self.is_edit else "Add Attendance"
        )

        self.resize(420, 480)

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

        self.check_in = QTimeEdit()
        self.check_in.setDisplayFormat("HH:mm")
        self.check_in.setTime(QTime(9, 30))

        # Check-out is optional; the checkbox controls whether it is sent.
        self.checkout_enabled = QCheckBox("Set check-out time")
        self.check_out = QTimeEdit()
        self.check_out.setDisplayFormat("HH:mm")
        self.check_out.setTime(QTime(18, 30))
        self.check_out.setEnabled(False)
        self.checkout_enabled.toggled.connect(self.check_out.setEnabled)

        checkout_row = QHBoxLayout()
        checkout_row.addWidget(self.checkout_enabled)
        checkout_row.addWidget(self.check_out)

        self.status = QComboBox()
        for value, label in STATUS_CHOICES:
            self.status.addItem(label, value)

        self.remarks = QPlainTextEdit()
        self.remarks.setFixedHeight(70)

        form.addRow("Employee *", self.employee)
        form.addRow("Date *", self.date)
        form.addRow("Check In *", self.check_in)
        form.addRow("Check Out", checkout_row)
        form.addRow("Status", self.status)
        form.addRow("Remarks", self.remarks)

        layout.addLayout(form)

        hint = QLabel(
            "Working hours & late flag are calculated automatically."
        )
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

        rec = self.record

        index = self.employee.findData(rec.get("employee"))
        if index >= 0:
            self.employee.setCurrentIndex(index)

        if rec.get("date"):
            self.date.setDate(
                QDate.fromString(rec["date"], "yyyy-MM-dd")
            )

        if rec.get("check_in"):
            self.check_in.setTime(
                QTime.fromString(rec["check_in"][:5], "HH:mm")
            )

        if rec.get("check_out"):
            self.checkout_enabled.setChecked(True)
            self.check_out.setEnabled(True)
            self.check_out.setTime(
                QTime.fromString(rec["check_out"][:5], "HH:mm")
            )

        status_index = self.status.findData(rec.get("status"))
        if status_index >= 0:
            self.status.setCurrentIndex(status_index)

        self.remarks.setPlainText(rec.get("remarks", "") or "")

    def collect_payload(self):

        payload = {
            "employee": self.employee.currentData(),
            "date": self.date.date().toString("yyyy-MM-dd"),
            "check_in": self.check_in.time().toString("HH:mm"),
            "status": self.status.currentData(),
            "remarks": self.remarks.toPlainText().strip(),
        }

        if self.checkout_enabled.isChecked():
            payload["check_out"] = self.check_out.time().toString("HH:mm")
        else:
            payload["check_out"] = None

        return payload

    def save(self):

        payload = self.collect_payload()

        if payload["employee"] is None:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please select an employee."
            )
            return

        if self.is_edit:
            ok, result = self.api.update_attendance(
                self.record["id"],
                payload
            )
        else:
            ok, result = self.api.create_attendance(payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Save Failed",
                str(result)
            )
