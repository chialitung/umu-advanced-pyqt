"""Empty state component for tables and lists."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..styles import SLATE_400, SLATE_500, SLATE_600, SLATE_800


class EmptyState(QWidget):
    """Placeholder shown when a table or list has no data."""

    def __init__(
        self,
        icon: str = "📭",
        title: str = "暂无数据",
        description: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._setup_ui(icon, title, description)

    def _setup_ui(self, icon: str, title: str, description: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon = QLabel(icon)
        self._icon.setStyleSheet(f"font-size: 48px;")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon)

        self._title = QLabel(title)
        self._title.setStyleSheet(f"color: {SLATE_800}; font-size: 16px; font-weight: 600;")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        if description:
            self._desc = QLabel(description)
            self._desc.setStyleSheet(f"color: {SLATE_500}; font-size: 14px;")
            self._desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._desc.setWordWrap(True)
            layout.addWidget(self._desc)

        layout.addStretch()

    def set_icon(self, icon: str) -> None:
        self._icon.setText(icon)

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_description(self, description: str) -> None:
        self._desc.setText(description)
        self._desc.setVisible(bool(description))
