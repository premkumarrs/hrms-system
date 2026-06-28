from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMessageBox
)

from PyQt6.QtCore import Qt


class FieldDialog(QDialog):
    """Generic add/edit dialog driven by a field specification.

    ``fields`` is a list of (key, label, kind) where kind is one of
    'text', 'multiline'.
    """

    def __init__(self, title, fields, initial=None, parent=None):

        super().__init__(parent)

        self.fields = fields
        self.widgets = {}
        initial = initial or {}

        self.setWindowTitle(title)
        self.resize(380, 320)

        layout = QVBoxLayout()
        form = QFormLayout()

        for key, label, kind in fields:
            value = "" if initial.get(key) is None else str(initial.get(key))
            if kind == 'multiline':
                widget = QPlainTextEdit()
                widget.setFixedHeight(60)
                widget.setPlainText(value)
            else:
                widget = QLineEdit()
                widget.setText(value)
            self.widgets[key] = widget
            form.addRow(label, widget)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self.accept)

        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def get_data(self):
        data = {}
        for key, _, kind in self.fields:
            widget = self.widgets[key]
            if kind == 'multiline':
                data[key] = widget.toPlainText().strip()
            else:
                data[key] = widget.text().strip()
        return data


class _ListTab(QWidget):
    """A table tab supporting multiple records (Education, Emergency)."""

    def __init__(self, api, employee_id, can_manage, columns, field_spec,
                 fetch, create, update, delete, label):

        super().__init__()

        self.api = api
        self.employee_id = employee_id
        self.can_manage = can_manage
        self.columns = columns
        self.field_spec = field_spec
        self.fetch = fetch
        self.create = create
        self.update = update
        self.delete = delete
        self.label = label
        self.records = []

        layout = QVBoxLayout()

        button_row = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_record)
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_record)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_record)
        button_row.addWidget(self.add_button)
        button_row.addWidget(self.edit_button)
        button_row.addWidget(self.delete_button)
        button_row.addStretch()

        for btn in (self.add_button, self.edit_button, self.delete_button):
            btn.setVisible(can_manage)

        layout.addLayout(button_row)

        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.doubleClicked.connect(self.edit_record)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.load()

    def load(self):
        self.records = self.fetch(self.employee_id)
        self.table.setRowCount(len(self.records))
        for row, rec in enumerate(self.records):
            for col, (key, _, _) in enumerate(self.field_spec):
                value = rec.get(key)
                self.table.setItem(
                    row, col, QTableWidgetItem("" if value is None else str(value))
                )

    def selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.records):
            return None
        return self.records[row]

    def add_record(self):
        dialog = FieldDialog(f"Add {self.label}", self.field_spec, parent=self)
        if not dialog.exec():
            return
        payload = dialog.get_data()
        payload["employee"] = self.employee_id
        ok, result = self.create(payload)
        if ok:
            self.load()
        else:
            QMessageBox.critical(self, "Save Failed", str(result))

    def edit_record(self):
        rec = self.selected()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a row to edit.")
            return
        dialog = FieldDialog(
            f"Edit {self.label}", self.field_spec, initial=rec, parent=self
        )
        if not dialog.exec():
            return
        payload = dialog.get_data()
        payload["employee"] = self.employee_id
        ok, result = self.update(rec["id"], payload)
        if ok:
            self.load()
        else:
            QMessageBox.critical(self, "Save Failed", str(result))

    def delete_record(self):
        rec = self.selected()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a row to delete.")
            return
        confirm = QMessageBox.question(
            self, "Confirm Delete", f"Delete this {self.label.lower()} record?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, error = self.delete(rec["id"])
        if ok:
            self.load()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))


