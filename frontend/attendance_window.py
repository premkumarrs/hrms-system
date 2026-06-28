from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QCheckBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox,
    QFrame,
)

from PyQt6.QtCore import Qt, QTimer, QDate

from attendance_form import AttendanceForm
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
    ("Present", "PRESENT"),
    ("Absent", "ABSENT"),
    ("Half Day", "HALF_DAY"),
    ("Leave", "LEAVE"),
]


class AttendanceWindow(QWidget):

    COLUMNS = [
        "ID",
        "Code",
        "Employee",
        "Date",
        "Check In",
        "Check Out",
        "Hours",
        "Late",
        "Status",
    ]

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.employees = []

        self.setWindowTitle("Attendance Management")

        self.resize(1150, 680)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_attendance)

        self.build_ui()

        self.load_employees()

        self.load_attendance()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Attendance Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.summary_labels = {}
        summary_row = QHBoxLayout()
        for key, label in [
            ("present", "Present"),
            ("absent", "Absent"),
            ("late_count", "Late"),
            ("total_working_hours", "Total Hours"),
        ]:
            card = QFrame()
            card.setFixedHeight(72)
            card.setStyleSheet(
                "background-color: #2d2d44; border-radius: 8px; padding: 8px;"
            )
            card_layout = QVBoxLayout()
            title_label = QLabel(label)
            title_label.setStyleSheet("font-size: 12px; color: #9aa0c0;")
            value_label = QLabel("0")
            value_label.setStyleSheet("font-size: 20px; font-weight: bold;")
            self.summary_labels[key] = value_label
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            card.setLayout(card_layout)
            summary_row.addWidget(card)
        layout.addLayout(summary_row)

        # --- Filter / search row ---
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by employee name or code..."
        )
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_row.addWidget(self.search_input)

        self.employee_filter = QComboBox()
        self.employee_filter.addItem("All Employees", None)
        self.employee_filter.currentIndexChanged.connect(self.on_employee_filter_changed)
        filter_row.addWidget(self.employee_filter)

        self.status_filter = QComboBox()
        for label, value in STATUS_FILTERS:
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self.load_attendance)
        filter_row.addWidget(self.status_filter)

        self.date_enabled = QCheckBox("Date")
        self.date_enabled.toggled.connect(self.on_date_toggle)
        filter_row.addWidget(self.date_enabled)

        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDisplayFormat("yyyy-MM-dd")
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.setEnabled(False)
        self.date_filter.dateChanged.connect(self.on_date_changed)
        filter_row.addWidget(self.date_filter)

        layout.addLayout(filter_row)

        # --- Action button row ---
        action_row = QHBoxLayout()

        self.check_in_button = QPushButton("Check In")
        self.check_in_button.clicked.connect(self.check_in)
        action_row.addWidget(self.check_in_button)

        self.check_out_button = QPushButton("Check Out")
        self.check_out_button.clicked.connect(self.check_out)
        action_row.addWidget(self.check_out_button)

        action_row.addStretch()

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_record)
        action_row.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_record)
        action_row.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_record)
        action_row.addWidget(self.delete_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        action_row.addWidget(self.refresh_button)

        add_export_buttons(
            action_row,
            self,
            "attendance",
            lambda: self.EXPORT_COLUMNS,
            self._export_rows,
        )

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

        can_manage = self.api.can("manage_attendance")
        self.add_button.setVisible(can_manage)
        self.edit_button.setVisible(can_manage)
        self.delete_button.setVisible(can_manage)

        linked = None
        employee_info = (self.api.current_user or {}).get("employee")
        if employee_info:
            linked = employee_info.get("id")

        if can_manage:
            self.check_in_button.setVisible(True)
            self.check_out_button.setVisible(True)
        elif linked:
            self.check_in_button.setVisible(True)
            self.check_out_button.setVisible(True)
            self._lock_employee_filter(linked)
        else:
            self.check_in_button.setVisible(False)
            self.check_out_button.setVisible(False)

    def _lock_employee_filter(self, employee_id):

        for index in range(self.employee_filter.count()):
            if self.employee_filter.itemData(index) == employee_id:
                self.employee_filter.setCurrentIndex(index)
                break

        self.employee_filter.setEnabled(False)

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

        if self.date_enabled.isChecked():
            filters["date"] = self.date_filter.date().toString("yyyy-MM-dd")

        return filters

    def on_employee_filter_changed(self):
        self.load_attendance()
        self.load_summary()

    def load_summary(self):

        employee_id = self.employee_filter.currentData()
        ref_date = None
        if self.date_enabled.isChecked():
            ref_date = self.date_filter.date().toString("yyyy-MM-dd")

        summary = self.api.get_attendance_summary(employee_id, ref_date) or {}

        for key, label in self.summary_labels.items():
            value = summary.get(key, 0)
            if key == "total_working_hours":
                label.setText(f"{float(value):.1f}")
            else:
                label.setText(str(value))

        cycle_start = summary.get("cycle_start", "")
        cycle_end = summary.get("cycle_end", "")
        if cycle_start and cycle_end:
            total = len(self.pager.all_records)
            self.status_label.setText(
                f"Cycle {cycle_start} to {cycle_end} · "
                f"{total} record(s) shown"
            )

    def load_attendance(self):

        with loading(self):
            data = self.api.get_attendance(self.build_filters())

        if show_list_load_error(self, self.api, "attendance records"):
            return

        self.pager.set_records(data, "record(s)")
        self.populate_table()
        self.load_summary()

    def refresh_all(self):

        self.load_employees()
        self.load_attendance()

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, rec in enumerate(self.pager.page_records):

            values = [
                str(rec.get("id", "")),
                rec.get("employee_code", "") or "",
                rec.get("employee_name", "") or "",
                rec.get("date", "") or "",
                (rec.get("check_in") or "")[:5],
                (rec.get("check_out") or "")[:5] if rec.get("check_out") else "-",
                str(rec.get("working_hours", "")),
                "Yes" if rec.get("late_entry") else "No",
                rec.get("status_display") or rec.get("status", ""),
            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(value)

                if col in (0, 4, 5, 6, 7):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for rec in self.pager.all_records:
            rows.append([
                rec.get("employee_code", "") or "",
                rec.get("employee_name", "") or "",
                rec.get("date", "") or "",
                (rec.get("check_in") or "")[:5],
                (rec.get("check_out") or "")[:5] if rec.get("check_out") else "",
                str(rec.get("working_hours", "")),
                "Yes" if rec.get("late_entry") else "No",
                rec.get("status_display") or rec.get("status", ""),
            ])
        return rows

    EXPORT_COLUMNS = [
        "Code", "Employee", "Date", "Check In",
        "Check Out", "Hours", "Late", "Status"
    ]

    # ------------------------------------------------------------------
    # Filter event handlers
    # ------------------------------------------------------------------

    def on_search_changed(self):
        self.search_timer.start()

    def on_date_toggle(self, checked):
        self.date_filter.setEnabled(checked)
        self.load_attendance()
        self.load_summary()

    def on_date_changed(self):
        if self.date_enabled.isChecked():
            self.load_attendance()
            self.load_summary()

    # ------------------------------------------------------------------
    # Check In / Check Out
    # ------------------------------------------------------------------

    def _selected_filter_employee(self):
        """Employee chosen in the filter combo, used as check-in/out target."""

        employee_id = self.employee_filter.currentData()

        if not employee_id:
            QMessageBox.information(
                self,
                "Select Employee",
                "Please choose an employee in the filter to check in/out."
            )
            return None

        return employee_id

    def check_in(self):

        employee_id = self._selected_filter_employee()

        if not employee_id:
            return

        ok, result = self.api.attendance_check_in(employee_id)

        if ok:
            QMessageBox.information(self, "Checked In", "Check-in recorded.")
            self.load_attendance()
        else:
            QMessageBox.critical(self, "Check-In Failed", str(result))

    def check_out(self):

        employee_id = self._selected_filter_employee()

        if not employee_id:
            return

        ok, result = self.api.attendance_check_out(employee_id)

        if ok:
            QMessageBox.information(self, "Checked Out", "Check-out recorded.")
            self.load_attendance()
        else:
            QMessageBox.critical(self, "Check-Out Failed", str(result))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def selected_record(self):

        return self.pager.record_at_row(self.table.currentRow())

    def add_record(self):

        if not self.api.can("manage_attendance"):
            QMessageBox.information(
                self,
                "Access Denied",
                "You do not have permission to add attendance records."
            )
            return

        if not self.employees:
            QMessageBox.warning(
                self,
                "No Employees",
                "Add an employee before recording attendance."
            )
            return

        form = AttendanceForm(self.api, self.employees, parent=self)

        if form.exec():
            self.load_attendance()

    def edit_record(self):

        if not self.api.can("manage_attendance"):
            QMessageBox.information(
                self,
                "Access Denied",
                "You do not have permission to edit attendance records."
            )
            return

        record = self.selected_record()

        if not record:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a record to edit."
            )
            return

        form = AttendanceForm(
            self.api,
            self.employees,
            record=record,
            parent=self
        )

        if form.exec():
            self.load_attendance()

    def delete_record(self):

        if not self.api.can("manage_attendance"):
            QMessageBox.information(
                self,
                "Access Denied",
                "You do not have permission to delete attendance records."
            )
            return

        record = self.selected_record()

        if not record:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a record to delete."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete attendance for {record.get('employee_name', '')} "
            f"on {record.get('date', '')}?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, error = self.api.delete_attendance(record["id"])

        if ok:
            self.load_attendance()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))
