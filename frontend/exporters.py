"""Shared CSV / Excel export helpers for table data."""

import csv

from PyQt6.QtWidgets import QFileDialog, QMessageBox


def export_csv(parent, default_name, columns, rows):

    if not rows:
        QMessageBox.information(parent, "No Data", "Nothing to export.")
        return

    path, _ = QFileDialog.getSaveFileName(
        parent, "Export CSV", f"{default_name}.csv", "CSV (*.csv)"
    )

    if not path:
        return

    try:
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(rows)
    except OSError as exc:
        QMessageBox.critical(parent, "Export Failed", str(exc))
        return

    QMessageBox.information(parent, "Exported", "CSV exported successfully.")


def export_excel(parent, default_name, columns, rows):

    if not rows:
        QMessageBox.information(parent, "No Data", "Nothing to export.")
        return

    try:
        from openpyxl import Workbook
    except ImportError:
        QMessageBox.critical(
            parent, "Excel Unavailable",
            "openpyxl is not installed. Use CSV export instead."
        )
        return

    path, _ = QFileDialog.getSaveFileName(
        parent, "Export Excel", f"{default_name}.xlsx", "Excel (*.xlsx)"
    )

    if not path:
        return

    try:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Export"
        sheet.append(list(columns))
        for row in rows:
            sheet.append(list(row))
        workbook.save(path)
    except (OSError, ValueError) as exc:
        QMessageBox.critical(parent, "Export Failed", str(exc))
        return

    QMessageBox.information(parent, "Exported", "Excel exported successfully.")
