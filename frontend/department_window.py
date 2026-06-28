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
    QMessageBox,
)

from PyQt6.QtCore import Qt, QTimer

from lookup_form import LookupForm
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
)


class DepartmentWindow(QWidget):

    COLUMNS = ["ID", "Department Name"]

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.setWindowTitle("Departments")
        self.resize(700, 520)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_records)

        self.build_ui()
        self.load_records()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Department Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search departments...")
        self.search_input.textChanged.connect(lambda: self.search_timer.start())
        toolbar.addWidget(self.search_input)

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_record)
        toolbar.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_record)
        toolbar.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_record)
        toolbar.addWidget(self.delete_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_records)
        toolbar.addWidget(self.refresh_button)

        add_export_buttons(
            toolbar, self, "departments", lambda: self.COLUMNS, self._export_rows
        )

        can_manage = self.api.can("manage_departments")
        self.add_button.setVisible(can_manage)
        self.edit_button.setVisible(can_manage)
        self.delete_button.setVisible(can_manage)

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.edit_record)

        setup_list_table(self.table, id_column=0, stretch_column=1)

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

    def load_records(self):

        search = self.search_input.text().strip()

        with loading(self):
            data = self.api.get_departments(search=search or None)

        if show_list_load_error(self, self.api, "departments"):
            return

        self.pager.set_records(data, "department(s)")
        self.populate_table()

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, rec in enumerate(self.pager.page_records):
            self.table.setItem(row, 0, QTableWidgetItem(str(rec.get("id", ""))))
            item = QTableWidgetItem(rec.get("name", ""))
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(row, 1, item)

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        return [
            [str(rec.get("id", "")), rec.get("name", "")]
            for rec in self.pager.all_records
        ]

    def selected_record(self):
        return self.pager.record_at_row(self.table.currentRow())

    def add_record(self):
        form = LookupForm("Add Department", "Name *", parent=self)
        if not form.exec():
            return
        name = form.get_value()
        if not name:
            QMessageBox.warning(self, "Validation", "Department name is required.")
            return
        ok, error = self.api.create_department({"name": name})
        if ok:
            self.load_records()
        else:
            QMessageBox.critical(self, "Save Failed", str(error))

    def edit_record(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a department.")
            return
        form = LookupForm(
            "Edit Department", "Name *", initial=rec.get("name", ""), parent=self
        )
        if not form.exec():
            return
        name = form.get_value()
        if not name:
            QMessageBox.warning(self, "Validation", "Department name is required.")
            return
        ok, error = self.api.update_department(rec["id"], {"name": name})
        if ok:
            self.load_records()
        else:
            QMessageBox.critical(self, "Save Failed", str(error))

    def delete_record(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(self, "No Selection", "Select a department.")
            return
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete department '{rec.get('name', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, error = self.api.delete_department(rec["id"])
        if ok:
            self.load_records()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))
