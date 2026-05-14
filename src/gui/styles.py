"""Global stylesheet definitions for UMU Advanced PyQt6 GUI.

Maps the web CSS design system to Qt stylesheets.
"""

# =============================================================================
# Color Palette
# =============================================================================

# Brand colors (UMU Red)
BRAND_50 = "#FDE8EF"
BRAND_100 = "#F9B9CD"
BRAND_200 = "#F58AAB"
BRAND_300 = "#F15B89"
BRAND_400 = "#ED2C67"
BRAND_500 = "#D31145"  # Primary brand color
BRAND_600 = "#A90D37"
BRAND_700 = "#7F0A29"
BRAND_800 = "#55061C"
BRAND_900 = "#2B030E"

# Slate neutrals
SLATE_50 = "#F8FAFC"
SLATE_100 = "#F1F5F9"
SLATE_200 = "#E2E8F0"
SLATE_300 = "#CBD5E1"
SLATE_400 = "#94A3B8"
SLATE_500 = "#64748B"
SLATE_600 = "#475569"
SLATE_700 = "#334155"
SLATE_800 = "#1E293B"
SLATE_900 = "#0F172A"

# Semantic colors
SUCCESS_50 = "#F0FDF4"
SUCCESS_500 = "#22C55E"
SUCCESS_600 = "#16A34A"
WARNING_50 = "#FFFBEB"
WARNING_500 = "#F59E0B"
WARNING_600 = "#D97706"
INFO_50 = "#EFF6FF"
INFO_500 = "#3B82F6"
INFO_600 = "#2563EB"
DANGER_50 = "#FEF2F2"
DANGER_500 = "#EF4444"
DANGER_600 = "#DC2626"
DANGER_700 = "#B91C1C"

# Backgrounds
BG_PAGE = SLATE_50
BG_SURFACE = "#FFFFFF"

# =============================================================================
# Spacing Scale
# =============================================================================

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 20
SPACING_2XL = 24
SPACING_3XL = 32
SPACING_4XL = 40
MARGIN_PAGE = (40, 32, 40, 32)

# =============================================================================
# Base Application Stylesheet
# =============================================================================

APP_STYLE = f"""
QMainWindow {{
    background-color: {BG_PAGE};
}}

QWidget {{
    font-family: "Microsoft YaHei", "PingFang SC", "Inter", sans-serif;
    font-size: 14px;
    color: {SLATE_800};
}}

QLabel {{
    color: {SLATE_700};
}}

QLineEdit {{
    background-color: {BG_SURFACE};
    border: 1.5px solid {SLATE_200};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    color: {SLATE_800};
    selection-background-color: {BRAND_500};
}}

QLineEdit:focus {{
    border: 2px solid {BRAND_500};
}}

QLineEdit::placeholder {{
    color: {SLATE_400};
}}

QTextEdit {{
    background-color: {BG_SURFACE};
    border: 1.5px solid {SLATE_200};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    color: {SLATE_800};
    selection-background-color: {BRAND_500};
}}

QTextEdit:focus {{
    border: 2px solid {BRAND_500};
}}

QComboBox {{
    background-color: {BG_SURFACE};
    border: 1.5px solid {SLATE_200};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    color: {SLATE_800};
    min-width: 120px;
}}

QComboBox:focus {{
    border: 2px solid {BRAND_500};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_SURFACE};
    border: 1px solid {SLATE_200};
    border-radius: 8px;
    selection-background-color: {BRAND_50};
    selection-color: {BRAND_700};
    padding: 4px;
}}

QDateEdit {{
    background-color: {BG_SURFACE};
    border: 1.5px solid {SLATE_200};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    color: {SLATE_800};
}}

QDateEdit:focus {{
    border: 2px solid {BRAND_500};
}}

QGroupBox {{
    background-color: {BG_SURFACE};
    border: 1px solid {SLATE_200};
    border-radius: 12px;
    margin-top: 16px;
    padding-top: 16px;
    padding: 16px;
    font-weight: 600;
    color: {SLATE_800};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 8px;
    color: {SLATE_700};
    font-weight: 600;
    font-size: 15px;
}}

QScrollBar:vertical {{
    background: {SLATE_100};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {SLATE_300};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {SLATE_400};
}}

QScrollBar:horizontal {{
    background: {SLATE_100};
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {SLATE_300};
    border-radius: 4px;
    min-width: 30px;
}}

QTabWidget::pane {{
    border: none;
    background: transparent;
}}

QTabBar::tab {{
    background: transparent;
    border: none;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
    color: {SLATE_500};
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {BRAND_500};
    border-bottom: 2px solid {BRAND_500};
}}

QTabBar::tab:hover:!selected {{
    color: {SLATE_700};
}}

QTableView {{
    background-color: {BG_SURFACE};
    border: 1px solid {SLATE_200};
    border-radius: 8px;
    gridline-color: {SLATE_100};
    selection-background-color: {BRAND_50};
    selection-color: {SLATE_800};
}}

QTableView::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {SLATE_100};
}}

QTableView::item:selected {{
    background-color: {BRAND_50};
    color: {SLATE_800};
}}

QHeaderView::section {{
    background-color: {SLATE_50};
    color: {SLATE_500};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid {SLATE_200};
}}

QProgressBar {{
    border: none;
    border-radius: 6px;
    background-color: {SLATE_200};
    height: 8px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {BRAND_400}, stop:1 {BRAND_600});
}}

QDockWidget {{
    border: none;
    titlebar-close-icon: url(none);
}}

QDockWidget::title {{
    background: transparent;
    padding: 0px;
}}
"""

