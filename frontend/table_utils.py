"""Table sorting, resizing, client pagination, and export toolbar helpers."""

import math

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QComboBox,
    QLabel,
    QWidget,
)

from exporters import export_csv, export_excel


def setup_list_table(table, id_column=0, stretch_column=None):
    """Enable sort + interactive resize on a read-only list table."""

    table.setSortingEnabled(True)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(True)
    if id_column is not None:
        header.setSectionResizeMode(
            id_column, QHeaderView.ResizeMode.ResizeToContents
        )
    if stretch_column is not None:
        header.setSectionResizeMode(
            stretch_column, QHeaderView.ResizeMode.Stretch
        )


class TablePager:
    """Client-side pagination for in-memory record lists."""

    PAGE_SIZES = (10, 25, 50, 100)

    def __init__(self, table, status_label=None, page_size=25):
        self.table = table
        self.status_label = status_label
        self.page_size = page_size
        self.page = 0
        self.all_records = []
        self.page_records = []
        self.entity_label = "record(s)"

    def set_records(self, records, entity_label=None):
        self.all_records = list(records or [])
        if entity_label:
            self.entity_label = entity_label
        self.page = 0
        self._refresh_slice()
        self._update_status()

    def _refresh_slice(self):
        if not self.all_records:
            self.page_records = []
            return
        total_pages = max(1, math.ceil(len(self.all_records) / self.page_size))
        if self.page >= total_pages:
            self.page = total_pages - 1
        start = self.page * self.page_size
        end = start + self.page_size
        self.page_records = self.all_records[start:end]

    def record_at_row(self, row):
        if 0 <= row < len(self.page_records):
            return self.page_records[row]
        return None

    def total_pages(self):
        if not self.all_records:
            return 1
        return max(1, math.ceil(len(self.all_records) / self.page_size))

    def go_prev(self):
        if self.page > 0:
            self.page -= 1
            self._refresh_slice()
            self._update_status()
            return True
        return False

    def go_next(self):
        if self.page < self.total_pages() - 1:
            self.page += 1
            self._refresh_slice()
            self._update_status()
            return True
        return False

    def set_page_size(self, size):
        self.page_size = int(size)
        self.page = 0
        self._refresh_slice()
        self._update_status()

    def _update_status(self):
        if not self.status_label:
            return
        total = len(self.all_records)
        if total == 0:
            self.status_label.setText(f"0 {self.entity_label} shown")
            return
        start = self.page * self.page_size + 1
        end = min(total, (self.page + 1) * self.page_size)
        self.status_label.setText(
            f"Showing {start}–{end} of {total} {self.entity_label} "
            f"(page {self.page + 1}/{self.total_pages()})"
        )


def build_pagination_bar(pager, on_page_change):
    """Return a widget with page-size, prev/next controls."""

    bar = QWidget()
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)

    layout.addWidget(QLabel("Rows per page:"))
    size_combo = QComboBox()
    for size in TablePager.PAGE_SIZES:
        size_combo.addItem(str(size), size)
    size_combo.setCurrentText(str(pager.page_size))
    layout.addWidget(size_combo)

    prev_btn = QPushButton("Previous")
    next_btn = QPushButton("Next")
    page_label = QLabel("")
    layout.addWidget(prev_btn)
    layout.addWidget(page_label)
    layout.addWidget(next_btn)
    layout.addStretch()

    def refresh_label():
        page_label.setText(
            f"Page {pager.page + 1} of {pager.total_pages()}"
        )

    def rerender():
        refresh_label()
        on_page_change()

    def on_prev():
        if pager.go_prev():
            rerender()

    def on_next():
        if pager.go_next():
            rerender()

    def on_size_changed():
        pager.set_page_size(size_combo.currentData())
        rerender()

    prev_btn.clicked.connect(on_prev)
    next_btn.clicked.connect(on_next)
    size_combo.currentIndexChanged.connect(on_size_changed)
    refresh_label()

    bar.setLayout(layout)
    bar.refresh_label = refresh_label
    return bar


def add_export_buttons(toolbar, parent, default_name, columns_getter, rows_getter):
    """Append CSV/Excel export buttons to an existing toolbar layout."""

    csv_btn = QPushButton("Export CSV")
    excel_btn = QPushButton("Export Excel")

    def do_csv():
        export_csv(parent, default_name, columns_getter(), rows_getter())

    def do_excel():
        export_excel(parent, default_name, columns_getter(), rows_getter())

    csv_btn.clicked.connect(do_csv)
    excel_btn.clicked.connect(do_excel)
    toolbar.addWidget(csv_btn)
    toolbar.addWidget(excel_btn)


def populate_employee_filter(combo, employees, include_all=True):
    """Fill an employee QComboBox with standard name/code labels."""

    combo.blockSignals(True)
    combo.clear()
    if include_all:
        combo.addItem("All Employees", None)
    for emp in employees or []:
        name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        label = f"{name} ({emp.get('employee_code', '')})"
        combo.addItem(label, emp["id"])
    combo.blockSignals(False)


def employee_display_label(emp):
    """Format employee dict as 'Name (CODE)' for exports and tables."""

    name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
    code = emp.get("employee_code", "")
    return f"{name} ({code})" if code else name
