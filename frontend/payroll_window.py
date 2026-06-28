from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox,
    QFileDialog,
    QDialog,
)

from PyQt6.QtCore import Qt, QTimer

from payroll_form import PayrollForm
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
    populate_employee_filter,
)


class PayslipHistoryDialog(QDialog):

    COLUMNS = ["Period", "Basic", "Allowances", "Deductions", "Net Salary"]

    def __init__(self, api, employee, parent=None):

        super().__init__(parent)

        self.api = api
        self.employee = employee
        self.records = []

        name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        self.setWindowTitle(f"Payslip History — {name}")
        self.resize(700, 420)

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        layout.addWidget(self.table)

        buttons = QHBoxLayout()

        download_button = QPushButton("Download Selected Payslip")
        download_button.clicked.connect(self.download_selected)
        buttons.addWidget(download_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)

        layout.addLayout(buttons)
        self.setLayout(layout)

        self.load_history()

    def load_history(self):

        with loading(self):
            self.records = self.api.get_employee_salary_history(self.employee["id"])

        if show_list_load_error(self, self.api, "payslip history"):
            return

        self.table.setRowCount(len(self.records))

        for row, record in enumerate(self.records):
            values = [
                record.get("period", ""),
                str(record.get("basic_salary", "")),
                str(record.get("allowances", "")),
                str(record.get("deductions", "")),
                str(record.get("net_salary", "")),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def selected_record(self):

        row = self.table.currentRow()
        if row < 0 or row >= len(self.records):
            return None
        return self.records[row]

    def download_selected(self):

        record = self.selected_record()
        if not record:
            QMessageBox.information(self, "No Selection", "Select a payslip record.")
            return

        default_name = (
            f"payslip_{self.employee.get('employee_code', 'employee')}_"
            f"{record.get('period', 'period')}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Payslip", default_name, "PDF (*.pdf)"
        )
        if not path:
            return

        ok, error = self.api.download_payslip(record["id"], path)
        if ok:
            QMessageBox.information(self, "Downloaded", f"Payslip saved to:\n{path}")
        else:
            QMessageBox.critical(self, "Download Failed", str(error))


class PayrollWindow(QWidget):

    COLUMNS = [
        "ID", "Code", "Employee", "Period",
        "Basic", "Allowances", "Deductions", "Net Salary",
    ]

    def __init__(self, api):

        super().__init__()

        self.api = api
        self.employees = []

        self.setWindowTitle("Payroll")
        self.resize(1100, 660)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_salaries)

        self.build_ui()
        self.load_employees()
        self.load_salaries()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Payroll Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by employee, code or period..."
        )
        self.search_input.textChanged.connect(lambda: self.search_timer.start())
        filter_row.addWidget(self.search_input)

        self.employee_filter = QComboBox()
        self.employee_filter.addItem("All Employees", None)
        self.employee_filter.currentIndexChanged.connect(self.load_salaries)
        filter_row.addWidget(self.employee_filter)

        layout.addLayout(filter_row)

        action_row = QHBoxLayout()

        self.add_button = QPushButton("Add Salary Record")
        self.add_button.clicked.connect(self.add_record)
        action_row.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_record)
        action_row.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_record)
        action_row.addWidget(self.delete_button)

        self.payslip_button = QPushButton("Download Payslip")
        self.payslip_button.clicked.connect(self.download_payslip)
        action_row.addWidget(self.payslip_button)

        self.history_button = QPushButton("Payslip History")
        self.history_button.clicked.connect(self.show_payslip_history)
        action_row.addWidget(self.history_button)

        action_row.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        action_row.addWidget(self.refresh_button)

        add_export_buttons(
            action_row, self, "payroll", lambda: self.COLUMNS, self._export_rows
        )

        # Only HR can create/modify payroll.
        can_manage = self.api.can("full_access")
        self.add_button.setVisible(can_manage)
        self.edit_button.setVisible(can_manage)
        self.delete_button.setVisible(can_manage)

        layout.addLayout(action_row)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.edit_record)

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

    def load_employees(self):
        with loading(self):
            self.employees = self.api.get_employees()
        if show_list_load_error(self, self.api, "employees"):
            return
        populate_employee_filter(self.employee_filter, self.employees)

    def build_filters(self):
        filters = {}
        search = self.search_input.text().strip()
        if search:
            filters["search"] = search
        employee = self.employee_filter.currentData()
        if employee:
            filters["employee"] = employee
        return filters

    def load_salaries(self):
        with loading(self):
            data = self.api.get_salaries(self.build_filters())
        if show_list_load_error(self, self.api, "salary records"):
            return
        self.pager.set_records(data, "record(s)")
        self.populate_table()

    def refresh_all(self):
        self.load_employees()
        self.load_salaries()

    def populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))
        for row, rec in enumerate(self.pager.page_records):
            values = [
                str(rec.get("id", "")),
                rec.get("employee_code", "") or "",
                rec.get("employee_name", "") or "",
                rec.get("period", "") or "",
                str(rec.get("basic_salary", "")),
                str(rec.get("allowances", "")),
                str(rec.get("deductions", "")),
                str(rec.get("net_salary", "")),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 3, 4, 5, 6, 7):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for rec in self.pager.all_records:
            rows.append([
                str(rec.get("id", "")),
                rec.get("employee_code", "") or "",
                rec.get("employee_name", "") or "",
                rec.get("period", "") or "",
                str(rec.get("basic_salary", "")),
                str(rec.get("allowances", "")),
                str(rec.get("deductions", "")),
                str(rec.get("net_salary", "")),
            ])
        return rows

    def selected_record(self):
        return self.pager.record_at_row(self.table.currentRow())

    def add_record(self):
        if not self.employees:
            QMessageBox.warning(
                self, "No Employees", "Add an employee before payroll."
            )
            return
        form = PayrollForm(self.api, self.employees, parent=self)
        if form.exec():
            self.load_salaries()

    def edit_record(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a record.")
            return
        form = PayrollForm(self.api, self.employees, record=rec, parent=self)
        if form.exec():
            self.load_salaries()

    def delete_record(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a record.")
            return
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete salary record for {rec.get('employee_name', '')} "
            f"({rec.get('period', '')})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, error = self.api.delete_salary(rec["id"])
        if ok:
            self.load_salaries()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))

    def download_payslip(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a record.")
            return

        default_name = (
            f"payslip_{rec.get('employee_code', 'employee')}_"
            f"{rec.get('period', 'period')}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Payslip", default_name, "PDF (*.pdf)"
        )
        if not path:
            return

        ok, error = self.api.download_payslip(rec["id"], path)
        if ok:
            QMessageBox.information(self, "Downloaded", f"Payslip saved to:\n{path}")
        else:
            QMessageBox.critical(self, "Download Failed", str(error))

    def show_payslip_history(self):

        employee_id = self.employee_filter.currentData()
        employee = None

        if employee_id:
            employee = next(
                (emp for emp in self.employees if emp["id"] == employee_id),
                None
            )

        if not employee:
            linked = (self.api.current_user or {}).get("employee")
            if linked:
                employee = {
                    "id": linked["id"],
                    "first_name": linked.get("name", "").split(" ")[0],
                    "last_name": " ".join(linked.get("name", "").split(" ")[1:]),
                    "employee_code": linked.get("employee_code", ""),
                }

        if not employee:
            QMessageBox.information(
                self,
                "Select Employee",
                "Choose an employee in the filter to view payslip history."
            )
            return

        dialog = PayslipHistoryDialog(self.api, employee, parent=self)
        dialog.exec()
