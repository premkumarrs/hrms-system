from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView
)

from PyQt6.QtCore import Qt, QTimer

from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
)


class EmployeeDetailDialog(QDialog):
    """Read-only detail card for a single directory entry."""

    def __init__(self, employee, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Employee Details")
        self.resize(420, 360)

        layout = QVBoxLayout()

        name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        heading = QLabel(name)
        heading.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(heading)

        form = QFormLayout()

        fields = [
            ("Employee ID", employee.get("employee_code")),
            ("Department", employee.get("department_name")),
            ("Designation", employee.get("designation_title")),
            ("Manager", employee.get("manager_name")),
            ("Branch", employee.get("branch")),
            ("Contact Number", employee.get("phone")),
            ("Official Email", employee.get("email")),
            ("Status", employee.get("status")),
        ]

        for label, value in fields:
            form.addRow(QLabel(f"{label}:"), QLabel(str(value or "-")))

        layout.addLayout(form)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)


class DirectoryWindow(QWidget):
    """Read-only, searchable employee directory."""

    COLUMNS = [
        "Employee ID",
        "Name",
        "Department",
        "Designation",
        "Manager",
        "Branch",
        "Contact",
        "Official Email",
    ]

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.departments = []

        self.setWindowTitle("Employee Directory")

        self.resize(1150, 660)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_directory)

        self.build_ui()

        self.load_departments()

        self.load_directory()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Employee Directory")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # --- Filter / search row ---
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by name, code, email or phone..."
        )
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_row.addWidget(self.search_input)

        self.department_filter = QComboBox()
        self.department_filter.addItem("All Departments", None)
        self.department_filter.currentIndexChanged.connect(self.load_directory)
        filter_row.addWidget(self.department_filter)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        filter_row.addWidget(self.refresh_button)

        add_export_buttons(
            filter_row, self, "directory", lambda: self.COLUMNS, self._export_rows
        )

        layout.addLayout(filter_row)

        # --- Table (read-only) ---
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
        self.table.doubleClicked.connect(self.view_details)

        setup_list_table(self.table, id_column=None, stretch_column=1)

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

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_departments(self):

        with loading(self):
            self.departments = self.api.get_departments()

        if show_list_load_error(self, self.api, "departments"):
            return

        self.department_filter.blockSignals(True)
        self.department_filter.clear()
        self.department_filter.addItem("All Departments", None)
        for dept in self.departments:
            self.department_filter.addItem(dept["name"], dept["id"])
        self.department_filter.blockSignals(False)

    def load_directory(self):

        search = self.search_input.text().strip() or None
        department = self.department_filter.currentData()

        with loading(self):
            data = self.api.get_employees(
                search=search,
                department=department
            )

        if show_list_load_error(self, self.api, "directory entries"):
            return

        self.pager.set_records(data, "employee(s)")
        self.populate_table()

    def refresh_all(self):
        self.load_departments()
        self.load_directory()

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, emp in enumerate(self.pager.page_records):

            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()

            values = [
                emp.get("employee_code", "") or "",
                name,
                emp.get("department_name") or "-",
                emp.get("designation_title") or "-",
                emp.get("manager_name") or "-",
                emp.get("branch") or "-",
                emp.get("phone", "") or "",
                emp.get("email", "") or "",
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for emp in self.pager.all_records:
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            rows.append([
                emp.get("employee_code", "") or "",
                name,
                emp.get("department_name") or "-",
                emp.get("designation_title") or "-",
                emp.get("manager_name") or "-",
                emp.get("branch") or "-",
                emp.get("phone", "") or "",
                emp.get("email", "") or "",
            ])
        return rows

    def on_search_changed(self):
        self.search_timer.start()

    def view_details(self):

        employee = self.pager.record_at_row(self.table.currentRow())

        if not employee:
            return

        dialog = EmployeeDetailDialog(employee, parent=self)
        dialog.exec()