# =============================================================================
# Component Styles
# =============================================================================

SIDEBAR_STYLE = f"""
QWidget#sidebar {{
    background-color: {BG_SURFACE};
    border-right: 1px solid {SLATE_200};
}}

QWidget#sidebar QLabel#brand-title {{
    color: {SLATE_800};
    font-size: 20px;
    font-weight: 700;
}}

QWidget#sidebar QLabel#brand-subtitle {{
    color: {SLATE_500};
    font-size: 12px;
}}

QWidget#sidebar QPushButton#nav-btn {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    color: {SLATE_600};
}}

QWidget#sidebar QPushButton#nav-btn:hover {{
    background-color: {SLATE_100};
    color: {SLATE_800};
}}

QWidget#sidebar QPushButton#nav-btn:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {BRAND_50}, stop:1 {BRAND_100});
    color: {BRAND_600};
    font-weight: 600;
}}

QWidget#sidebar QLabel#user-name {{
    color: {SLATE_700};
    font-size: 13px;
    font-weight: 600;
}}

QWidget#sidebar QLabel#admin-badge {{
    background-color: {BRAND_50};
    color: {BRAND_600};
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}}
"""

BUTTON_PRIMARY_STYLE = f"""
QPushButton#btn-primary {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BRAND_400}, stop:1 {BRAND_500});
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    color: white;
}}

QPushButton#btn-primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BRAND_500}, stop:1 {BRAND_600});
}}

QPushButton#btn-primary:pressed {{
    background: {BRAND_700};
}}

QPushButton#btn-primary:disabled {{
    background: {SLATE_300};
    color: {SLATE_500};
}}
"""

BUTTON_SECONDARY_STYLE = f"""
QPushButton#btn-secondary {{
    background-color: {BG_SURFACE};
    border: 1.5px solid {SLATE_200};
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    color: {SLATE_700};
}}

QPushButton#btn-secondary:hover {{
    border-color: {SLATE_300};
    background-color: {SLATE_50};
}}

QPushButton#btn-secondary:pressed {{
    background-color: {SLATE_100};
}}
"""

BUTTON_GHOST_STYLE = f"""
QPushButton#btn-ghost {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    color: {SLATE_500};
}}

QPushButton#btn-ghost:hover {{
    background-color: {SLATE_100};
    color: {SLATE_700};
}}
"""

CARD_STYLE = f"""
QWidget#card {{
    background-color: {BG_SURFACE};
    border: 1px solid {SLATE_200};
    border-radius: 12px;
}}
"""

LOGIN_CARD_STYLE = f"""
QWidget#login-card {{
    background-color: {BG_SURFACE};
    border: 1px solid {SLATE_200};
    border-radius: 16px;
}}

QWidget#login-card QLabel#login-title {{
    color: {SLATE_800};
    font-size: 24px;
    font-weight: 700;
}}

QWidget#login-card QLabel#login-subtitle {{
    color: {SLATE_500};
    font-size: 14px;
}}

QWidget#login-card QLabel#login-error {{
    color: {DANGER_500};
    font-size: 13px;
    padding: 8px;
    background-color: {DANGER_50};
    border-radius: 6px;
}}
"""

