import os

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
    QFileDialog,
    QMessageBox
)

from PyQt6.QtCore import Qt, QTimer

from document_form import DocumentUploadForm
from document_generate_form import DocumentGenerateForm
from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
    populate_employee_filter,
)


class DocumentWindow(QWidget):

    COLUMNS = [
        "ID",
        "Code",
        "Employee",
        "Category",
        "Title",
        "File",
        "Uploaded",
    ]

    def __init__(self, api):

        super().__init__()

        self.api = api

        self.employees = []

        self.categories = []

        self.categories = []

        self.setWindowTitle("Documents Management")

        self.resize(1100, 660)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self.load_documents)

        self.build_ui()

        self.load_lookups()

        self.load_documents()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Documents Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # --- Filter / search row ---
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by title or employee..."
        )
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_row.addWidget(self.search_input)

        self.employee_filter = QComboBox()
        self.employee_filter.addItem("All Employees", None)
        self.employee_filter.currentIndexChanged.connect(self.load_documents)
        filter_row.addWidget(self.employee_filter)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        self.category_filter.currentIndexChanged.connect(self.load_documents)
        filter_row.addWidget(self.category_filter)

        layout.addLayout(filter_row)

        # --- Action button row ---
        action_row = QHBoxLayout()

        self.upload_button = QPushButton("Upload Document")
        self.upload_button.clicked.connect(self.upload_document)
        action_row.addWidget(self.upload_button)

        self.generate_button = QPushButton("Generate Letter")
        self.generate_button.clicked.connect(self.generate_letter)
        action_row.addWidget(self.generate_button)

        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_document)
        action_row.addWidget(self.download_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_document)
        action_row.addWidget(self.delete_button)

        action_row.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        action_row.addWidget(self.refresh_button)

        add_export_buttons(
            action_row, self, "documents", lambda: self.COLUMNS, self._export_rows
        )

        # Only HR can upload/delete/generate; everyone may download.
        can_manage = self.api.can("manage_documents")
        self.upload_button.setVisible(can_manage)
        self.generate_button.setVisible(can_manage)
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
        self.table.doubleClicked.connect(self.download_document)

        setup_list_table(self.table, id_column=0, stretch_column=4)

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

    def load_lookups(self):

        with loading(self):
            self.employees = self.api.get_employees()
            self.categories = self.api.get_document_categories()

        if show_list_load_error(self, self.api, "lookup data"):
            return

        populate_employee_filter(self.employee_filter, self.employees)

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories", None)
        for cat in self.categories:
            self.category_filter.addItem(cat["name"], cat["id"])
        self.category_filter.blockSignals(False)

    def build_filters(self):

        filters = {}

        search = self.search_input.text().strip()
        if search:
            filters["search"] = search

        employee = self.employee_filter.currentData()
        if employee:
            filters["employee"] = employee

        category = self.category_filter.currentData()
        if category:
            filters["category"] = category

        return filters

    def load_documents(self):

        with loading(self):
            data = self.api.get_documents(self.build_filters())

        if show_list_load_error(self, self.api, "documents"):
            return

        self.pager.set_records(data, "document(s)")
        self.populate_table()

    def refresh_all(self):
        self.load_lookups()
        self.load_documents()

    def populate_table(self):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))

        for row, doc in enumerate(self.pager.page_records):

            values = [
                str(doc.get("id", "")),
                doc.get("employee_code", "") or "",
                doc.get("employee_name", "") or "",
                doc.get("category_name") or "-",
                doc.get("title", "") or "",
                doc.get("file_name", "") or "",
                (doc.get("uploaded_at", "") or "")[:10],
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for doc in self.pager.all_records:
            rows.append([
                str(doc.get("id", "")),
                doc.get("employee_code", "") or "",
                doc.get("employee_name", "") or "",
                doc.get("category_name") or "-",
                doc.get("title", "") or "",
                doc.get("file_name", "") or "",
                (doc.get("uploaded_at", "") or "")[:10],
            ])
        return rows

    def on_search_changed(self):
        self.search_timer.start()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def selected_document(self):

        return self.pager.record_at_row(self.table.currentRow())

    def upload_document(self):

        if not self.employees:
            QMessageBox.warning(
                self, "No Employees",
                "Add an employee before uploading documents."
            )
            return

        form = DocumentUploadForm(
            self.api, self.employees, self.categories, parent=self
        )

        if form.exec():
            self.load_documents()

    def generate_letter(self):

        if not self.employees:
            QMessageBox.warning(
                self, "No Employees",
                "Add an employee before generating letters."
            )
            return

        form = DocumentGenerateForm(self.api, self.employees, parent=self)

        if form.exec():
            doc = getattr(form, "generated", None)
            self.load_documents()
            if doc:
                QMessageBox.information(
                    self,
                    "Letter Generated",
                    f"Saved: {doc.get('title', 'Document')}\n"
                    "Select the row and click Download to save a local copy.",
                )

    def download_document(self):

        doc = self.selected_document()

        if not doc:
            QMessageBox.information(
                self, "No Selection", "Please select a document to download."
            )
            return

        suggested = doc.get("file_name") or f"document_{doc['id']}"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Document As", suggested
        )

        if not save_path:
            return

        ok, error = self.api.download_document(doc["id"], save_path)

        if ok:
            QMessageBox.information(
                self, "Downloaded",
                f"Saved to:\n{os.path.basename(save_path)}"
            )
        else:
            QMessageBox.critical(self, "Download Failed", str(error))

    def delete_document(self):

        doc = self.selected_document()

        if not doc:
            QMessageBox.information(
                self, "No Selection", "Please select a document to delete."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete document '{doc.get('title', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, error = self.api.delete_document(doc["id"])

        if ok:
            self.load_documents()
        else:
            QMessageBox.critical(self, "Delete Failed", str(error))
