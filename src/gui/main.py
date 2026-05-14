"""Entry point for UMU Advanced PyQt6 GUI."""

from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from .log_config import setup_excepthook, setup_logging
from .main_window import MainWindow
from .styles import get_all_styles

logger = logging.getLogger(__name__)


class App(QApplication):
    """QApplication subclass that logs exceptions in event handlers."""

    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception:
            logger.exception("Exception in Qt event handler (receiver=%s, event=%s)", receiver, event.type().name if hasattr(event.type(), "name") else event.type())
            raise


def main() -> None:
    """Run the PyQt6 GUI application."""
    setup_logging()
    setup_excepthook()
    logger.info("=" * 50)
    logger.info("Application starting")

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = App(sys.argv)
    app.setStyle("Fusion")

    # Global font
    font = QFont("Microsoft YaHei", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Apply global stylesheet
    app.setStyleSheet(get_all_styles())

    window = MainWindow()
    window.showMaximized()

    logger.info("Main window shown (maximized)")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
