from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox,
    QFileDialog,
)

from PyQt6.QtCore import Qt, QTimer

from onboarding_form import OnboardingForm
from resignation_form import ResignationForm
from onboarding_checklist_dialog import OnboardingChecklistDialog
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
)


class _BaseTab(QWidget):
    """Common table tab with search + add/edit/delete + refresh."""

    COLUMNS = []

    def __init__(self, api):

        super().__init__()

        self.api = api
        self.employees = []

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_records)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout()

        top_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by employee...")
        self.search_input.textChanged.connect(
            lambda: self.search_timer.start()
        )
        top_row.addWidget(self.search_input)

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_record)
        top_row.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_record)
        top_row.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_record)
        top_row.addWidget(self.delete_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        top_row.addWidget(self.refresh_button)

        add_export_buttons(
            top_row,
            self,
            self.export_name(),
            lambda: self.COLUMNS,
            self._export_rows,
        )

        # Only HR can create/modify lifecycle records.
        can_manage = self.api.can("manage_lifecycle")
        self.add_button.setVisible(can_manage)
        self.edit_button.setVisible(can_manage)
        self.delete_button.setVisible(can_manage)

        layout.addLayout(top_row)

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

    def refresh_all(self):
        with loading(self):
            self.employees = self.api.get_employees()
        if show_list_load_error(self, self.api, "employees"):
            return
        self.load_records()

    def selected_record(self):
        return self.pager.record_at_row(self.table.currentRow())

    def set_cell(self, row, col, value, center=False):
        item = QTableWidgetItem(value)
        if center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, col, item)

    def export_name(self):
        return "lifecycle"

    # --- to be implemented by subclasses ---

    def load_records(self):
        raise NotImplementedError

    def populate_table(self):
        raise NotImplementedError

    def _export_rows(self):
        raise NotImplementedError

    def add_record(self):
        raise NotImplementedError

    def edit_record(self):
        raise NotImplementedError

    def delete_record(self):
        raise NotImplementedError