class _SingleTab(QWidget):
    """A single-record (O2O) form tab (Bank, ID Proof)."""

    def __init__(self, api, employee_id, can_manage, field_spec,
                 fetch, create, update, delete=None, label="Record"):

        super().__init__()

        self.api = api
        self.employee_id = employee_id
        self.field_spec = field_spec
        self.fetch = fetch
        self.create = create
        self.update = update
        self.delete = delete
        self.label = label
        self.can_manage = can_manage
        self.record = None
        self.widgets = {}

        layout = QVBoxLayout()
        form = QFormLayout()

        for key, lbl, _ in field_spec:
            widget = QLineEdit()
            self.widgets[key] = widget
            form.addRow(lbl, widget)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.delete_button = QPushButton(f"Delete {label}")
        self.delete_button.clicked.connect(self.delete_record)
        self.delete_button.setVisible(can_manage and delete is not None)
        button_row.addWidget(self.delete_button)
        self.save_button = QPushButton(f"Save {label}")
        self.save_button.clicked.connect(self.save)
        self.save_button.setVisible(can_manage)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

        layout.addStretch()
        self.setLayout(layout)

        self.load()

    def load(self):
        records = self.fetch(self.employee_id)
        self.record = records[0] if records else None
        for key, _, _ in self.field_spec:
            value = self.record.get(key) if self.record else ""
            self.widgets[key].setText("" if value is None else str(value))

    def save(self):
        payload = {key: self.widgets[key].text().strip()
                   for key, _, _ in self.field_spec}
        payload["employee"] = self.employee_id

        if self.record:
            ok, result = self.update(self.record["id"], payload)
        else:
            ok, result = self.create(payload)

        if ok:
            self.record = result
            QMessageBox.information(self, "Saved", f"{self.label} saved.")
        else:
            QMessageBox.critical(self, "Save Failed", str(result))

    def delete_record(self):
        if not self.record or not self.delete:
            QMessageBox.information(
                self, "No Record", f"No {self.label.lower()} record to delete."
            )
            return
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete {self.label.lower()} for this employee?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, error = self.delete(self.record["id"])
        if ok:
            self.record = None
            for key, _, _ in self.field_spec:
                self.widgets[key].clear()
            QMessageBox.information(self, "Deleted", f"{self.label} deleted.")
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))


class EmployeeProfileDialog(QDialog):
    """Tabbed editor for an employee's extended information."""

    def __init__(self, api, employee, parent=None):

        super().__init__(parent)

        self.api = api
        self.employee = employee
        employee_id = employee["id"]
        can_manage = api.can("manage_employees")

        name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        self.setWindowTitle(f"Employee Profile — {name}")
        self.resize(720, 480)

        layout = QVBoxLayout()

        heading = QLabel(f"{name}  ({employee.get('employee_code', '')})")
        heading.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(heading)

        tabs = QTabWidget()

        # Education (multiple)
        tabs.addTab(
            _ListTab(
                api, employee_id, can_manage,
                columns=["Degree", "College", "University", "Year", "%"],
                field_spec=[
                    ("degree", "Degree *", "text"),
                    ("institution", "College *", "text"),
                    ("university", "University", "text"),
                    ("year_of_passing", "Year *", "text"),
                    ("percentage", "Percentage *", "text"),
                ],
                fetch=api.get_education,
                create=api.create_education,
                update=api.update_education,
                delete=api.delete_education,
                label="Education",
            ),
            "Education"
        )

        # Bank (single)
        tabs.addTab(
            _SingleTab(
                api, employee_id, can_manage,
                field_spec=[
                    ("bank_name", "Bank Name", "text"),
                    ("branch", "Branch", "text"),
                    ("account_number", "Account Number", "text"),
                    ("ifsc_code", "IFSC", "text"),
                ],
                fetch=api.get_bank_details,
                create=api.create_bank_details,
                update=api.update_bank_details,
                delete=api.delete_bank_details,
                label="Bank Details",
            ),
            "Bank"
        )

        # ID Proof (single)
        tabs.addTab(
            _SingleTab(
                api, employee_id, can_manage,
                field_spec=[
                    ("aadhaar_number", "Aadhaar", "text"),
                    ("pan_number", "PAN", "text"),
                    ("passport_number", "Passport", "text"),
                    ("driving_license", "Driving License", "text"),
                ],
                fetch=api.get_id_proofs,
                create=api.create_id_proof,
                update=api.update_id_proof,
                delete=api.delete_id_proof,
                label="ID Proof",
            ),
            "ID Proof"
        )

        # Emergency contacts (multiple)
        tabs.addTab(
            _ListTab(
                api, employee_id, can_manage,
                columns=["Name", "Relationship", "Phone", "Address"],
                field_spec=[
                    ("contact_name", "Contact Name *", "text"),
                    ("relationship", "Relationship *", "text"),
                    ("phone", "Phone *", "text"),
                    ("address", "Address", "multiline"),
                ],
                fetch=api.get_emergency_contacts,
                create=api.create_emergency_contact,
                update=api.update_emergency_contact,
                delete=api.delete_emergency_contact,
                label="Emergency Contact",
            ),
            "Emergency Contacts"
        )

        layout.addWidget(tabs)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

        self.setLayout(layout)
