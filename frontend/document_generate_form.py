from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QMessageBox,
)

from document_letter_types import LETTER_TYPE_CHOICES


class DocumentGenerateForm(QDialog):
    """Generate an HR letter PDF for an employee."""

    def __init__(self, api, employees, parent=None):

        super().__init__(parent)

        self.api = api
        self.employees = employees
        self.generated = None

        self.setWindowTitle("Generate HR Letter")
        self.resize(480, 320)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout()
        form = QFormLayout()

        self.employee = QComboBox()
        for emp in self.employees:
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            label = f"{name} ({emp.get('employee_code', '')})"
            self.employee.addItem(label, emp["id"])

        self.letter_type = QComboBox()
        for label, value in LETTER_TYPE_CHOICES:
            self.letter_type.addItem(label, value)
        self.letter_type.currentIndexChanged.connect(self.on_type_changed)

        self.new_designation = QLineEdit()
        self.new_designation.setPlaceholderText("Required for promotion letters")

        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText("Reason or details (for warning letters)")
        self.notes.setFixedHeight(80)

        form.addRow("Employee *", self.employee)
        form.addRow("Letter Type *", self.letter_type)
        form.addRow("New Designation", self.new_designation)
        form.addRow("Notes", self.notes)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        self.generate_button = QPushButton("Generate")
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self.generate)

        buttons.addWidget(cancel_button)
        buttons.addWidget(self.generate_button)

        layout.addLayout(buttons)
        self.setLayout(layout)

        self.on_type_changed()

    def on_type_changed(self):

        letter_type = self.letter_type.currentData()
        self.new_designation.setEnabled(letter_type == "promotion")
        self.notes.setEnabled(letter_type == "warning")

    def generate(self):

        employee_id = self.employee.currentData()
        letter_type = self.letter_type.currentData()

        if employee_id is None:
            QMessageBox.warning(
                self, "Missing Information", "Please select an employee."
            )
            return

        payload = {
            "employee": employee_id,
            "letter_type": letter_type,
        }

        if letter_type == "warning":
            payload["notes"] = self.notes.toPlainText().strip()

        if letter_type == "promotion":
            designation = self.new_designation.text().strip()
            if not designation:
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    "Please enter the new designation for the promotion letter.",
                )
                return
            payload["new_designation"] = designation

        ok, result = self.api.generate_letter(payload)

        if ok:
            self.generated = result
            self.accept()
        else:
            QMessageBox.critical(self, "Generation Failed", str(result))
