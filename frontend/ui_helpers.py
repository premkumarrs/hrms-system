"""Shared UI helpers: error dialogs and loading feedback."""

from contextlib import contextmanager

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox


def show_error(parent, title, message):
    QMessageBox.critical(parent, title, message or "An unexpected error occurred.")


def show_warning(parent, title, message):
    QMessageBox.warning(parent, title, message or "Please review and try again.")


def show_info(parent, title, message):
    QMessageBox.information(parent, title, message)


def show_api_error(parent, api, title="Request Failed", fallback=None):
    message = (api.last_error if api else None) or fallback or "Could not complete the request."
    show_error(parent, title, message)


def show_list_load_error(parent, api, entity_name="records"):
    if api and getattr(api, "last_list_ok", True):
        return False
    show_api_error(
        parent,
        api,
        title="Load Failed",
        fallback=f"Could not load {entity_name}. Check your connection and try again.",
    )
    return True


@contextmanager
def loading(parent, message="Loading..."):
    """Show a busy cursor while a blocking API call runs."""

    app = QApplication.instance()
    if parent:
        parent.setEnabled(False)
    if app:
        app.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        if app:
            app.restoreOverrideCursor()
        if parent:
            parent.setEnabled(True)
