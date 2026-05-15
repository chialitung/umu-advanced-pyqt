"""Main window with sidebar and stacked pages."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QWidget

from .components.sidebar import Sidebar
from .components.toast import ToastManager
from .pages.config_page import ConfigPage
from .pages.courses_page import CoursesPage
from .pages.governance_page import GovernancePage
from .pages.login_page import LoginPage
from .pages.users_page import UsersPage
from lms_client.storage.database import DatabaseManager

from .services.auth_service import AuthService
from .services.config_service import ConfigService
from .services.governance_service import GovernanceService
from .services.sync_service import SyncService
from .styles import SLATE_50


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UMU Advanced - 企业数据管理平台")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Services
        self._auth_service = AuthService()
        self._sync_service = SyncService()
        self._governance_service = GovernanceService()
        self._config_service = ConfigService()

        # Database migration
        db_mgr = DatabaseManager()
        db_mgr.create_tables()
        db_mgr.migrate_columns()
        db_mgr.migrate_constraints()

        # Toast manager
        self._toast_manager = ToastManager(self)

        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()

        # Show login initially
        self._show_login()

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(f"background-color: {SLATE_50};")
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.setVisible(False)
        layout.addWidget(self._sidebar)

        # Pages stack
        self._stack = QStackedWidget()

        # Login page
        self._login_page = LoginPage(self._auth_service, self._config_service)
        self._stack.addWidget(self._login_page)

        # Dashboard pages container
        self._dashboard = QWidget()
        dashboard_layout = QHBoxLayout(self._dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(0)

        # Inner stack for dashboard pages
        self._page_stack = QStackedWidget()

        # Users page (accessible via URL hash in web, add as hidden nav for now)
        self._users_page = UsersPage(self._auth_service, self._sync_service)
        self._page_stack.addWidget(self._users_page)

        # Courses page
        self._courses_page = CoursesPage(self._auth_service, self._sync_service)
        self._page_stack.addWidget(self._courses_page)

        # Governance page
        self._governance_page = GovernancePage(
            self._auth_service, self._sync_service, self._governance_service,
            show_toast=self.toast,
        )
        self._page_stack.addWidget(self._governance_page)

        # Config page
        self._config_page = ConfigPage(
            self._auth_service, self._config_service,
            show_toast=self.toast,
        )
        self._page_stack.addWidget(self._config_page)

        dashboard_layout.addWidget(self._page_stack)
        self._stack.addWidget(self._dashboard)

        layout.addWidget(self._stack, stretch=1)

        # Page mapping
        self._page_map = {
            "users": 0,
            "courses": 1,
            "governance": 2,
            "config": 3,
        }

    def _connect_signals(self) -> None:
        self._login_page.login_success.connect(self._on_login_success)
        self._auth_service.auth_changed.connect(self._on_auth_changed)
        self._sidebar.page_changed.connect(self._on_page_changed)
        self._sidebar.logout_clicked.connect(self._auth_service.logout)

    def _show_login(self) -> None:
        self._sidebar.setVisible(False)
        self._stack.setCurrentIndex(0)
        self._login_page.reset()

    def _on_login_success(self) -> None:
        self._sidebar.setVisible(True)
        self._sidebar.set_user(
            self._auth_service.get_username(),
            self._auth_service.is_admin(),
            self._auth_service.get_role_type(),
        )
        self._stack.setCurrentIndex(1)
        self._switch_page("governance")
        self._refresh_current_page()

    def _on_auth_changed(self, is_authenticated: bool) -> None:
        if not is_authenticated:
            self._show_login()

    def _on_page_changed(self, page_id: str) -> None:
        self._switch_page(page_id)

    def _switch_page(self, page_id: str) -> None:
        index = self._page_map.get(page_id, 2)
        self._page_stack.setCurrentIndex(index)
        self._sidebar.set_page(page_id)
        self._refresh_current_page()

    def _refresh_current_page(self) -> None:
        index = self._page_stack.currentIndex()
        if index == 0:
            self._users_page.refresh()
        elif index == 1:
            self._courses_page.refresh()
        elif index == 2:
            self._governance_page.refresh()
        elif index == 3:
            self._config_page.refresh()

    def _setup_shortcuts(self) -> None:
        from PyQt6.QtGui import QAction, QKeySequence

        # Ctrl+1/2/3/4 for page switching
        for idx, page_id in enumerate(("governance", "courses", "users", "config"), 1):
            action = QAction(self)
            action.setShortcut(QKeySequence(f"Ctrl+{idx}"))
            action.triggered.connect(lambda checked, pid=page_id: self._switch_page(pid))
            self.addAction(action)

    def toast(self, message: str, toast_type: str = "info") -> None:
        """Show a toast notification."""
        self._toast_manager.show(message, toast_type)

    def closeEvent(self, event) -> None:
        """Confirm before closing."""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出程序吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._auth_service.close_client()
            event.accept()
        else:
            event.ignore()
