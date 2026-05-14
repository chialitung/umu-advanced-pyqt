"""Styled button component."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QPushButton

from ..styles import (
    BRAND_400,
    BRAND_500,
    BRAND_600,
    BRAND_700,
    DANGER_50,
    DANGER_500,
    DANGER_600,
    DANGER_700,
    SLATE_50,
    SLATE_100,
    SLATE_200,
    SLATE_300,
    SLATE_500,
    SLATE_600,
    SLATE_700,
    SLATE_800,
)


class StyledButton(QPushButton):
    """Brand-styled button with primary/secondary/ghost variants."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    GHOST = "ghost"
    DANGER = "danger"

    def __init__(self, text: str = "", variant: str = PRIMARY, parent=None) -> None:
        super().__init__(text, parent)
        self._variant = variant
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._apply_style()

    def _apply_style(self) -> None:
        if self._variant == self.DANGER:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: white;
                    border: 1.5px solid {DANGER_500};
                    border-radius: 8px;
                    padding: 10px 24px;
                    font-size: 14px;
                    font-weight: 600;
                    color: {DANGER_500};
                }}
                QPushButton:hover {{
                    background-color: {DANGER_50};
                }}
                QPushButton:pressed {{
                    background-color: {DANGER_500};
                    color: white;
                }}
            """)
        elif self._variant == self.PRIMARY:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {BRAND_400}, stop:1 {BRAND_500});
                    border: none;
                    border-radius: 8px;
                    padding: 10px 24px;
                    font-size: 14px;
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
                QPushButton:disabled {{
                    background: {SLATE_300};
                    color: {SLATE_500};
                }}
            """)
        elif self._variant == self.SECONDARY:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: white;
                    border: 1.5px solid {SLATE_200};
                    border-radius: 8px;
                    padding: 10px 24px;
                    font-size: 14px;
                    font-weight: 600;
                    color: {SLATE_700};
                }}
                QPushButton:hover {{
                    border-color: {SLATE_300};
                    background-color: {SLATE_50};
                }}
                QPushButton:pressed {{
                    background-color: {SLATE_100};
                }}
            """)
        else:  # GHOST
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {SLATE_50};
                    border: 1px solid {SLATE_200};
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 13px;
                    font-weight: 500;
                    color: {SLATE_600};
                }}
                QPushButton:hover {{
                    background-color: {SLATE_100};
                    border-color: {SLATE_300};
                    color: {SLATE_800};
                }}
                QPushButton:pressed {{
                    background-color: {SLATE_200};
                }}
            """)

    def set_variant(self, variant: str) -> None:
        self._variant = variant
        self._apply_style()
