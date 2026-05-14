"""Config service for PyQt6 GUI."""

from __future__ import annotations

import json
import logging

from PyQt6.QtCore import QObject, pyqtSignal

from .governance_service import GovernanceConfigService

logger = logging.getLogger(__name__)


class ConfigService(QObject):
    """Manages governance configuration for the GUI."""

    config_changed = pyqtSignal()

    def __init__(self, database_url: str | None = None) -> None:
        super().__init__()
        if database_url is not None:
            self._service = GovernanceConfigService(database_url)
        else:
            self._service = GovernanceConfigService()

    def load_config(self) -> dict:
        return self._service.get_all_configs()

    def save_config(self, configs: dict) -> None:
        for key, value in configs.items():
            self._service.set_config(key, value)
        self.config_changed.emit()

    def reset_config(self) -> None:
        self._service.reset_to_defaults()
        self.config_changed.emit()

    def backup_config(self) -> str:
        return json.dumps(self._service.get_all_configs(), ensure_ascii=False, indent=2)

    def restore_config(self, json_str: str) -> None:
        data = json.loads(json_str)
        for key, value in data.items():
            self._service.set_config(key, value)
        self.config_changed.emit()