STAT_CARD_STYLE = f"""
QWidget#stat-card {{
    background-color: {BG_SURFACE};
    border: 1px solid {SLATE_200};
    border-radius: 12px;
    padding: 16px;
}}

QWidget#stat-card QLabel#stat-value {{
    color: {SLATE_800};
    font-size: 24px;
    font-weight: 700;
}}

QWidget#stat-card QLabel#stat-label {{
    color: {SLATE_500};
    font-size: 12px;
    font-weight: 500;
}}
"""

STEP_INDICATOR_STYLE = f"""
QLabel#step-circle {{
    background-color: {SLATE_200};
    color: {SLATE_500};
    border-radius: 14px;
    font-size: 12px;
    font-weight: 700;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    qproperty-alignment: AlignCenter;
}}

QLabel#step-circle-active {{
    background-color: {BRAND_500};
    color: white;
    border-radius: 14px;
    font-size: 12px;
    font-weight: 700;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    qproperty-alignment: AlignCenter;
}}

QLabel#step-circle-done {{
    background-color: {SUCCESS_500};
    color: white;
    border-radius: 14px;
    font-size: 12px;
    font-weight: 700;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    qproperty-alignment: AlignCenter;
}}

QLabel#step-label {{
    color: {SLATE_500};
    font-size: 12px;
    font-weight: 500;
}}

QLabel#step-label-active {{
    color: {BRAND_600};
    font-size: 12px;
    font-weight: 600;
}}
"""

BADGE_OK_STYLE = f"""
QLabel#badge-ok {{
    background-color: {SUCCESS_50};
    color: {SUCCESS_600};
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 12px;
}}
"""

BADGE_MAJOR_STYLE = f"""
QLabel#badge-major {{
    background-color: {DANGER_50};
    color: {DANGER_600};
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 12px;
}}
"""

BADGE_MINOR_STYLE = f"""
QLabel#badge-minor {{
    background-color: {WARNING_50};
    color: {WARNING_600};
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 12px;
}}
"""

BADGE_UNKNOWN_STYLE = f"""
QLabel#badge-unknown {{
    background-color: {SLATE_100};
    color: {SLATE_600};
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 12px;
}}
"""

PAGE_TITLE_STYLE = f"""
QLabel#page-title {{
    color: {SLATE_800};
    font-size: 22px;
    font-weight: 700;
}}
"""

PAGE_DESC_STYLE = f"""
QLabel#page-desc {{
    color: {SLATE_500};
    font-size: 14px;
    line-height: 22px;
}}
"""

CHIP_STYLE = f"""
QPushButton#chip {{
    background-color: {SLATE_100};
    border: none;
    border-radius: 16px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 500;
    color: {SLATE_600};
}}

QPushButton#chip:hover {{
    background-color: {SLATE_200};
}}

QPushButton#chip:checked {{
    background-color: {BRAND_50};
    color: {BRAND_600};
    font-weight: 600;
}}
"""

DRAWER_STYLE = f"""
QWidget#drawer {{
    background-color: {BG_SURFACE};
    border-left: 1px solid {SLATE_200};
}}
"""

TOAST_SUCCESS_STYLE = f"""
QWidget#toast-success {{
    background-color: {SUCCESS_50};
    border: 1px solid {SUCCESS_500};
    border-radius: 8px;
    padding: 12px 20px;
}}

QWidget#toast-success QLabel {{
    color: {SUCCESS_600};
    font-size: 14px;
    font-weight: 500;
}}
"""

TOAST_ERROR_STYLE = f"""
QWidget#toast-error {{
    background-color: {DANGER_50};
    border: 1px solid {DANGER_500};
    border-radius: 8px;
    padding: 12px 20px;
}}

QWidget#toast-error QLabel {{
    color: {DANGER_600};
    font-size: 14px;
    font-weight: 500;
}}
"""

TOAST_WARNING_STYLE = f"""
QWidget#toast-warning {{
    background-color: {WARNING_50};
    border: 1px solid {WARNING_500};
    border-radius: 8px;
    padding: 12px 20px;
}}

QWidget#toast-warning QLabel {{
    color: {WARNING_600};
    font-size: 14px;
    font-weight: 500;
}}
"""

TOAST_INFO_STYLE = f"""
QWidget#toast-info {{
    background-color: {INFO_50};
    border: 1px solid {INFO_500};
    border-radius: 8px;
    padding: 12px 20px;
}}

QWidget#toast-info QLabel {{
    color: {INFO_600};
    font-size: 14px;
    font-weight: 500;
}}
"""

