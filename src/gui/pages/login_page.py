"""Login page for UMU Advanced GUI."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..components.styled_button import StyledButton
from ..styles import (
    BRAND_400, BRAND_500, BRAND_600, BRAND_700, BRAND_50,
    DANGER_500, DANGER_50,
    INFO_500, INFO_50,
    SLATE_200, SLATE_400, SLATE_500, SLATE_800,
)


class LoginPage(QWidget):
    """Login page with centered card on gradient background."""

    login_success = pyqtSignal()

    def __init__(self, auth_service, config_service, parent=None) -> None:
        super().__init__(parent)
        self._auth_service = auth_service
        self._config_service = config_service
        self._setup_ui()

    def _setup_ui(self) -> None:
        # Main layout - centered
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Gradient background widget
        self.setStyleSheet(f"""
            LoginPage {{
                background: qradialgradient(cx:0.5, cy:0.3, radius:0.8,
                    stop:0 {BRAND_50}, stop:0.5 {BRAND_50}, stop:1 #F8FAFC);
            }}
        """)

        # Spacer left
        main_layout.addStretch()

        # Login card
        card = QFrame()
        card.setObjectName("login-card")
        card.setStyleSheet(f"""
            QFrame#login-card {{
                background-color: white;
                border: 1px solid {SLATE_200};
                border-radius: 16px;
            }}
        """)
        card.setFixedWidth(400)
        card.setMinimumHeight(480)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo icon (text-based placeholder)
        logo_label = QLabel("🎓")
        logo_label.setStyleSheet("font-size: 48px;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(logo_label)

        # Title
        title = QLabel("UMU Advanced")
        title.setObjectName("login-title")
        title.setStyleSheet(f"color: {SLATE_800}; font-size: 24px; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("企业数据管理平台")
        subtitle.setObjectName("login-subtitle")
        subtitle.setStyleSheet(f"color: {SLATE_500}; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(20)

        # Username input
        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("请输入UMU账号")
        self._username_input.setMinimumHeight(48)
        clear_action = QAction("×", self._username_input)
        clear_action.setToolTip("清除记录")
        clear_action.triggered.connect(self._on_clear_username)
        self._username_input.addAction(clear_action, QLineEdit.ActionPosition.TrailingPosition)
        card_layout.addWidget(self._username_input)

        # Password input
        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText("请输入密码")
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setMinimumHeight(48)
        self._password_input.returnPressed.connect(self._on_login)
        card_layout.addWidget(self._password_input)

        # Error label
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(f"""
            color: {DANGER_500};
            font-size: 13px;
            padding: 8px;
            background-color: {DANGER_50};
            border-radius: 6px;
        """)
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)
        card_layout.addWidget(self._error_label)

        # Login button
        self._login_btn = StyledButton("登录", StyledButton.PRIMARY)
        self._login_btn.setMinimumHeight(48)
        self._login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._login_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {BRAND_400}, stop:1 {BRAND_500});
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 600;
                color: white;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {BRAND_500}, stop:1 {BRAND_600});
            }}
            QPushButton:pressed {{
                background: {BRAND_700};
            }}
        """)
        self._login_btn.clicked.connect(self._on_login)
        card_layout.addWidget(self._login_btn)

        card_layout.addStretch()

        main_layout.addWidget(card)
        main_layout.addStretch()

    def _load_saved_username(self) -> None:
        """Fill username input with saved account if any, set focus accordingly."""
        configs = self._config_service.load_config()
        saved = configs.get("last_username", "")
        if saved:
            self._username_input.setText(saved)
            self._password_input.setFocus()
        else:
            self._username_input.setFocus()

    def _on_clear_username(self) -> None:
        """Clear saved username and empty the input."""
        self._username_input.clear()
        self._config_service.save_config({"last_username": ""})

    def _on_login(self) -> None:
        username = self._username_input.text().strip()
        password = self._password_input.text().strip()

        if not username or not password:
            self._show_error("账号和密码不能为空")
            return

        self._login_btn.setEnabled(False)
        self._login_btn.setText("登录中...")
        self._show_info("正在登录，请稍候...")

        # Force UI repaint so the progress hint is visible before blocking login call
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        success, error = self._auth_service.login(username, password)

        self._login_btn.setEnabled(True)
        self._login_btn.setText("登录")

        if success:
            self._config_service.save_config({"last_username": username})
            self._username_input.clear()
            self._password_input.clear()
            self._error_label.setVisible(False)
            self.login_success.emit()
        else:
            self._show_error(error)

    def _show_info(self, message: str) -> None:
        self._error_label.setText(f"  {message}")
        self._error_label.setStyleSheet(f"""
            color: {INFO_500};
            font-size: 13px;
            padding: 8px;
            background-color: {INFO_50};
            border-radius: 6px;
        """)
        self._error_label.setVisible(True)

    def _show_error(self, message: str) -> None:
        self._error_label.setText(f"  {message}")
        self._error_label.setStyleSheet(f"""
            color: {DANGER_500};
            font-size: 13px;
            padding: 8px;
            background-color: {DANGER_50};
            border-radius: 6px;
        """)
        self._error_label.setVisible(True)

    def reset(self) -> None:
        self._password_input.clear()
        self._error_label.setVisible(False)
        self._login_btn.setEnabled(True)
        self._login_btn.setText("登录")
        self._load_saved_username()
