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
    QStackedWidget,
)

from PyQt6.QtCore import QDate

from bar_chart import BarChartWidget
from attendance_deviation_window import AttendanceDeviationWindow
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
)


# (Display label, report path, supports status filter)
REPORT_TYPES = [
    ("Attendance Report", "attendance", False),
    ("Leave Report", "leave", True),
    ("Project Headcount", "project-headcount", False),
    ("Attrition Report", "attrition", False),
    ("Payroll Summary", "payroll", False),
    ("Attendance Trend (14d)", "analytics:attendance", False),
    ("Leave Trend (6mo)", "analytics:leave", False),
    ("Project Headcount Chart", "analytics:headcount", False),
    ("Attrition Trend (12mo)", "analytics:attrition", False),
    ("Attendance Deviation", "attendance-deviation", False),
]

LEAVE_STATUSES = [
    ("All Statuses", None),
    ("Pending", "PENDING"),
    ("Approved", "APPROVED"),
    ("Rejected", "REJECTED"),
]


class ReportWindow(QWidget):

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.columns = []

        self.current_title = "Report"

        self.setWindowTitle("Reports & Analytics")

        self.resize(1150, 680)

        self.build_ui()

        self.generate_report()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Reports & Analytics")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # --- Controls row 1: report type + filters ---
        controls = QHBoxLayout()

        self.report_type = QComboBox()
        for label, path, _ in REPORT_TYPES:
            self.report_type.addItem(label, path)
        self.report_type.currentIndexChanged.connect(self.on_type_changed)
        controls.addWidget(self.report_type)

        self.status_filter = QComboBox()
        for label, value in LEAVE_STATUSES:
            self.status_filter.addItem(label, value)
        controls.addWidget(self.status_filter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search employee...")
        controls.addWidget(self.search_input)

        layout.addLayout(controls)

        # --- Controls row 2: date filters + actions ---
        date_row = QHBoxLayout()

        self.start_enabled = QCheckBox("From")
        date_row.addWidget(self.start_enabled)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setEnabled(False)
        date_row.addWidget(self.start_date)

        self.end_enabled = QCheckBox("To")
        date_row.addWidget(self.end_enabled)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setEnabled(False)
        date_row.addWidget(self.end_date)

        self.start_enabled.toggled.connect(self.start_date.setEnabled)
        self.end_enabled.toggled.connect(self.end_date.setEnabled)

        date_row.addStretch()

        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate_report)
        date_row.addWidget(self.generate_button)

        self.export_bar = QWidget()
        export_layout = QHBoxLayout()
        export_layout.setContentsMargins(0, 0, 0, 0)
        self.export_bar.setLayout(export_layout)
        add_export_buttons(
            export_layout,
            self,
            "report",
            lambda: self.columns,
            self._export_rows,
        )
        date_row.addWidget(self.export_bar)

        self.chart_toggle = QCheckBox("Show Chart")
        self.chart_toggle.toggled.connect(self.on_chart_toggle)
        date_row.addWidget(self.chart_toggle)

        layout.addLayout(date_row)

        self.content_stack = QStackedWidget()

        # Standard tabular reports.
        table_page = QWidget()
        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)

        setup_list_table(self.table, id_column=0, stretch_column=1)

        table_layout.addWidget(self.table)

        self.chart = BarChartWidget()
        self.chart.setVisible(False)
        table_layout.addWidget(self.chart)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        table_layout.addWidget(self.status_label)

        self.pager = TablePager(self.table, self.status_label)
        self.pagination_bar = build_pagination_bar(
            self.pager, self.populate_table
        )
        table_layout.addWidget(self.pagination_bar)

        table_page.setLayout(table_layout)

        self.deviation_page = AttendanceDeviationWindow(self.api)

        self.content_stack.addWidget(table_page)
        self.content_stack.addWidget(self.deviation_page)
        layout.addWidget(self.content_stack)

        self.setLayout(layout)

        self.on_type_changed()

    def on_type_changed(self):

        path = self.report_type.currentData()
        is_deviation = path == "attendance-deviation"

        self.content_stack.setCurrentIndex(1 if is_deviation else 0)
        self.generate_button.setVisible(not is_deviation)
        self.export_bar.setVisible(not is_deviation)
        self.chart_toggle.setVisible(not is_deviation)
        self.search_input.setVisible(not is_deviation)
        self.start_enabled.setVisible(not is_deviation)
        self.start_date.setVisible(not is_deviation)
        self.end_enabled.setVisible(not is_deviation)
        self.end_date.setVisible(not is_deviation)

        supports_status = REPORT_TYPES[self.report_type.currentIndex()][2]
        self.status_filter.setVisible(supports_status and not is_deviation)

        if is_deviation:
            self.deviation_page.generate_report()

    def build_filters(self):

        filters = {}

        if self.start_enabled.isChecked():
            filters["start"] = self.start_date.date().toString("yyyy-MM-dd")

        if self.end_enabled.isChecked():
            filters["end"] = self.end_date.date().toString("yyyy-MM-dd")

        search = self.search_input.text().strip()
        if search:
            filters["search"] = search

        if self.status_filter.isVisible():
            status = self.status_filter.currentData()
            if status:
                filters["status"] = status

        # Attrition is filtered by year (from the start date control).
        path = self.report_type.currentData()
        if path == "attrition":
            filters["year"] = self.start_date.date().year()

        return filters

    def generate_report(self):

        path = self.report_type.currentData()

        if path == "attendance-deviation":
            self.deviation_page.generate_report()
            return

        with loading(self):
            if isinstance(path, str) and path.startswith("analytics:"):
                report = self._build_analytics_report(path.split(":", 1)[1])
            else:
                report = self.api.get_report(path, self.build_filters())

        if not report:
            if show_list_load_error(self, self.api, "report"):
                return
            QMessageBox.critical(
                self, "Error", "Could not load the report."
            )
            return

        self.current_title = report.get("title", "Report")
        self.columns = report.get("columns", [])
        rows = report.get("rows", [])

        self.pager.set_records(rows, "row(s)")
        self.populate_table()
        self.update_chart()

        self.status_label.setText(
            f"{self.current_title}: {len(rows)} row(s)"
        )

    def _build_analytics_report(self, chart_key):

        analytics = self.api.get_dashboard_analytics()
        if not analytics:
            return None

        builders = {
            "attendance": (
                "Attendance Trend (14 days)",
                ["Date", "Present", "Absent"],
                lambda rows: [
                    [row["date"], row.get("present", 0), row.get("absent", 0)]
                    for row in rows
                ],
                analytics.get("attendance_trend", []),
            ),
            "leave": (
                "Leave Trend (6 months)",
                ["Month", "Approved", "Pending", "Rejected"],
                lambda rows: [
                    [
                        row["month"],
                        row.get("approved", 0),
                        row.get("pending", 0),
                        row.get("rejected", 0),
                    ]
                    for row in rows
                ],
                analytics.get("leave_trend", []),
            ),
            "headcount": (
                "Project Headcount Chart",
                ["Project", "Headcount"],
                lambda rows: [
                    [row["project"], row.get("headcount", 0)] for row in rows
                ],
                analytics.get("project_headcount", []),
            ),
            "attrition": (
                "Attrition Trend (12 months)",
                ["Month", "Resignations"],
                lambda rows: [
                    [row["month"], row.get("count", 0)] for row in rows
                ],
                analytics.get("attrition_trend", []),
            ),
        }

        spec = builders.get(chart_key)
        if not spec:
            return None

        title, columns, row_fn, source_rows = spec
        return {
            "title": title,
            "columns": columns,
            "rows": row_fn(source_rows),
        }

    def on_chart_toggle(self, checked):
        self.chart.setVisible(checked)
        if checked:
            self.update_chart()

    def update_chart(self):
        """Plot the rightmost numeric column against the first column label."""

        rows = self.pager.all_records

        if not self.chart_toggle.isChecked() or not rows:
            self.chart.set_data([])
            return

        # Find the rightmost column whose values are mostly numeric.
        chart_col = None
        for col in range(len(self.columns) - 1, 0, -1):
            numeric = 0
            for row in rows:
                if col < len(row) and self._as_number(row[col]) is not None:
                    numeric += 1
            if numeric >= max(1, len(rows) // 2):
                chart_col = col
                break

        if chart_col is None:
            self.chart.set_data([])
            return

        data = []
        for row in rows:
            value = self._as_number(row[chart_col]) if chart_col < len(row) else None
            if value is not None:
                data.append((row[0], value))

        self.chart.set_data(data)

    @staticmethod
    def _as_number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setRowCount(len(self.pager.page_records))

        for r, row in enumerate(self.pager.page_records):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        return list(self.pager.all_records)
