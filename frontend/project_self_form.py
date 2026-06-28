from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QHBoxLayout,
    QPushButton,
)


class ProjectSelfUpdateForm(QDialog):

    def __init__(self, allocation, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Update Project Details")
        self.resize(460, 320)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.role_input = QLineEdit(allocation.get("role", "") or "")
        self.responsibilities_input = QPlainTextEdit(
            allocation.get("responsibilities", "") or ""
        )
        self.responsibilities_input.setFixedHeight(80)
        self.notes_input = QPlainTextEdit(allocation.get("notes", "") or "")
        self.notes_input.setFixedHeight(80)

        form.addRow("Role", self.role_input)
        form.addRow("Responsibilities", self.responsibilities_input)
        form.addRow("Notes", self.notes_input)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def get_payload(self):
        return {
            "role": self.role_input.text().strip(),
            "responsibilities": self.responsibilities_input.toPlainText().strip(),
            "notes": self.notes_input.toPlainText().strip(),
        }
