"""Toast notification system with ToastManager."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..styles import (
    DANGER_50,
    DANGER_600,
    INFO_50,
    INFO_600,
    SUCCESS_50,
    SUCCESS_600,
    WARNING_50,
    WARNING_600,
)


class Toast(QWidget):
    """Toast notification widget."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    COLORS = {
        SUCCESS: (SUCCESS_600, SUCCESS_50, SUCCESS_600),
        ERROR: (DANGER_600, DANGER_50, DANGER_600),
        WARNING: (WARNING_600, WARNING_50, WARNING_600),
        INFO: (INFO_600, INFO_50, INFO_600),
    }

    def __init__(self, message: str, toast_type: str = INFO, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui(message, toast_type)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(3000)

    def _setup_ui(self, message: str, toast_type: str) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        color, bg, border = self.COLORS.get(toast_type, self.COLORS[self.INFO])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 8, 12)
        layout.setSpacing(12)

        self._label = QLabel(message)
        self._label.setStyleSheet(f"""
            color: {color};
            font-size: 14px;
            font-weight: 500;
        """)
        self._label.setWordWrap(True)
        layout.addWidget(self._label, stretch=1)

        close_btn = QPushButton("✕")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {color};
                font-size: 12px;
                font-weight: 600;
                padding: 2px 6px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.05);
            }}
        """)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setStyleSheet(f"""
            Toast {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)

        self.setFixedWidth(360)

    def _on_timeout(self) -> None:
        self.close()


class ToastManager:
    """Manages toast notifications for a parent window."""

    def __init__(self, parent: QWidget) -> None:
        self._parent = parent
        self._toasts: list[Toast] = []

    def show(self, message: str, toast_type: str = Toast.INFO) -> None:
        """Show a toast notification."""
        toast = Toast(message, toast_type)
        toast.setParent(self._parent)

        # Position at bottom-right of parent
        parent_geo = self._parent.geometry()
        x = parent_geo.width() - toast.width() - 24
        base_y = parent_geo.height() - 80

        # Stack above existing toasts
        offset = len(self._toasts) * 56
        y = base_y - offset

        toast.move(x, y)
        toast.show()

        self._toasts.append(toast)

        # Remove from list when closed
        toast.destroyed.connect(lambda: self._remove_toast(toast))

    def _remove_toast(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._reposition_toasts()

    def _reposition_toasts(self) -> None:
        """Reposition all active toasts after one is removed."""
        parent_geo = self._parent.geometry()
        base_y = parent_geo.height() - 80

        for i, toast in enumerate(self._toasts):
            x = parent_geo.width() - toast.width() - 24
            y = base_y - i * 56
            toast.move(x, y)
