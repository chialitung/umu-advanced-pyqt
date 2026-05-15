"""Stat card component."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QVBoxLayout, QWidget, QLabel

from ..styles import SLATE_500, SLATE_800


class StatCard(QWidget):
    """Card displaying a label and value statistic.

    When *compact* is ``True`` the card renders without its own border,
    shadow or background — useful when it is placed inside a larger panel.
    """

    def __init__(self, label: str, value: str = "-", compact: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._compact = compact
        if not compact:
            self.setObjectName("stat-card")
        self._setup_ui(label, value)
        if not compact:
            self._setup_shadow()

    def _setup_ui(self, label: str, value: str) -> None:
        layout = QVBoxLayout(self)
        if self._compact:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
        else:
            layout.setContentsMargins(16, 24, 16, 24)
            layout.setSpacing(12)

        layout.addStretch()

        self._value_label = QLabel(value)
        self._value_label.setObjectName("stat-value")
        self._value_label.setStyleSheet(f"color: {SLATE_800}; font-size: 24px; font-weight: 700;")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

        self._label = QLabel(label)
        self._label.setObjectName("stat-label")
        self._label.setStyleSheet(f"color: {SLATE_500}; font-size: 12px; font-weight: 500;")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        layout.addStretch()

    def _setup_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)
