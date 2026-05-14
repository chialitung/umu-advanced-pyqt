"""Step indicator component."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QLabel

from ..styles import BRAND_500, SLATE_200, SLATE_500, SUCCESS_500


class StepIndicator(QWidget):
    """Horizontal step indicator with numbered circles and labels."""

    def __init__(self, steps: list[str], parent=None) -> None:
        super().__init__(parent)
        self._steps = steps
        self._current = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._circles: list[QLabel] = []
        self._labels: list[QLabel] = []
        self._lines: list[QWidget] = []

        for i, step in enumerate(self._steps):
            # Circle
            circle = QLabel(str(i + 1))
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setFixedSize(28, 28)
            circle.setStyleSheet(f"""
                background-color: {SLATE_200};
                color: {SLATE_500};
                border-radius: 14px;
                font-size: 12px;
                font-weight: 700;
            """)
            self._circles.append(circle)

            # Label
            label = QLabel(step)
            label.setStyleSheet(f"color: {SLATE_500}; font-size: 12px; font-weight: 500;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._labels.append(label)

            # Step container (circle + label)
            step_widget = QWidget()
            step_layout = QVBoxLayout(step_widget)
            step_layout.setContentsMargins(0, 0, 0, 0)
            step_layout.setSpacing(4)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

            layout.addWidget(step_widget)

            # Connector line
            if i < len(self._steps) - 1:
                line = QWidget()
                line.setFixedHeight(2)
                line.setMinimumWidth(40)
                line.setStyleSheet(f"background-color: {SLATE_200};")
                line.setSizePolicy(
                    line.sizePolicy().Policy.Expanding,
                    line.sizePolicy().Policy.Fixed
                )
                self._lines.append(line)
                layout.addWidget(line, stretch=1)

        self.set_current(0)

    def set_current(self, index: int) -> None:
        self._current = index
        for i, circle in enumerate(self._circles):
            if i < index:
                circle.setText("✓")
                circle.setStyleSheet(f"""
                    background-color: {SUCCESS_500};
                    color: white;
                    border-radius: 14px;
                    font-size: 12px;
                    font-weight: 700;
                """)
                self._labels[i].setStyleSheet(f"color: {SUCCESS_500}; font-size: 12px; font-weight: 600;")
            elif i == index:
                circle.setText(str(i + 1))
                circle.setStyleSheet(f"""
                    background-color: {BRAND_500};
                    color: white;
                    border-radius: 14px;
                    font-size: 12px;
                    font-weight: 700;
                """)
                self._labels[i].setStyleSheet(f"color: {BRAND_500}; font-size: 12px; font-weight: 600;")
            else:
                circle.setText(str(i + 1))
                circle.setStyleSheet(f"""
                    background-color: {SLATE_200};
                    color: {SLATE_500};
                    border-radius: 14px;
                    font-size: 12px;
                    font-weight: 700;
                """)
                self._labels[i].setStyleSheet(f"color: {SLATE_500}; font-size: 12px; font-weight: 500;")

        for i, line in enumerate(self._lines):
            if i < index:
                line.setStyleSheet(f"background-color: {SUCCESS_500};")
            else:
                line.setStyleSheet(f"background-color: {SLATE_200};")
