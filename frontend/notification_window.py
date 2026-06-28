from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox
)

from PyQt6.QtCore import Qt

from ui_helpers import loading, show_list_load_error
from table_utils import (
    setup_list_table,
    TablePager,
    build_pagination_bar,
    add_export_buttons,
)


FILTERS = [
    ("All", False),
    ("Unread only", True),
]


class NotificationWindow(QWidget):

    COLUMNS = ["ID", "Type", "Title", "Message", "Date", "Read"]

    def __init__(self, api, on_change=None):

        super().__init__()

        self.api = api
        # Optional callback to refresh the sidebar badge.
        self.on_change = on_change

        self.setWindowTitle("Notifications")
        self.resize(1000, 620)

        self.build_ui()
        self.load_notifications()

    def build_ui(self):

        layout = QVBoxLayout()

        title = QLabel("Notification Center")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        action_row = QHBoxLayout()

        self.filter_combo = QComboBox()
        for label, value in FILTERS:
            self.filter_combo.addItem(label, value)
        self.filter_combo.currentIndexChanged.connect(self.load_notifications)
        action_row.addWidget(self.filter_combo)

        action_row.addStretch()

        self.mark_read_button = QPushButton("Mark Selected Read")
        self.mark_read_button.clicked.connect(self.mark_selected_read)
        action_row.addWidget(self.mark_read_button)

        self.mark_all_button = QPushButton("Mark All Read")
        self.mark_all_button.clicked.connect(self.mark_all_read)
        action_row.addWidget(self.mark_all_button)

        self.generate_button = QPushButton("Generate Alerts")
        self.generate_button.clicked.connect(self.generate_alerts)
        action_row.addWidget(self.generate_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_notifications)
        action_row.addWidget(self.refresh_button)

        add_export_buttons(
            action_row,
            self,
            "notifications",
            lambda: self.COLUMNS,
            self._export_rows,
        )

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
        self.table.doubleClicked.connect(self.mark_selected_read)

        setup_list_table(self.table, id_column=0, stretch_column=3)

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

    def load_notifications(self):

        unread_only = self.filter_combo.currentData()

        with loading(self):
            data = self.api.get_notifications(unread=unread_only)

        if show_list_load_error(self, self.api, "notifications"):
            return

        self.pager.set_records(data, "notification(s)")
        self.populate_table()

        unread = sum(1 for r in self.pager.all_records if not r.get("is_read"))
        self.status_label.setText(
            f"{len(self.pager.all_records)} notification(s), {unread} unread"
        )

        if self.on_change:
            self.on_change()

    def populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.pager.page_records))
        for row, rec in enumerate(self.pager.page_records):
            values = [
                str(rec.get("id", "")),
                rec.get("type_display") or rec.get("notification_type", ""),
                rec.get("title", "") or "",
                rec.get("message", "") or "",
                (rec.get("created_at", "") or "")[:10],
                "Read" if rec.get("is_read") else "Unread",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

    def _export_rows(self):
        rows = []
        for rec in self.pager.all_records:
            rows.append([
                str(rec.get("id", "")),
                rec.get("type_display") or rec.get("notification_type", ""),
                rec.get("title", "") or "",
                rec.get("message", "") or "",
                (rec.get("created_at", "") or "")[:10],
                "Read" if rec.get("is_read") else "Unread",
            ])
        return rows

    def selected_record(self):
        return self.pager.record_at_row(self.table.currentRow())

    def mark_selected_read(self):
        rec = self.selected_record()
        if not rec:
            QMessageBox.information(
                self, "No Selection", "Select a notification."
            )
            return
        if rec.get("is_read"):
            return
        ok, result = self.api.mark_notification_read(rec["id"])
        if ok:
            self.load_notifications()
        else:
            QMessageBox.critical(self, "Failed", str(result))

    def mark_all_read(self):
        ok, result = self.api.mark_all_notifications_read()
        if ok:
            self.load_notifications()
        else:
            QMessageBox.critical(self, "Failed", str(result))

    def generate_alerts(self):
        ok, result = self.api.generate_notifications()
        if ok:
            self.load_notifications()
        else:
            QMessageBox.critical(self, "Failed", str(result))
