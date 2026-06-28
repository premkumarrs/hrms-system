from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QPushButton,
)


class OnboardingChecklistDialog(QDialog):

    def __init__(self, checklist, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Onboarding Document Checklist")
        self.resize(560, 380)

        layout = QVBoxLayout()

        percent = checklist.get("completion_percent", 0)
        completed = checklist.get("completed_count", 0)
        total = checklist.get("total_count", 0)
        missing = checklist.get("missing_documents") or []

        summary = QLabel(
            f"Completion: {percent}% ({completed}/{total})"
        )
        summary.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(summary)

        if missing:
            layout.addWidget(
                QLabel("Missing: " + ", ".join(missing))
            )
        else:
            layout.addWidget(QLabel("All required documents are uploaded."))

        table = QTableWidget()
        items = checklist.get("items") or []
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Required Document", "Status", "Uploaded File"])
        table.setRowCount(len(items))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        for row, item in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(item.get("label", "")))
            status = "Uploaded" if item.get("uploaded") else "Missing"
            table.setItem(row, 1, QTableWidgetItem(status))
            title = item.get("document_title") or "-"
            table.setItem(row, 2, QTableWidgetItem(title))

        layout.addWidget(table)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)
