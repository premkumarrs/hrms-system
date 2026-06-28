from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
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

from project_form import ProjectForm
from allocate_form import AllocateForm
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
)


STATUS_FILTERS = [
    ("All Statuses", None),
    ("Active", "ACTIVE"),
    ("Completed", "COMPLETED"),
]


class ProjectHistoryDialog(QDialog):
    """Shows the allocation history of a project, with a release action."""

    COLUMNS = ["ID", "Code", "Employee", "Role", "Allocated", "Released", "Active"]

    def __init__(self, api, project, parent=None):

        super().__init__(parent)

        self.api = api
        self.project = project
        self.allocations = []

        self.setWindowTitle(f"Project History — {project.get('name', '')}")
        self.resize(760, 420)

        layout = QVBoxLayout()

        heading = QLabel(
            f"{project.get('name', '')}  ({project.get('client', '')})"
        )
        heading.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(heading)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        button_row = QHBoxLayout()

        self.release_button = QPushButton("Release Selected")
        self.release_button.clicked.connect(self.release_selected)
        self.release_button.setVisible(self.api.can("manage_projects"))
        button_row.addWidget(self.release_button)

        button_row.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)

        layout.addLayout(button_row)

        self.setLayout(layout)

        self.load()

    def load(self):

        self.allocations = self.api.get_project_allocations(self.project["id"])

        self.table.setRowCount(len(self.allocations))

        for row, alloc in enumerate(self.allocations):

            values = [
                str(alloc.get("id", "")),
                alloc.get("employee_code", "") or "",
                alloc.get("employee_name", "") or "",
                alloc.get("role", "") or "",
                alloc.get("allocated_on", "") or "",
                alloc.get("released_on") or "-",
                "Yes" if alloc.get("is_active") else "No",
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

    def release_selected(self):

        row = self.table.currentRow()

        if row < 0 or row >= len(self.allocations):
            QMessageBox.information(
                self, "No Selection", "Please select an allocation to release."
            )
            return

        alloc = self.allocations[row]

        if not alloc.get("is_active"):
            QMessageBox.information(
                self, "Already Released",
                "This allocation has already been released."
            )
            return

        ok, result = self.api.release_allocation(alloc["id"])

        if ok:
            self.load()
        else:
            QMessageBox.critical(self, "Release Failed", str(result))


class ProjectWindow(QWidget):

    COLUMNS = [
        "ID",
        "Name",
        "Client",
        "Start",
        "End",
        "Status",
        "Headcount",
    ]

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.employees = []

        self.setWindowTitle("Project Management")

        self.resize(1100, 660)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_projects)

        self.build_ui()

        self.load_employees()

        self.load_projects()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Project Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # --- Filter / search row ---
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by name, client or description..."
        )
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_row.addWidget(self.search_input)

        self.status_filter = QComboBox()
        for label, value in STATUS_FILTERS:
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self.load_projects)
        filter_row.addWidget(self.status_filter)

        layout.addLayout(filter_row)

        # --- Action button row ---
        action_row = QHBoxLayout()

        self.add_button = QPushButton("Add Project")
        self.add_button.clicked.connect(self.add_project)
        action_row.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_project)
        action_row.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_project)
        action_row.addWidget(self.delete_button)

        action_row.addStretch()

        self.allocate_button = QPushButton("Allocate Employee")
        self.allocate_button.clicked.connect(self.allocate_employee)
        action_row.addWidget(self.allocate_button)

        self.history_button = QPushButton("Project History")
        self.history_button.clicked.connect(self.view_history)
        action_row.addWidget(self.history_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        action_row.addWidget(self.refresh_button)

        add_export_buttons(
            action_row, self, "projects", lambda: self.COLUMNS, self._export_rows
        )

        # Only HR can create/modify projects and allocations.
        can_manage = self.api.can("manage_projects")
        self.add_button.setVisible(can_manage)
        self.edit_button.setVisible(can_manage)
        self.delete_button.setVisible(can_manage)
        self.allocate_button.setVisible(can_manage)

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
        self.table.doubleClicked.connect(self.view_history)

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

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_employees(self):
        with loading(self):
            self.employees = self.api.get_employees()
        if show_list_load_error(self, self.api, "employees"):
            return

    def build_filters(self):

        filters = {}

        search = self.search_input.text().strip()
        if search:
            filters["search"] = search

        status = self.status_filter.currentData()
        if status:
            filters["status"] = status

        return filters

    def load_projects(self):

        with loading(self):
            data = self.api.get_projects(self.build_filters())

        if show_list_load_error(self, self.api, "projects"):
            return

        self.pager.set_records(data, "project(s)")
        self.populate_table()

    def refresh_all(self):
        self.load_employees()
        self.load_projects()

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, proj in enumerate(self.pager.page_records):

            values = [
                str(proj.get("id", "")),
                proj.get("name", "") or "",
                proj.get("client", "") or "",
                proj.get("start_date", "") or "",
                proj.get("end_date") or "-",
                proj.get("status_display") or proj.get("status", ""),
                str(proj.get("headcount", 0)),
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 3, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for proj in self.pager.all_records:
            rows.append([
                str(proj.get("id", "")),
                proj.get("name", "") or "",
                proj.get("client", "") or "",
                proj.get("start_date", "") or "",
                proj.get("end_date") or "-",
                proj.get("status_display") or proj.get("status", ""),
                str(proj.get("headcount", 0)),
            ])
        return rows

    def on_search_changed(self):
        self.search_timer.start()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def selected_project(self):

        return self.pager.record_at_row(self.table.currentRow())

    def add_project(self):

        form = ProjectForm(self.api, parent=self)

        if form.exec():
            self.load_projects()

    def edit_project(self):

        project = self.selected_project()

        if not project:
            QMessageBox.information(
                self, "No Selection", "Please select a project to edit."
            )
            return

        form = ProjectForm(self.api, project=project, parent=self)

        if form.exec():
            self.load_projects()

    def delete_project(self):

        project = self.selected_project()

        if not project:
            QMessageBox.information(
                self, "No Selection", "Please select a project to delete."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete project '{project.get('name', '')}'?\n"
            "This also removes its allocations.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, error = self.api.delete_project(project["id"])

        if ok:
            self.load_projects()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))

    def allocate_employee(self):

        project = self.selected_project()

        if not project:
            QMessageBox.information(
                self, "No Selection", "Please select a project."
            )
            return

        if not self.employees:
            QMessageBox.warning(
                self, "No Employees", "Add an employee before allocating."
            )
            return

        form = AllocateForm(self.api, project, self.employees, parent=self)

        if form.exec():
            self.load_projects()

    def view_history(self):

        project = self.selected_project()

        if not project:
            QMessageBox.information(
                self, "No Selection", "Please select a project."
            )
            return

        dialog = ProjectHistoryDialog(self.api, project, parent=self)
        dialog.exec()

        # Headcount may have changed after releasing allocations.
        self.load_projects()