class OnboardingTab(_BaseTab):

    COLUMNS = [
        "ID", "Code", "Employee", "Joining", "Dept", "Desig", "Docs", "Status"
    ]

    def __init__(self, api):
        super().__init__(api)
        self.joining_letter_button = QPushButton("Download Joining Letter")
        self.joining_letter_button.clicked.connect(self.download_joining_letter)
        self.checklist_button = QPushButton("Document Checklist")
        self.checklist_button.clicked.connect(self.show_document_checklist)
        top_row = self.layout().itemAt(0).layout()
        top_row.insertWidget(3, self.checklist_button)
        top_row.insertWidget(4, self.joining_letter_button)

    def export_name(self):
        return "onboarding"

    def show_document_checklist(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(
                self, "No Selection", "Select an onboarding record."
            )
            return

        checklist = self.api.get_onboarding_document_checklist(rec["id"])
        if not checklist:
            QMessageBox.warning(
                self, "Unavailable", "Could not load document checklist."
            )
            return

        OnboardingChecklistDialog(checklist, parent=self).exec()
        self.load_records()

    def download_joining_letter(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(
                self, "No Selection", "Select an onboarding record."
            )
            return
        code = rec.get("employee_code", "employee")
        default_name = f"joining_letter_{code}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Joining Letter", default_name, "PDF (*.pdf)"
        )
        if not path:
            return
        ok, error = self.api.download_joining_letter(rec["id"], path)
        if ok:
            QMessageBox.information(
                self, "Downloaded", f"Joining letter saved to:\n{path}"
            )
        else:
            QMessageBox.critical(self, "Download Failed", str(error))

    def load_records(self):

        filters = {}
        search = self.search_input.text().strip()
        if search:
            filters["search"] = search

        with loading(self):
            data = self.api.get_onboardings(filters)

        if show_list_load_error(self, self.api, "onboarding records"):
            return

        self.pager.set_records(data, "onboarding record(s)")
        self.populate_table()

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, rec in enumerate(self.pager.page_records):
            self.set_cell(row, 0, str(rec.get("id", "")), True)
            self.set_cell(row, 1, rec.get("employee_code", "") or "")
            self.set_cell(row, 2, rec.get("employee_name", "") or "")
            self.set_cell(row, 3, rec.get("joining_date") or "-", True)
            self.set_cell(
                row, 4, "Yes" if rec.get("department_assigned") else "No", True
            )
            self.set_cell(
                row, 5, "Yes" if rec.get("designation_assigned") else "No", True
            )
            self.set_cell(
                row, 6, "Yes" if rec.get("documents_submitted") else "No", True
            )
            self.set_cell(
                row, 7,
                rec.get("status_display") or rec.get("status", ""), True
            )

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for rec in self.pager.all_records:
            rows.append([
                str(rec.get("id", "")),
                rec.get("employee_code", "") or "",
                rec.get("employee_name", "") or "",
                rec.get("joining_date") or "-",
                "Yes" if rec.get("department_assigned") else "No",
                "Yes" if rec.get("designation_assigned") else "No",
                "Yes" if rec.get("documents_submitted") else "No",
                rec.get("status_display") or rec.get("status", ""),
            ])
        return rows

    def add_record(self):
        if not self.employees:
            QMessageBox.warning(
                self, "No Employees", "Add an employee first."
            )
            return
        form = OnboardingForm(self.api, self.employees, parent=self)
        if form.exec():
            self.load_records()

    def edit_record(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(
                self, "No Selection", "Please select a record to edit."
            )
            return
        form = OnboardingForm(
            self.api, self.employees, record=rec, parent=self
        )
        if form.exec():
            self.load_records()

    def delete_record(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(
                self, "No Selection", "Please select a record to delete."
            )
            return
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete onboarding for {rec.get('employee_name', '')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, error = self.api.delete_onboarding(rec["id"])
        if ok:
            self.load_records()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))


class ExitTab(_BaseTab):

    COLUMNS = [
        "ID", "Code", "Employee", "Resigned", "Notice",
        "Last Day", "Exit", "Settlement"
    ]

    def export_name(self):
        return "resignations"

    def load_records(self):

        filters = {}
        search = self.search_input.text().strip()
        if search:
            filters["search"] = search

        with loading(self):
            data = self.api.get_resignations(filters)

        if show_list_load_error(self, self.api, "resignation records"):
            return

        self.pager.set_records(data, "resignation record(s)")
        self.populate_table()

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, rec in enumerate(self.pager.page_records):
            self.set_cell(row, 0, str(rec.get("id", "")), True)
            self.set_cell(row, 1, rec.get("employee_code", "") or "")
            self.set_cell(row, 2, rec.get("employee_name", "") or "")
            self.set_cell(row, 3, rec.get("resignation_date") or "-", True)
            self.set_cell(
                row, 4, f"{rec.get('notice_period_days', '')} d", True
            )
            self.set_cell(
                row, 5,
                rec.get("last_working_day")
                or rec.get("expected_last_working_day") or "-",
                True
            )
            self.set_cell(
                row, 6,
                rec.get("exit_status_display")
                or rec.get("exit_status", ""), True
            )
            self.set_cell(
                row, 7,
                rec.get("final_settlement_status_display")
                or rec.get("final_settlement_status", ""), True
            )

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for rec in self.pager.all_records:
            rows.append([
                str(rec.get("id", "")),
                rec.get("employee_code", "") or "",
                rec.get("employee_name", "") or "",
                rec.get("resignation_date") or "-",
                f"{rec.get('notice_period_days', '')} d",
                rec.get("last_working_day")
                or rec.get("expected_last_working_day") or "-",
                rec.get("exit_status_display") or rec.get("exit_status", ""),
                rec.get("final_settlement_status_display")
                or rec.get("final_settlement_status", ""),
            ])
        return rows

    def add_record(self):
        if not self.employees:
            QMessageBox.warning(
                self, "No Employees", "Add an employee first."
            )
            return
        form = ResignationForm(self.api, self.employees, parent=self)
        if form.exec():
            self.load_records()

    def edit_record(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(
                self, "No Selection", "Please select a record to edit."
            )
            return
        form = ResignationForm(
            self.api, self.employees, record=rec, parent=self
        )
        if form.exec():
            self.load_records()

    def delete_record(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(
                self, "No Selection", "Please select a record to delete."
            )
            return
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete resignation for {rec.get('employee_name', '')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, error = self.api.delete_resignation(rec["id"])
        if ok:
            self.load_records()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))


class LifecycleWindow(QWidget):

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.setWindowTitle("Employee Lifecycle")
        self.resize(1100, 660)

        layout = QVBoxLayout()

        title = QLabel("Employee Lifecycle")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.tabs = QTabWidget()

        self.onboarding_tab = OnboardingTab(self.api)
        self.exit_tab = ExitTab(self.api)

        self.tabs.addTab(self.onboarding_tab, "Onboarding")
        self.tabs.addTab(self.exit_tab, "Exit Management")

        layout.addWidget(self.tabs)

        self.setLayout(layout)

        # Initial load for both tabs.
        self.onboarding_tab.refresh_all()
        self.exit_tab.refresh_all()
