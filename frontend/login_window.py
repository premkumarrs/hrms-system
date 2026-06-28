from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QMessageBox
)

from api_service import APIService
from dashboard import Dashboard


class LoginWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.api = APIService()

        self.dashboard = None

        self.setWindowTitle("HRMS Login")

        self.resize(300, 200)

        layout = QVBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(
            "Username"
        )

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(
            "Password"
        )

        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.login_button = QPushButton(
            "Login"
        )

        self.login_button.clicked.connect(
            self.login
        )

        layout.addWidget(
            QLabel("Username")
        )

        layout.addWidget(
            self.username_input
        )

        layout.addWidget(
            QLabel("Password")
        )

        layout.addWidget(
            self.password_input
        )

        layout.addWidget(
            self.login_button
        )

        self.setLayout(layout)

    def login(self):

        username = self.username_input.text()

        password = self.password_input.text()

        success = self.api.login(
            username,
            password
        )

        if success:

            QMessageBox.information(
                self,
                "Success",
                "Login Successful"
            )

            self.dashboard = Dashboard(self.api, on_logout=self.return_to_login)

            self.dashboard.show()

            self.hide()

        else:

            QMessageBox.critical(
                self,
                "Error",
                self.api.last_error or "Invalid username or password."
            )

    def return_to_login(self):

        self.username_input.clear()
        self.password_input.clear()

        if self.dashboard:
            self.dashboard = None

        self.show()