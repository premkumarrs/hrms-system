from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
)


class LookupForm(QDialog):
    """Add/Edit dialog for a single-field lookup (department or designation)."""

    def __init__(self, title, field_label, initial="", parent=None):

        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(360, 140)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.value_input = QLineEdit(initial or "")
        form.addRow(field_label, self.value_input)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self.accept)
        buttons.addWidget(save)

        layout.addLayout(buttons)
        self.setLayout(layout)

    def get_value(self):
        return self.value_input.text().strip()
