from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QDoubleSpinBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QMessageBox
)

from PyQt6.QtCore import QDate


class PayrollForm(QDialog):
    """Add / edit dialog for a monthly salary record."""

    def __init__(self, api, employees, record=None, parent=None):

        super().__init__(parent)

        self.api = api
        self.employees = employees
        self.record = record
        self.is_edit = record is not None

        self.setWindowTitle(
            "Edit Salary Record" if self.is_edit else "Add Salary Record"
        )
        self.resize(420, 420)

        self.build_ui()

        if self.is_edit:
            self.populate()

        self.update_net()

    def build_ui(self):

        layout = QVBoxLayout()
        form = QFormLayout()

        self.employee = QComboBox()
        for emp in self.employees:
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            self.employee.addItem(
                f"{name} ({emp.get('employee_code', '')})", emp["id"]
            )

        self.period = QLineEdit()
        self.period.setPlaceholderText("YYYY-MM (e.g. 2026-06)")
        self.period.setText(QDate.currentDate().toString("yyyy-MM"))

        self.basic_salary = self._money()
        self.allowances = self._money()
        self.deductions = self._money()

        self.basic_salary.valueChanged.connect(self.update_net)
        self.allowances.valueChanged.connect(self.update_net)
        self.deductions.valueChanged.connect(self.update_net)

        self.net_label = QLabel("0.00")
        self.net_label.setStyleSheet("font-weight: bold;")

        self.remarks = QPlainTextEdit()
        self.remarks.setFixedHeight(60)

        form.addRow("Employee *", self.employee)
        form.addRow("Period *", self.period)
        form.addRow("Basic Salary", self.basic_salary)
        form.addRow("Allowances", self.allowances)
        form.addRow("Deductions", self.deductions)
        form.addRow("Net Salary", self.net_label)
        form.addRow("Remarks", self.remarks)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        self.save_button = QPushButton("Update" if self.is_edit else "Create")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)

        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def _money(self):
        spin = QDoubleSpinBox()
        spin.setRange(0, 10_000_000)
        spin.setDecimals(2)
        spin.setSingleStep(1000)
        return spin

    def update_net(self):
        net = (
            self.basic_salary.value()
            + self.allowances.value()
            - self.deductions.value()
        )
        self.net_label.setText(f"{net:.2f}")

    def populate(self):
        rec = self.record
        index = self.employee.findData(rec.get("employee"))
        if index >= 0:
            self.employee.setCurrentIndex(index)
        self.period.setText(rec.get("period", ""))
        self.basic_salary.setValue(float(rec.get("basic_salary") or 0))
        self.allowances.setValue(float(rec.get("allowances") or 0))
        self.deductions.setValue(float(rec.get("deductions") or 0))
        self.remarks.setPlainText(rec.get("remarks", "") or "")

    def collect_payload(self):
        return {
            "employee": self.employee.currentData(),
            "period": self.period.text().strip(),
            "basic_salary": self.basic_salary.value(),
            "allowances": self.allowances.value(),
            "deductions": self.deductions.value(),
            "remarks": self.remarks.toPlainText().strip(),
        }

    def save(self):
        payload = self.collect_payload()

        if payload["employee"] is None:
            QMessageBox.warning(
                self, "Missing Information", "Please select an employee."
            )
            return

        if not payload["period"]:
            QMessageBox.warning(
                self, "Missing Information", "Please enter a pay period."
            )
            return

        if self.is_edit:
            ok, result = self.api.update_salary(self.record["id"], payload)
        else:
            ok, result = self.api.create_salary(payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Save Failed", str(result))
