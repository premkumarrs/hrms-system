"""Dedicated attendance deviation analysis screen (embedded in Reports)."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDateEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox,
)

from PyQt6.QtCore import QDate

from bar_chart import BarChartWidget
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
)


class AttendanceDeviationWindow(QWidget):
    """Employee + date filtered deviation report with missing/overtime hours."""

    COLUMNS = [
        "Code",
        "Employee",
        "Present",
        "Absent",
        "Expected Hrs",
        "Actual Hrs",
        "Missing Hrs",
        "Overtime Hrs",
        "Deviation",
    ]

    def __init__(self, api, parent=None):

        super().__init__(parent)

        self.api = api
        self.employees = []
        self.chart_points = []

        self.build_ui()
        self.load_employees()

    def build_ui(self):

        layout = QVBoxLayout()

        heading = QLabel("Attendance Deviation Analysis")
        heading.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(heading)

        filters = QHBoxLayout()

        filters.addWidget(QLabel("Employee:"))
        self.employee_combo = QComboBox()
        self.employee_combo.setMinimumWidth(220)
        filters.addWidget(self.employee_combo)

        filters.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        filters.addWidget(self.start_date)

        filters.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        filters.addWidget(self.end_date)

        self.generate_button = QPushButton("Analyze")
        self.generate_button.clicked.connect(self.generate_report)
        filters.addWidget(self.generate_button)

        add_export_buttons(
            filters,
            self,
            "attendance_deviation",
            lambda: self.COLUMNS,
            self._export_rows,
        )

        layout.addLayout(filters)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #9aa0c0;")
        layout.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)

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

        self.chart = BarChartWidget(title="Deviation (hours)")
        self.chart.setMinimumHeight(180)
        layout.addWidget(self.chart)

        self.setLayout(layout)

    def load_employees(self):

        with loading(self):
            self.employees = self.api.get_employees() or []

        if show_list_load_error(self, self.api, "employees"):
            return

        self.employee_combo.clear()
        self.employee_combo.addItem("All (in scope)", None)

        for emp in self.employees:
            code = emp.get("employee_code", "")
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            label = f"{code} — {name}" if code else name
            self.employee_combo.addItem(label, emp.get("id"))

    def generate_report(self):

        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        employee_id = self.employee_combo.currentData()

        with loading(self):
            data = self.api.get_attendance_report(
                start=start,
                end=end,
                employee_id=employee_id,
            )

        if not data:
            if show_list_load_error(
                self, self.api, "deviation report"
            ) or self.api.last_error:
                QMessageBox.warning(
                    self,
                    "No Data",
                    self.api.last_error or "Could not load deviation report.",
                )
            self.pager.set_records([], "employee(s)")
            self.populate_table()
            self.chart.set_data([])
            self.summary_label.setText("")
            self.chart_points = []
            return

        records = []
        chart_points = []

        for row in data.get("results", []):
            deviation = float(row.get("deviation_hours", 0) or 0)
            missing = abs(deviation) if deviation < 0 else 0
            overtime = deviation if deviation > 0 else 0

            record = {
                "values": [
                    row.get("employee_code", ""),
                    row.get("employee_name", ""),
                    row.get("present", 0),
                    row.get("absent", 0),
                    row.get("expected_hours", 0),
                    row.get("actual_hours", 0),
                    round(missing, 2),
                    round(overtime, 2),
                    round(deviation, 2),
                ],
                "chart_label": row.get("employee_code", "?")[:10],
                "chart_value": abs(deviation),
            }
            records.append(record)
            chart_points.append(
                (record["chart_label"], record["chart_value"])
            )

        self.chart_points = chart_points
        self.pager.set_records(records, "employee(s)")
        self.populate_table()

        self.chart.set_data(chart_points)
        self.summary_label.setText(
            f"Cycle {data.get('cycle_start', start)} to "
            f"{data.get('cycle_end', end)} — {len(records)} employee(s)"
        )

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for r, record in enumerate(self.pager.page_records):
            values = record["values"]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        return [rec["values"] for rec in self.pager.all_records]
