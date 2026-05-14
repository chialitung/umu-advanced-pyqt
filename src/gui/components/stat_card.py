"""Stat card component."""

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QVBoxLayout, QWidget, QLabel

from ..styles import SLATE_500, SLATE_800


class StatCard(QWidget):
    """Card displaying a label and value statistic."""

    def __init__(self, label: str, value: str = "-", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("stat-card")
        self._setup_ui(label, value)
        self._setup_shadow()

    def _setup_ui(self, label: str, value: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("stat-value")
        self._value_label.setStyleSheet(f"color: {SLATE_800}; font-size: 24px; font-weight: 700;")
        layout.addWidget(self._value_label)

        self._label = QLabel(label)
        self._label.setObjectName("stat-label")
        self._label.setStyleSheet(f"color: {SLATE_500}; font-size: 12px; font-weight: 500;")
        layout.addWidget(self._label)

    def _setup_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)
