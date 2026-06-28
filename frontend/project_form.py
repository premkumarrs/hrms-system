from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QCheckBox,
    QPlainTextEdit,
    QPushButton,
    QMessageBox
)

from PyQt6.QtCore import QDate


STATUS_CHOICES = [
    ("ACTIVE", "Active"),
    ("COMPLETED", "Completed"),
]


class ProjectForm(QDialog):
    """Add / edit dialog for a single project.

    Pass ``project`` (a dict from the API) to edit; leave it ``None`` to add.
    """

    def __init__(self, api, project=None, parent=None):

        super().__init__(parent)

        self.api = api

        self.project = project

        self.is_edit = project is not None

        self.setWindowTitle(
            "Edit Project" if self.is_edit else "Add Project"
        )

        self.resize(440, 460)

        self.build_ui()

        if self.is_edit:
            self.populate()

    def build_ui(self):

        layout = QVBoxLayout()

        form = QFormLayout()

        self.name = QLineEdit()
        self.client = QLineEdit()

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate())

        self.end_enabled = QCheckBox("Set end date")
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setEnabled(False)
        self.end_enabled.toggled.connect(self.end_date.setEnabled)

        end_row = QHBoxLayout()
        end_row.addWidget(self.end_enabled)
        end_row.addWidget(self.end_date)

        self.status = QComboBox()
        for value, label in STATUS_CHOICES:
            self.status.addItem(label, value)

        self.description = QPlainTextEdit()
        self.description.setFixedHeight(90)

        form.addRow("Name *", self.name)
        form.addRow("Client *", self.client)
        form.addRow("Start Date *", self.start_date)
        form.addRow("End Date", end_row)
        form.addRow("Status", self.status)
        form.addRow("Description", self.description)

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

        proj = self.project

        self.name.setText(proj.get("name", ""))
        self.client.setText(proj.get("client", ""))

        if proj.get("start_date"):
            self.start_date.setDate(
                QDate.fromString(proj["start_date"], "yyyy-MM-dd")
            )

        if proj.get("end_date"):
            self.end_enabled.setChecked(True)
            self.end_date.setEnabled(True)
            self.end_date.setDate(
                QDate.fromString(proj["end_date"], "yyyy-MM-dd")
            )

        status_index = self.status.findData(proj.get("status"))
        if status_index >= 0:
            self.status.setCurrentIndex(status_index)

        self.description.setPlainText(proj.get("description", "") or "")

    def collect_payload(self):

        payload = {
            "name": self.name.text().strip(),
            "client": self.client.text().strip(),
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),
            "status": self.status.currentData(),
            "description": self.description.toPlainText().strip(),
        }

        if self.end_enabled.isChecked():
            payload["end_date"] = self.end_date.date().toString("yyyy-MM-dd")
        else:
            payload["end_date"] = None

        return payload

    def save(self):

        payload = self.collect_payload()

        if not payload["name"] or not payload["client"]:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Name and client are required."
            )
            return

        if self.is_edit:
            ok, result = self.api.update_project(self.project["id"], payload)
        else:
            ok, result = self.api.create_project(payload)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Save Failed", str(result))
