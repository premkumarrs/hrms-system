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
    QMessageBox
)

from PyQt6.QtCore import Qt, QTimer

from permission_form import PermissionForm
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
    populate_employee_filter,
)


STATUS_FILTERS = [
    ("All Statuses", None),
    ("Pending", "PENDING"),
    ("Approved", "APPROVED"),
    ("Rejected", "REJECTED"),
]


class PermissionWindow(QWidget):

    COLUMNS = [
        "ID", "Code", "Employee", "Date",
        "From", "To", "Status", "Approved By",
    ]

    def __init__(self, api):

        super().__init__()

        self.api = api
        self.employees = []

        self.setWindowTitle("Permission Management")
        self.resize(1100, 660)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_permissions)

        self.build_ui()
        self.load_employees()
        self.load_permissions()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Permission Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by employee, code or reason..."
        )
        self.search_input.textChanged.connect(lambda: self.search_timer.start())
        filter_row.addWidget(self.search_input)

        self.employee_filter = QComboBox()
        self.employee_filter.addItem("All Employees", None)
        self.employee_filter.currentIndexChanged.connect(self.load_permissions)
        filter_row.addWidget(self.employee_filter)

        self.status_filter = QComboBox()
        for label, value in STATUS_FILTERS:
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self.load_permissions)
        filter_row.addWidget(self.status_filter)

        layout.addLayout(filter_row)

        action_row = QHBoxLayout()

        self.apply_button = QPushButton("Apply Permission")
        self.apply_button.clicked.connect(self.apply_permission)
        action_row.addWidget(self.apply_button)

        self.approve_button = QPushButton("Approve")
        self.approve_button.clicked.connect(lambda: self._decide(True))
        action_row.addWidget(self.approve_button)

        self.reject_button = QPushButton("Reject")
        self.reject_button.clicked.connect(lambda: self._decide(False))
        action_row.addWidget(self.reject_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_permission)
        action_row.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_permission)
        action_row.addWidget(self.delete_button)

        action_row.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        action_row.addWidget(self.refresh_button)

        add_export_buttons(
            action_row, self, "permissions", lambda: self.COLUMNS, self._export_rows
        )

        # Approval is restricted to Managers / HR.
        can_approve = self.api.can("approve_leave")
        self.approve_button.setVisible(can_approve)
        self.reject_button.setVisible(can_approve)

        can_manage = self.api.can("approve_leave")
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
        if can_manage:
            self.table.doubleClicked.connect(self.edit_permission)

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
        status = self.status_filter.currentData()
        if status:
            filters["status"] = status
        return filters

    def load_permissions(self):
        with loading(self):
            data = self.api.get_permissions(self.build_filters())
        if show_list_load_error(self, self.api, "permission requests"):
            return
        self.pager.set_records(data, "request(s)")
        self.populate_table()

    def refresh_all(self):
        self.load_employees()
        self.load_permissions()

    def populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))
        for row, rec in enumerate(self.pager.page_records):
            values = [
                str(rec.get("id", "")),
                rec.get("employee_code", "") or "",
                rec.get("employee_name", "") or "",
                rec.get("date", "") or "",
                (rec.get("from_time") or "")[:5],
                (rec.get("to_time") or "")[:5],
                rec.get("status_display") or rec.get("status", ""),
                rec.get("approved_by_name") or "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 3, 4, 5, 6):
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
                rec.get("date", "") or "",
                (rec.get("from_time") or "")[:5],
                (rec.get("to_time") or "")[:5],
                rec.get("status_display") or rec.get("status", ""),
                rec.get("approved_by_name") or "-",
            ])
        return rows

    def selected_record(self):
        return self.pager.record_at_row(self.table.currentRow())

    def apply_permission(self):
        if not self.employees:
            QMessageBox.warning(
                self, "No Employees", "Add an employee before applying."
            )
            return
        form = PermissionForm(self.api, self.employees, parent=self)
        if form.exec():
            self.load_permissions()

    def edit_permission(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a request.")
            return
        form = PermissionForm(
            self.api, self.employees, record=rec, parent=self
        )
        if form.exec():
            self.load_permissions()

    def _decide(self, approve):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a request.")
            return
        verb = "approve" if approve else "reject"
        confirm = QMessageBox.question(
            self, f"Confirm {verb.title()}",
            f"{verb.title()} permission for {rec.get('employee_name', '')} "
            f"on {rec.get('date', '')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if approve:
            ok, result = self.api.approve_permission(rec["id"])
        else:
            ok, result = self.api.reject_permission(rec["id"])
        if ok:
            self.load_permissions()
        else:
            QMessageBox.critical(self, f"{verb.title()} Failed", str(result))

    def delete_permission(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a request.")
            return
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete permission for {rec.get('employee_name', '')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, error = self.api.delete_permission(rec["id"])
        if ok:
            self.load_permissions()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))
