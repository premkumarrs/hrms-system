from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox
)

from PyQt6.QtCore import Qt, QTimer

from leave_form import LeaveForm
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

TYPE_FILTERS = [
    ("All Types", None),
    ("Casual Leave", "CL"),
    ("Sick Leave", "SL"),
    ("Earned Leave", "EL"),
]


class LeaveBalanceDialog(QDialog):

    def __init__(self, employee_label, balance, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Leave Balance")
        self.resize(420, 280)

        layout = QVBoxLayout()

        heading = QLabel(
            f"{employee_label}  —  {balance.get('year', '')}"
        )
        heading.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(heading)

        table = QTableWidget()
        rows = balance.get("balances", [])
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            ["Type", "Allocated", "Used", "Pending", "Available"]
        )
        table.setRowCount(len(rows))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        for row, item in enumerate(rows):
            values = [
                item.get("leave_type_display", ""),
                str(item.get("allocated", "")),
                str(item.get("used", "")),
                str(item.get("pending", "")),
                str(item.get("available", "")),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col > 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, cell)

        layout.addWidget(table)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)


class LeaveWindow(QWidget):

    COLUMNS = [
        "ID",
        "Code",
        "Employee",
        "Type",
        "Start",
        "End",
        "Days",
        "Status",
        "Approved By",
    ]

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.employees = []

        self.setWindowTitle("Leave Management")

        self.resize(1150, 700)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_leaves)

        self.build_ui()

        self.load_employees()

        self.load_leaves()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Leave Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # --- Dashboard cards ---
        self.cards_layout = QHBoxLayout()
        self.card_labels = {}

        for key, text in [
            ("total", "Total"),
            ("PENDING", "Pending"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
        ]:
            card, value_label = self._build_card(text)
            self.card_labels[key] = value_label
            self.cards_layout.addWidget(card)

        layout.addLayout(self.cards_layout)

        # --- Filter / search row ---
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by employee, code or reason..."
        )
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_row.addWidget(self.search_input)

        self.employee_filter = QComboBox()
        self.employee_filter.addItem("All Employees", None)
        self.employee_filter.currentIndexChanged.connect(self.load_leaves)
        filter_row.addWidget(self.employee_filter)

        self.status_filter = QComboBox()
        for label, value in STATUS_FILTERS:
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self.load_leaves)
        filter_row.addWidget(self.status_filter)

        self.type_filter = QComboBox()
        for label, value in TYPE_FILTERS:
            self.type_filter.addItem(label, value)
        self.type_filter.currentIndexChanged.connect(self.load_leaves)
        filter_row.addWidget(self.type_filter)

        layout.addLayout(filter_row)

        # --- Action button row ---
        action_row = QHBoxLayout()

        self.apply_button = QPushButton("Apply Leave")
        self.apply_button.clicked.connect(self.apply_leave)
        action_row.addWidget(self.apply_button)

        self.approve_button = QPushButton("Approve")
        self.approve_button.clicked.connect(self.approve_leave)
        action_row.addWidget(self.approve_button)

        self.reject_button = QPushButton("Reject")
        self.reject_button.clicked.connect(self.reject_leave)
        action_row.addWidget(self.reject_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_leave)
        action_row.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_leave)
        action_row.addWidget(self.delete_button)

        action_row.addStretch()

        self.balance_button = QPushButton("View Balance")
        self.balance_button.clicked.connect(self.view_balance)
        action_row.addWidget(self.balance_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        action_row.addWidget(self.refresh_button)

        add_export_buttons(
            action_row, self, "leaves", lambda: self.COLUMNS, self._export_rows
        )

        # Approval is restricted to Managers / HR.
        can_approve = self.api.can("approve_leave")
        self.approve_button.setVisible(can_approve)
        self.reject_button.setVisible(can_approve)

        can_manage = self.api.can("approve_leave")
        self.edit_button.setVisible(can_manage)
        self.delete_button.setVisible(can_manage)

        layout.addLayout(action_row)

        # --- Table ---
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
        if can_manage:
            self.table.doubleClicked.connect(self.edit_leave)

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

    def _build_card(self, text):

        card = QFrame()
        card.setFixedHeight(80)
        card.setStyleSheet("""
            background-color: #2d2d44;
            border-radius: 10px;
            color: white;
        """)

        card_layout = QVBoxLayout()

        value_label = QLabel("0")
        value_label.setStyleSheet("font-size: 26px; font-weight: bold;")

        title_label = QLabel(text)
        title_label.setStyleSheet("font-size: 13px; color: #c0c0c0;")

        card_layout.addWidget(value_label)
        card_layout.addWidget(title_label)

        card.setLayout(card_layout)

        return card, value_label

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

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

        leave_type = self.type_filter.currentData()
        if leave_type:
            filters["leave_type"] = leave_type

        return filters

    def load_leaves(self):

        with loading(self):
            data = self.api.get_leaves(self.build_filters())

        if show_list_load_error(self, self.api, "leave requests"):
            return

        self.pager.set_records(data, "request(s)")
        self.populate_table()
        self.update_cards()

    def refresh_all(self):
        self.load_employees()
        self.load_leaves()

    def update_cards(self):

        counts = {"PENDING": 0, "APPROVED": 0, "REJECTED": 0}

        for rec in self.pager.all_records:
            status = rec.get("status")
            if status in counts:
                counts[status] += 1

        self.card_labels["total"].setText(str(len(self.pager.all_records)))
        self.card_labels["PENDING"].setText(str(counts["PENDING"]))
        self.card_labels["APPROVED"].setText(str(counts["APPROVED"]))
        self.card_labels["REJECTED"].setText(str(counts["REJECTED"]))

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, rec in enumerate(self.pager.page_records):

            values = [
                str(rec.get("id", "")),
                rec.get("employee_code", "") or "",
                rec.get("employee_name", "") or "",
                rec.get("leave_type_display") or rec.get("leave_type", ""),
                rec.get("start_date", "") or "",
                rec.get("end_date", "") or "",
                str(rec.get("number_of_days", "")),
                rec.get("status_display") or rec.get("status", ""),
                rec.get("approved_by_name") or "-",
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 6, 7):
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
                rec.get("leave_type_display") or rec.get("leave_type", ""),
                rec.get("start_date", "") or "",
                rec.get("end_date", "") or "",
                str(rec.get("number_of_days", "")),
                rec.get("status_display") or rec.get("status", ""),
                rec.get("approved_by_name") or "-",
            ])
        return rows

    # ------------------------------------------------------------------
    # Filter handlers
    # ------------------------------------------------------------------

    def on_search_changed(self):
        self.search_timer.start()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def selected_record(self):

        return self.pager.record_at_row(self.table.currentRow())

    def apply_leave(self):

        if not self.employees:
            QMessageBox.warning(
                self, "No Employees",
                "Add an employee before applying for leave."
            )
            return

        form = LeaveForm(self.api, self.employees, parent=self)

        if form.exec():
            self.load_leaves()

    def edit_leave(self):

        record = self.selected_record()

        if not record:
            QMessageBox.information(
                self, "No Selection", "Please select a leave to edit."
            )
            return

        form = LeaveForm(
            self.api, self.employees, record=record, parent=self
        )

        if form.exec():
            self.load_leaves()

    def approve_leave(self):
        self._decide(approve=True)

    def reject_leave(self):
        self._decide(approve=False)

    def _decide(self, approve):

        record = self.selected_record()

        if not record:
            QMessageBox.information(
                self, "No Selection", "Please select a leave request."
            )
            return

        verb = "approve" if approve else "reject"

        confirm = QMessageBox.question(
            self,
            f"Confirm {verb.title()}",
            f"{verb.title()} leave for {record.get('employee_name', '')} "
            f"({record.get('start_date', '')} to {record.get('end_date', '')})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        if approve:
            ok, result = self.api.approve_leave(record["id"])
        else:
            ok, result = self.api.reject_leave(record["id"])

        if ok:
            self.load_leaves()
        else:
            QMessageBox.critical(
                self, f"{verb.title()} Failed", str(result)
            )

    def delete_leave(self):

        record = self.selected_record()

        if not record:
            QMessageBox.information(
                self, "No Selection", "Please select a leave to delete."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete leave request for {record.get('employee_name', '')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, error = self.api.delete_leave(record["id"])

        if ok:
            self.load_leaves()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))

    def view_balance(self):

        employee_id = self.employee_filter.currentData()

        if not employee_id:
            QMessageBox.information(
                self, "Select Employee",
                "Please choose an employee in the filter to view balance."
            )
            return

        balance = self.api.get_leave_balance(employee_id)

        if not balance:
            QMessageBox.critical(
                self, "Error", "Could not load leave balance."
            )
            return

        label = self.employee_filter.currentText()

        dialog = LeaveBalanceDialog(label, balance, parent=self)
        dialog.exec()
