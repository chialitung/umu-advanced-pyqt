"""Users sync page."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..components.empty_state import EmptyState
from ..components.progress_bar import ProgressBar
from ..components.styled_button import StyledButton
from ..styles import SLATE_500, SLATE_800


class UsersPage(QWidget):
    """Page for updating user list from UMU."""

    def __init__(self, auth_service, sync_service, parent=None) -> None:
        super().__init__(parent)
        self._auth_service = auth_service
        self._sync_service = sync_service
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title
        title = QLabel("更新用户列表")
        title.setStyleSheet(f"color: {SLATE_800}; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        # Description
        desc = QLabel("从 UMU 企业后台同步用户数据到本地数据库。同步过程中请勿关闭应用。")
        desc.setStyleSheet(f"color: {SLATE_500}; font-size: 14px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(16)

        # Non-admin warning
        self._warning_label = QLabel("⚠️ 您不是管理员，无法执行同步操作。")
        self._warning_label.setObjectName("non-admin-warning")
        self._warning_label.setVisible(False)
        layout.addWidget(self._warning_label)

        # Start button
        self._start_btn = StyledButton("开始更新", StyledButton.PRIMARY)
        self._start_btn.setMinimumHeight(44)
        self._start_btn.setMinimumWidth(140)
        layout.addWidget(self._start_btn)

        layout.addSpacing(16)

        # Progress bar
        self._progress = ProgressBar()
        layout.addWidget(self._progress)

        # Empty state (shown when not running)
        self._empty_state = EmptyState(
            icon="👥",
            title="用户数据已是最新",
            description='点击"开始更新"从 UMU 同步最新用户数据',
        )
        layout.addWidget(self._empty_state)

        layout.addStretch()

    def _connect_signals(self) -> None:
        self._start_btn.clicked.connect(self._on_start_sync)
        self._sync_service.progress_updated.connect(self._on_progress)
        self._sync_service.sync_finished.connect(self._on_finished)

    def refresh(self) -> None:
        is_admin = self._auth_service.is_admin()
        self._start_btn.setEnabled(is_admin)
        self._warning_label.setVisible(not is_admin)
        self._progress.reset()
        self._empty_state.setVisible(not self._sync_service.is_running("users"))

    def _on_start_sync(self) -> None:
        if self._sync_service.is_running("users"):
            self._sync_service.cancel("users")
            self._start_btn.setText("开始更新")
            self._start_btn.setVariant("primary")
            self._progress.set_value(0, "已取消")
            return
        serialized = self._auth_service.get_serialized_session()
        if not serialized:
            return
        self._start_btn.setText("取消同步")
        self._start_btn.setVariant("danger")
        self._empty_state.setVisible(False)
        self._sync_service.start_sync_users(serialized)

    def _on_progress(self, sync_type: str, percent: int, message: str) -> None:
        if sync_type == "users":
            self._progress.set_value(percent, message)

    def _on_finished(self, sync_type: str, success: bool, details: str) -> None:
        if sync_type == "users":
            self._start_btn.setText("开始更新")
            self._start_btn.setVariant("primary")
            self._empty_state.setVisible(True)
            self._progress.set_value(100 if success else 0, details)
