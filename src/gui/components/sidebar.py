"""Sidebar navigation component."""

from __future__ import annotations

from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QVBoxLayout, QWidget

from ..icons import Icon
from ..styles import BRAND_50, BRAND_500, BRAND_600, SLATE_200, SLATE_500, SLATE_600, SLATE_800


class Sidebar(QWidget):
    """Left navigation sidebar."""

    page_changed = pyqtSignal(str)
    logout_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 24, 0, 16)
        layout.setSpacing(0)

        # Brand header
        brand_widget = QWidget()
        brand_layout = QVBoxLayout(brand_widget)
        brand_layout.setContentsMargins(20, 0, 20, 0)
        brand_layout.setSpacing(4)

        title = QLabel("UMU Advanced")
        title.setObjectName("brand-title")
        brand_layout.addWidget(title)

        subtitle = QLabel("企业数据管理平台")
        subtitle.setObjectName("brand-subtitle")
        brand_layout.addWidget(subtitle)

        layout.addWidget(brand_widget)
        layout.addSpacing(32)

        # Navigation buttons
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        nav_items = [
            ("governance", "培训数据治理", Icon.GOVERNANCE),
            ("courses", "更新课程信息", Icon.COURSES),
            ("users", "更新用户列表", Icon.USERS),
            ("config", "治理规则配置", Icon.CONFIG),
        ]

        for page_id, label, icon_name in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav-btn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            icon = Icon.get(icon_name, color="#64748B")
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QtCore.QSize(16, 16))
            btn.clicked.connect(lambda checked, pid=page_id: self.page_changed.emit(pid))
            self._button_group.addButton(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # User info area
        self._user_widget = QWidget()
        user_layout = QVBoxLayout(self._user_widget)
        user_layout.setContentsMargins(20, 12, 20, 12)
        user_layout.setSpacing(4)

        self._user_name_label = QLabel("未登录")
        self._user_name_label.setObjectName("user-name")
        user_layout.addWidget(self._user_name_label)

        self._admin_badge = QLabel("管理员")
        self._admin_badge.setObjectName("admin-badge")
        self._admin_badge.setVisible(False)
        user_layout.addWidget(self._admin_badge)

        # Logout button
        from ..styles import DANGER_50, DANGER_600
        self._logout_btn = QPushButton("退出登录")
        self._logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px 0px;
                text-align: left;
                font-size: 13px;
                font-weight: 500;
                color: {DANGER_600};
            }}
            QPushButton:hover {{
                background-color: {DANGER_50};
            }}
        """)
        self._logout_btn.clicked.connect(self.logout_clicked.emit)
        user_layout.addWidget(self._logout_btn)

        layout.addWidget(self._user_widget)

    def set_page(self, page_id: str) -> None:
        for btn in self._button_group.buttons():
            if btn.text() == self._get_label(page_id):
                btn.setChecked(True)
                break

    def _get_label(self, page_id: str) -> str:
        mapping = {
            "governance": "培训数据治理",
            "courses": "更新课程信息",
            "users": "更新用户列表",
            "config": "治理规则配置",
        }
        return mapping.get(page_id, "")

    def set_user(self, username: str, is_admin: bool) -> None:
        self._user_name_label.setText(username)
        self._admin_badge.setVisible(is_admin)
