from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox
)

from PyQt6.QtCore import Qt, QTimer

from employee_form import EmployeeForm
from employee_profile_dialog import EmployeeProfileDialog
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
)


class EmployeeWindow(QWidget):

    COLUMNS = [
        "ID",
        "Code",
        "Name",
        "Email",
        "Phone",
        "Department",
        "Designation",
        "Status",
    ]

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.setWindowTitle("Employees")

        self.resize(1100, 650)

        # Debounce timer so we don't hit the API on every keystroke.
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_employees)

        self.build_ui()

        self.load_employees()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Employee Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Toolbar: search + action buttons
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by name, code, email or phone..."
        )
        self.search_input.textChanged.connect(self.on_search_changed)
        toolbar.addWidget(self.search_input)

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_employee)
        toolbar.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_employee)
        toolbar.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_employee)
        toolbar.addWidget(self.delete_button)

        self.profile_button = QPushButton("Profile / Details")
        self.profile_button.clicked.connect(self.open_profile)
        toolbar.addWidget(self.profile_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_employees)
        toolbar.addWidget(self.refresh_button)

        add_export_buttons(
            toolbar, self, "employees", lambda: self.COLUMNS, self._export_rows
        )

        # Only HR can create/modify employees.
        can_manage = self.api.can("manage_employees")
        self.add_button.setVisible(can_manage)
        self.edit_button.setVisible(can_manage)
        self.delete_button.setVisible(can_manage)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.edit_employee)

        setup_list_table(self.table, id_column=0, stretch_column=2)

        layout.addWidget(self.table)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        self.pager = TablePager(self.table, self.status_label)
        self.pagination_bar = build_pagination_bar(
            self.pager, self.populate_table
        )
        layout.addWidget(self.pagination_bar)

        self.setLayout(layout)

    def on_search_changed(self):
        # Restart the debounce timer on each keystroke.
        self.search_timer.start()

    def load_employees(self):

        search = self.search_input.text().strip()

        with loading(self):
            data = self.api.get_employees(search=search or None)

        if show_list_load_error(self, self.api, "employees"):
            return

        self.pager.set_records(data, "employee(s)")
        self.populate_table()

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, emp in enumerate(self.pager.page_records):

            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()

            values = [
                str(emp.get("id", "")),
                emp.get("employee_code", "") or "",
                name,
                emp.get("email", "") or "",
                emp.get("phone", "") or "",
                emp.get("department_name") or "-",
                emp.get("designation_title") or "-",
                emp.get("status", "") or "",
            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(value)

                if col == 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for emp in self.pager.all_records:
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            rows.append([
                str(emp.get("id", "")),
                emp.get("employee_code", "") or "",
                name,
                emp.get("email", "") or "",
                emp.get("phone", "") or "",
                emp.get("department_name") or "-",
                emp.get("designation_title") or "-",
                emp.get("status", "") or "",
            ])
        return rows

    def selected_employee(self):

        return self.pager.record_at_row(self.table.currentRow())

    def add_employee(self):

        form = EmployeeForm(self.api, parent=self)

        if form.exec():
            self.load_employees()

    def edit_employee(self):

        employee = self.selected_employee()

        if not employee:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select an employee to edit."
            )
            return

        form = EmployeeForm(self.api, employee=employee, parent=self)

        if form.exec():
            self.load_employees()

    def open_profile(self):

        employee = self.selected_employee()

        if not employee:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select an employee to view their profile."
            )
            return

        dialog = EmployeeProfileDialog(self.api, employee, parent=self)
        dialog.exec()

    def delete_employee(self):

        employee = self.selected_employee()

        if not employee:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select an employee to delete."
            )
            return

        name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete '{name}' ({employee.get('employee_code', '')})?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, error = self.api.delete_employee(employee["id"])

        if ok:
            self.load_employees()
        else:
            QMessageBox.critical(
                self,
                "Delete Failed",
                str(error)
            )
