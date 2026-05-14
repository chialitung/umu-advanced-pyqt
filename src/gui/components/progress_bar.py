"""Custom progress bar component."""

from __future__ import annotations

from PyQt6.QtWidgets import QProgressBar, QVBoxLayout, QWidget, QLabel

from ..styles import BRAND_500, SLATE_200, SLATE_500


class ProgressBar(QWidget):
    """Styled progress bar with percentage label."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._label = QLabel("")
        self._label.setStyleSheet(f"color: {SLATE_500}; font-size: 13px;")
        layout.addWidget(self._label)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        self._progress.setMaximum(100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self.setVisible(False)

    def set_value(self, value: int, message: str = "") -> None:
        self._progress.setValue(value)
        if message:
            self._label.setText(message)
        self.setVisible(True)

    def reset(self) -> None:
        self._progress.setValue(0)
        self._label.setText("")
        self.setVisible(False)

    def set_progress_color(self, color: str) -> None:
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 6px;
                background-color: {SLATE_200};
                height: 8px;
            }}
            QProgressBar::chunk {{
                border-radius: 6px;
                background-color: {color};
            }}
        """)
