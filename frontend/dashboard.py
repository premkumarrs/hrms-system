from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QPushButton,
    QMessageBox,
    QGridLayout,
)

from ui_helpers import loading, show_api_error

from bar_chart import BarChartWidget
from department_window import DepartmentWindow
from designation_window import DesignationWindow
from employee_window import EmployeeWindow
from attendance_window import AttendanceWindow
from leave_window import LeaveWindow
from permission_window import PermissionWindow
from project_window import ProjectWindow
from document_window import DocumentWindow
from lifecycle_window import LifecycleWindow
from directory_window import DirectoryWindow
from self_service_window import SelfServiceWindow
from report_window import ReportWindow
from payroll_window import PayrollWindow
from notification_window import NotificationWindow


class Dashboard(QWidget):
    """Main application window.

    A single window holding a sidebar and a QStackedWidget. Menu clicks
    switch the visible page; no separate windows or popups are opened.
    """

    # Sidebar labels paired with the page index they activate.
    MENU_ITEMS = [
        "Dashboard",
        "Employees",
        "Departments",
        "Designations",
        "Attendance",
        "Leaves",
        "Permissions",
        "Projects",
        "Documents",
        "Lifecycle",
        "Directory",
        "Self Service",
        "Reports",
        "Payroll",
        "Notifications",
    ]

    def __init__(self, api, on_logout=None):

        super().__init__()

        self.api = api
        self.on_logout = on_logout
        self.stat_value_labels = {}
        self.dashboard_charts = {}

        self.api.on_session_expired = self.handle_session_expired

        self.setWindowTitle("HRMS Dashboard")

        self.resize(1200, 700)

        self.build_ui()

    def build_ui(self):

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self.build_sidebar())
        main_layout.addWidget(self.build_content())

        self.setLayout(main_layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-family: Segoe UI;
            }
        """)

        self._select_first_visible_menu()

        self.refresh_badge()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def build_sidebar(self):

        sidebar = QFrame()
        sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout()

        title = QLabel("HRMS")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            padding: 20px;
        """)

        sidebar_layout.addWidget(title)

        role_text = self.api.role or "User"
        role_label = QLabel(f"Role: {role_text}")
        role_label.setStyleSheet("""
            color: #9aa0c0;
            font-size: 12px;
            padding: 0px 20px 10px 20px;
        """)
        sidebar_layout.addWidget(role_label)

        self.menu = QListWidget()

        for label in self.MENU_ITEMS:
            self.menu.addItem(label)

        for row, label in enumerate(self.MENU_ITEMS):
            if not self._menu_visible(label):
                self.menu.setRowHidden(row, True)

        # currentRowChanged keeps the sidebar selection and the stacked
        # page index in sync (covers clicks and keyboard navigation).
        self.menu.currentRowChanged.connect(self.on_menu_changed)

        sidebar_layout.addWidget(self.menu)

        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setStyleSheet("""
            margin: 10px 20px 20px 20px;
            padding: 8px;
            background-color: #3d3d5c;
            border: none;
            color: white;
        """)
        sidebar_layout.addWidget(self.logout_button)

        sidebar.setLayout(sidebar_layout)

        sidebar.setStyleSheet("""
            background-color: #1e1e2f;
            color: white;
        """)

        return sidebar

    def _menu_visible(self, label):
        """Hide modules the current role is not allowed to access."""

        role = (self.api.role or "").upper()

        if self.api.can("full_access"):
            return True

        employee_menu = {
            "Dashboard",
            "Directory",
            "Self Service",
            "Notifications",
        }
        manager_menu = employee_menu | {
            "Attendance",
            "Leaves",
            "Permissions",
            "Projects",
            "Reports",
            "Payroll",
        }

        if role == "EMPLOYEE":
            return label in employee_menu

        if role == "MANAGER":
            return label in manager_menu

        permission_rules = {
            "Employees": "manage_employees",
            "Departments": "manage_departments",
            "Designations": "manage_designations",
            "Documents": "manage_documents",
            "Lifecycle": "manage_lifecycle",
            "Projects": "view_projects",
            "Reports": "view_reports",
            "Payroll": "view_payroll",
        }

        permission = permission_rules.get(label)
        if permission:
            return self.api.can(permission)

        return False

    # ------------------------------------------------------------------
    # Content area (stacked pages)
    # ------------------------------------------------------------------

    def build_content(self):

        content = QFrame()

        content_layout = QVBoxLayout()

        self.stack = QStackedWidget()

        # Index order must match MENU_ITEMS.
        self.stack.addWidget(self.build_dashboard_page())          # 0
        self.stack.addWidget(EmployeeWindow(self.api))             # 1
        self.stack.addWidget(DepartmentWindow(self.api))           # 2
        self.stack.addWidget(DesignationWindow(self.api))          # 3
        self.stack.addWidget(AttendanceWindow(self.api))           # 4
        self.stack.addWidget(LeaveWindow(self.api))                # 5
        self.stack.addWidget(PermissionWindow(self.api))           # 6
        self.stack.addWidget(ProjectWindow(self.api))              # 7
        self.stack.addWidget(DocumentWindow(self.api))             # 8
        self.stack.addWidget(LifecycleWindow(self.api))            # 9
        self.stack.addWidget(DirectoryWindow(self.api))            # 10
        self.stack.addWidget(SelfServiceWindow(self.api))          # 11
        self.stack.addWidget(ReportWindow(self.api))               # 12
        self.stack.addWidget(PayrollWindow(self.api))              # 13
        self.stack.addWidget(
            NotificationWindow(self.api, on_change=self.refresh_badge)  # 14
        )

        content_layout.addWidget(self.stack)

        content.setLayout(content_layout)

        content.setStyleSheet("""
            background-color: #121212;
            color: white;
        """)

        return content

    def _select_first_visible_menu(self):
        """Select the first menu row the current role is allowed to see."""

        for row, label in enumerate(self.MENU_ITEMS):
            if self._menu_visible(label):
                self.menu.setCurrentRow(row)
                return

        self.menu.setCurrentRow(0)

    def _select_nearest_visible_menu(self, from_index):
        """Move selection away from a hidden row (keyboard navigation guard)."""

        for delta in range(1, len(self.MENU_ITEMS)):
            for candidate in (from_index - delta, from_index + delta):
                if 0 <= candidate < len(self.MENU_ITEMS):
                    if self._menu_visible(self.MENU_ITEMS[candidate]):
                        self.menu.blockSignals(True)
                        self.menu.setCurrentRow(candidate)
                        self.menu.blockSignals(False)
                        self.on_menu_changed(candidate)
                        return

    def on_menu_changed(self, index):

        if index < 0 or index >= len(self.MENU_ITEMS):
            return

        label = self.MENU_ITEMS[index]
        if not self._menu_visible(label):
            self._select_nearest_visible_menu(index)
            return

        self.stack.setCurrentIndex(index)

        if index == 0:
            self.refresh_dashboard()

        if index == self.MENU_ITEMS.index("Notifications"):
            self.refresh_badge()

    def logout(self):

        self.api.logout()

        if self.on_logout:
            self.on_logout()

        self.close()

    def handle_session_expired(self):

        QMessageBox.warning(
            self,
            "Session Expired",
            "Your session has expired. Please log in again."
        )
        self.api.logout()

        if self.on_logout:
            self.on_logout()

        self.close()

    def refresh_badge(self):
        """Update the Notifications sidebar label with the unread count."""

        try:
            count = self.api.get_unread_count()
        except Exception:
            count = 0

        label = "Notifications"
        if count:
            label = f"Notifications ({count})"

        row = self.MENU_ITEMS.index("Notifications")
        item = self.menu.item(row)
        if item is not None:
            item.setText(label)

    # ------------------------------------------------------------------
    # Dashboard page
    # ------------------------------------------------------------------

    def build_dashboard_page(self):

        page = QWidget()

        content_layout = QVBoxLayout()

        header = QLabel("Dashboard Overview")

        header.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            padding: 10px;
        """)

        content_layout.addWidget(header)

        cards_layout = QHBoxLayout()

        cards = [
            ("total_employees", "Total Employees"),
            ("active_employees", "Active Employees"),
            ("present_today", "Present Today"),
            ("absent_today", "Absent Today"),
            ("on_leave", "On Leave"),
            ("active_projects", "Active Projects"),
        ]

        for key, title_text in cards:

            card = QFrame()

            card.setFixedHeight(120)

            card.setStyleSheet("""
                background-color: #2d2d44;
                border-radius: 10px;
                color: white;
            """)

            card_layout = QVBoxLayout()

            title_label = QLabel(title_text)

            title_label.setStyleSheet("""
                font-size: 18px;
            """)

            value_label = QLabel("0")

            value_label.setStyleSheet("""
                font-size: 32px;
                font-weight: bold;
            """)

            self.stat_value_labels[key] = value_label

            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)

            card.setLayout(card_layout)

            cards_layout.addWidget(card)

        content_layout.addLayout(cards_layout)

        insights_title = QLabel("Insights")
        insights_title.setStyleSheet(
            "font-size: 20px; font-weight: bold; padding: 16px 10px 8px 10px;"
        )
        content_layout.addWidget(insights_title)

        insights_grid = QGridLayout()
        self.insight_lists = {}

        insight_specs = [
            ("pending", "Pending Approvals"),
            ("birthdays", "Upcoming Birthdays"),
            ("anniversaries", "Upcoming Anniversaries"),
            ("notifications", "Recent Notifications"),
        ]

        for index, (key, label) in enumerate(insight_specs):
            frame = QFrame()
            frame.setStyleSheet("background-color: #2d2d44; border-radius: 8px;")
            frame_layout = QVBoxLayout()
            frame_layout.addWidget(QLabel(label))
            widget = QListWidget()
            widget.setMaximumHeight(120)
            self.insight_lists[key] = widget
            frame_layout.addWidget(widget)
            frame.setLayout(frame_layout)
            insights_grid.addWidget(frame, index // 2, index % 2)

        content_layout.addLayout(insights_grid)

        charts_title = QLabel("Analytics")
        charts_title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 16px 10px 8px 10px;")
        content_layout.addWidget(charts_title)

        charts_grid = QGridLayout()

        chart_specs = [
            ("attendance", "Attendance Trend (Present)"),
            ("leave", "Leave Trend (Approved)"),
            ("headcount", "Project Headcount"),
            ("attrition", "Attrition Trend"),
            ("deviation", "Attendance Deviation (Cycle)"),
        ]

        for index, (key, label) in enumerate(chart_specs):
            frame = QFrame()
            frame.setStyleSheet("background-color: #2d2d44; border-radius: 8px;")
            frame_layout = QVBoxLayout()

            chart_label = QLabel(label)
            chart_label.setStyleSheet("font-size: 14px; padding: 6px;")
            frame_layout.addWidget(chart_label)

            chart = BarChartWidget()
            self.dashboard_charts[key] = chart
            frame_layout.addWidget(chart)

            frame.setLayout(frame_layout)
            charts_grid.addWidget(frame, index // 2, index % 2)

        content_layout.addLayout(charts_grid)

        page.setLayout(content_layout)

        self.refresh_dashboard()

        return page

    def refresh_dashboard(self):

        with loading(self):
            stats = self.api.get_dashboard_stats()
            analytics = self.api.get_dashboard_analytics()
            insights = self.api.get_dashboard_insights()

        if stats is None:
            show_api_error(
                self, self.api, "Dashboard Error",
                fallback="Could not load dashboard statistics.",
            )
            stats = {}
        if analytics is None:
            show_api_error(
                self, self.api, "Dashboard Error",
                fallback="Could not load dashboard analytics.",
            )
            analytics = {}
        if insights is None:
            insights = {}

        for key, label in self.stat_value_labels.items():
            label.setText(str(stats.get(key, 0)))

        self._populate_insight_list(
            "pending",
            [
                f"Pending leaves: {insights.get('pending_leaves', 0)}",
                f"Pending permissions: {insights.get('pending_permissions', 0)}",
            ] if insights else ["No data"],
        )
        self._populate_insight_list(
            "birthdays",
            [
                f"{row.get('date', '')} — {row.get('employee', '')} ({row.get('employee_code', '')})"
                for row in insights.get("upcoming_birthdays", [])
            ] or ["No upcoming birthdays"],
        )
        self._populate_insight_list(
            "anniversaries",
            [
                f"{row.get('date', '')} — {row.get('employee', '')} ({row.get('years', 0)} yr)"
                for row in insights.get("upcoming_anniversaries", [])
            ] or ["No upcoming anniversaries"],
        )
        self._populate_insight_list(
            "notifications",
            [
                f"{row.get('title', 'Notification')}"
                for row in insights.get("recent_notifications", [])
            ] or ["No recent notifications"],
        )

        attendance = analytics.get("attendance_trend", [])
        self.dashboard_charts["attendance"].set_data([
            (row["date"][-5:], row.get("present", 0)) for row in attendance
        ])

        leave = analytics.get("leave_trend", [])
        self.dashboard_charts["leave"].set_data([
            (row["month"], row.get("approved", 0)) for row in leave
        ])

        headcount = analytics.get("project_headcount", [])
        self.dashboard_charts["headcount"].set_data([
            (row["project"], row.get("headcount", 0)) for row in headcount
        ])

        attrition = analytics.get("attrition_trend", [])
        self.dashboard_charts["attrition"].set_data([
            (row["month"], row.get("count", 0)) for row in attrition
        ])

        deviation = analytics.get("attendance_deviation", [])
        self.dashboard_charts["deviation"].set_data([
            (row["employee"][:10], abs(row.get("deviation_hours", 0)))
            for row in deviation
        ])

    def _populate_insight_list(self, key, lines):
        widget = self.insight_lists.get(key)
        if widget is None:
            return
        widget.clear()
        for line in lines:
            widget.addItem(QListWidgetItem(str(line)))
