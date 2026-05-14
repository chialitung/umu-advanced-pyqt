"""Icon utilities using qtawesome."""

from __future__ import annotations

try:
    import qtawesome as qta
    _QTA_AVAILABLE = True
except ImportError:
    _QTA_AVAILABLE = False

from PyQt6.QtGui import QIcon


def _icon(name: str, color: str = "#64748B") -> QIcon:
    """Create an icon from qtawesome, with fallback."""
    if _QTA_AVAILABLE:
        return qta.icon(name, color=color)
    return QIcon()


class Icon:
    """Semantic icon names for the application."""

    # Navigation
    GOVERNANCE = "fa5s.clipboard-check"
    COURSES = "fa5s.book"
    USERS = "fa5s.users"
    CONFIG = "fa5s.cog"

    # Actions
    LOGIN = "fa5s.sign-in-alt"
    LOGOUT = "fa5s.sign-out-alt"
    SYNC = "fa5s.sync"
    REFRESH = "fa5s.redo"
    EXPORT = "fa5s.file-export"
    SEARCH = "fa5s.search"
    DELETE = "fa5s.trash-alt"
    SAVE = "fa5s.save"

    # Status
    SUCCESS = "fa5s.check-circle"
    ERROR = "fa5s.times-circle"
    WARNING = "fa5s.exclamation-triangle"
    INFO = "fa5s.info-circle"

    # Brand
    LOGO = "fa5s.graduation-cap"

    @classmethod
    def get(cls, name: str, color: str = "#64748B") -> QIcon:
        """Get an icon by semantic name."""
        icon_name = getattr(cls, name.upper(), None)
        if icon_name:
            return _icon(icon_name, color)
        return QIcon()
