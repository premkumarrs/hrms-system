import os

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox
)


class DocumentUploadForm(QDialog):
    """Upload a document for an employee."""

    def __init__(self, api, employees, categories, parent=None):

        super().__init__(parent)

        self.api = api

        self.employees = employees

        self.categories = categories

        self.file_path = None

        self.setWindowTitle("Upload Document")

        self.resize(440, 260)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout()

        form = QFormLayout()

        self.employee = QComboBox()
        for emp in self.employees:
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            label = f"{name} ({emp.get('employee_code', '')})"
            self.employee.addItem(label, emp["id"])

        self.category = QComboBox()
        self.category.addItem("-- None --", None)
        for cat in self.categories:
            self.category.addItem(cat["name"], cat["id"])

        self.title = QLineEdit()

        # File picker row
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: gray;")

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse)

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_label)
        file_row.addStretch()
        file_row.addWidget(browse_button)

        form.addRow("Employee *", self.employee)
        form.addRow("Category", self.category)
        form.addRow("Title *", self.title)
        form.addRow("File *", file_row)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Upload")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)

        layout.addLayout(buttons)

        self.setLayout(layout)

    def browse(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document",
            "",
            "Documents (*.pdf *.doc *.docx *.png *.jpg *.jpeg *.txt);;All Files (*.*)"
        )

        if path:
            self.file_path = path
            self.file_label.setText(os.path.basename(path))
            self.file_label.setStyleSheet("color: white;")

            if not self.title.text().strip():
                base = os.path.splitext(os.path.basename(path))[0]
                self.title.setText(base)

    def save(self):

        employee_id = self.employee.currentData()
        title = self.title.text().strip()

        if employee_id is None:
            QMessageBox.warning(
                self, "Missing Information", "Please select an employee."
            )
            return

        if not title:
            QMessageBox.warning(
                self, "Missing Information", "Please provide a title."
            )
            return

        if not self.file_path:
            QMessageBox.warning(
                self, "Missing File", "Please choose a file to upload."
            )
            return

        ok, result = self.api.upload_document(
            employee_id,
            title,
            self.file_path,
            self.category.currentData()
        )

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Upload Failed", str(result))