NON_ADMIN_WARNING_STYLE = f"""
QWidget#non-admin-warning {{
    background-color: {WARNING_50};
    border: 1px solid {WARNING_500};
    border-radius: 8px;
    padding: 12px 16px;
}}

QWidget#non-admin-warning QLabel {{
    color: {WARNING_600};
    font-size: 13px;
}}
"""

MODAL_OVERLAY_STYLE = f"""
QWidget#modal-overlay {{
    background-color: rgba(15, 23, 42, 180);
}}
"""

MODAL_CONTENT_STYLE = f"""
QWidget#modal-content {{
    background-color: {BG_SURFACE};
    border-radius: 16px;
}}
"""

DIALOG_STYLE = f"""
QMessageBox {{
    background-color: {BG_SURFACE};
    font-family: "Microsoft YaHei", "PingFang SC", "Inter", sans-serif;
}}

QMessageBox QLabel {{
    color: {SLATE_800};
    font-size: 14px;
    padding: 8px;
}}

QMessageBox QPushButton,
QDialogButtonBox QPushButton {{
    background-color: {BG_SURFACE};
    border: 1.5px solid {SLATE_200};
    border-radius: 6px;
    padding: 8px 24px;
    font-size: 13px;
    font-weight: 500;
    color: {SLATE_700};
    min-width: 80px;
    min-height: 32px;
}}

QMessageBox QPushButton:hover,
QDialogButtonBox QPushButton:hover {{
    background-color: {SLATE_50};
    border-color: {SLATE_300};
}}

QMessageBox QPushButton:default,
QDialogButtonBox QPushButton:default {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BRAND_400}, stop:1 {BRAND_500});
    border: none;
    color: white;
}}

QMessageBox QPushButton:default:hover,
QDialogButtonBox QPushButton:default:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BRAND_500}, stop:1 {BRAND_600});
}}

QFileDialog {{
    background-color: {BG_SURFACE};
}}

QCalendarWidget QWidget {{
    background-color: {BG_SURFACE};
    color: {SLATE_800};
}}

QCalendarWidget QToolButton {{
    background-color: transparent;
    color: {SLATE_700};
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
}}

QCalendarWidget QToolButton:hover {{
    background-color: {SLATE_100};
}}

QCalendarWidget QMenu {{
    background-color: {BG_SURFACE};
}}

QCalendarWidget QSpinBox {{
    background-color: {BG_SURFACE};
    border: 1px solid {SLATE_200};
    border-radius: 4px;
    padding: 2px;
}}

QCalendarWidget QAbstractItemView:enabled {{
    background-color: {BG_SURFACE};
    color: {SLATE_800};
    selection-background-color: {BRAND_500};
    selection-color: white;
}}

QCalendarWidget QAbstractItemView:disabled {{
    color: {SLATE_300};
}}

QCalendarWidget QAbstractItemView::item {{
    padding: 2px 4px;
    border-bottom: none;
}}

QSpinBox {{
    background-color: {BG_SURFACE};
    border: 1.5px solid {SLATE_200};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    color: {SLATE_800};
}}

QSpinBox:focus {{
    border: 2px solid {BRAND_500};
}}
"""


def get_all_styles() -> str:
    """Return the complete application stylesheet."""
    return (
        APP_STYLE
        + SIDEBAR_STYLE
        + BUTTON_PRIMARY_STYLE
        + BUTTON_SECONDARY_STYLE
        + BUTTON_GHOST_STYLE
        + CARD_STYLE
        + LOGIN_CARD_STYLE
        + STAT_CARD_STYLE
        + STEP_INDICATOR_STYLE
        + BADGE_OK_STYLE
        + BADGE_MAJOR_STYLE
        + BADGE_MINOR_STYLE
        + BADGE_UNKNOWN_STYLE
        + PAGE_TITLE_STYLE
        + PAGE_DESC_STYLE
        + CHIP_STYLE
        + DRAWER_STYLE
        + TOAST_SUCCESS_STYLE
        + TOAST_ERROR_STYLE
        + TOAST_WARNING_STYLE
        + TOAST_INFO_STYLE
        + NON_ADMIN_WARNING_STYLE
        + MODAL_OVERLAY_STYLE
        + MODAL_CONTENT_STYLE
        + DIALOG_STYLE
    )
