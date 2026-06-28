import sys

from PyQt6.QtWidgets import QApplication

from api_service import BASE_URL
from log_config import install_exception_hook, setup_logging
from login_window import LoginWindow

logger = setup_logging()
install_exception_hook(logger)

print(f"HRMS API BASE_URL: {BASE_URL}")
logger.info("HRMS API BASE_URL: %s", BASE_URL)

app = QApplication(sys.argv)

window = LoginWindow()
window.show()

logger.info("HRMS desktop client started")
sys.exit(app.exec())
