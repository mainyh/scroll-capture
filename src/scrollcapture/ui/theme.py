"""Design tokens, Pretendard font and the application style sheet (light / dark)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from . import icons
from .resources import resource_path

log = logging.getLogger(__name__)

FONT_FAMILY = "Pretendard"
FALLBACK_FAMILIES = ["Pretendard", "Malgun Gothic", "Segoe UI"]
BASE_PT = 10


@dataclass(frozen=True)
class Tokens:
    dark: bool
    bg: str
    surface: str
    surface2: str
    border: str
    border_strong: str
    text: str
    muted: str
    accent: str
    accent_hover: str
    accent_press: str
    accent_weak: str
    accent_disabled: str
    on_accent: str
    warn: str
    warn_weak: str
    scroll: str
    scroll_hover: str
    checker_a: str
    checker_b: str


LIGHT = Tokens(
    dark=False, bg="#f6f7f9", surface="#ffffff", surface2="#eef1f5", border="#e3e6eb",
    border_strong="#cfd4dc", text="#1b1f24", muted="#5b6470", accent="#2f6fed",
    accent_hover="#285fd0", accent_press="#2352b4", accent_weak="#e6eefd", accent_disabled="#a9c0f3",
    on_accent="#ffffff", warn="#9a5b00", warn_weak="#fff3df", scroll="#c4cad3", scroll_hover="#a6aeba",
    checker_a="#e9ebee", checker_b="#f7f8fa",
)
DARK = Tokens(
    dark=True, bg="#111418", surface="#1a1e24", surface2="#232931", border="#2b323c",
    border_strong="#3a4250", text="#e6e9ed", muted="#9aa4b1", accent="#4c84f5",
    accent_hover="#5d91f7", accent_press="#3f74de", accent_weak="#1f2b45", accent_disabled="#2f456f",
    on_accent="#ffffff", warn="#e0a040", warn_weak="#3a2c14", scroll="#3a4250", scroll_hover="#4a5363",
    checker_a="#1d2128", checker_b="#262b33",
)


def is_dark() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def tokens() -> Tokens:
    return DARK if is_dark() else LIGHT


# ---------------------------------------------------------------------------- font
def load_fonts() -> str:
    """Register the bundled Pretendard weights; returns the family to use."""
    global FONT_FAMILY
    loaded = None
    for w in ("Regular", "Medium", "SemiBold", "Bold"):
        p = resource_path(f"fonts/Pretendard-{w}.otf")
        if p is None:
            continue
        fid = QFontDatabase.addApplicationFont(str(p))
        fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        if fams:
            loaded = fams[0]
    if loaded:
        FONT_FAMILY = loaded
    else:
        log.warning("Pretendard not found; falling back to system font")
        FONT_FAMILY = "Malgun Gothic"
    return FONT_FAMILY


def font(pt: float = BASE_PT, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont(FONT_FAMILY)
    f.setFamilies(FALLBACK_FAMILIES if FONT_FAMILY == "Pretendard" else [FONT_FAMILY, "Segoe UI"])
    f.setPointSizeF(pt)
    f.setWeight(weight)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


# ---------------------------------------------------------------------------- style
def build_qss(t: Tokens) -> str:
    chev_d = icons.svg_file("chevron_down", t.muted)
    chev_u = icons.svg_file("chevron_up", t.muted)
    check = icons.svg_file("check", t.on_accent, stroke=3)
    return f"""
QWidget {{ color: {t.text}; }}
QMainWindow, QDialog, QWidget#page {{ background: {t.bg}; }}
QLabel {{ background: transparent; }}
QLabel#muted {{ color: {t.muted}; }}
QLabel#section {{ color: {t.muted}; font-size: 8.5pt; font-weight: 600; letter-spacing: .3px; }}
QLabel#title {{ font-size: 11pt; font-weight: 600; }}
QLabel#hero {{ font-size: 17pt; font-weight: 700; }}
QLabel#warn {{ color: {t.warn}; background: {t.warn_weak}; border-radius: 8px; padding: 8px 10px; }}
QLabel a {{ color: {t.accent}; }}

QFrame#card {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 12px; }}
QFrame#sidePanel {{ background: {t.surface}; border: none; border-left: 1px solid {t.border}; }}
QFrame#iconTile {{ background: {t.accent_weak}; border-radius: 10px; }}

QPushButton {{
    background: {t.surface}; border: 1px solid {t.border_strong}; border-radius: 8px;
    padding: 7px 12px; min-height: 20px;
}}
QPushButton:hover {{ background: {t.surface2}; }}
QPushButton:pressed {{ background: {t.border}; }}
QPushButton:disabled {{ color: {t.muted}; background: {t.surface2}; border-color: {t.border}; }}
QPushButton:focus {{ outline: none; }}
QPushButton#primary {{
    background: {t.accent}; border: 1px solid {t.accent}; color: {t.on_accent};
    font-weight: 600; padding: 10px 16px; border-radius: 10px;
}}
QPushButton#primary:hover {{ background: {t.accent_hover}; border-color: {t.accent_hover}; }}
QPushButton#primary:pressed {{ background: {t.accent_press}; border-color: {t.accent_press}; }}
QPushButton#primary:disabled {{ background: {t.accent_disabled}; border-color: {t.accent_disabled}; color: {t.on_accent}; }}
QPushButton#segLeft, QPushButton#segRight {{
    padding: 5px 16px; border-radius: 0; background: {t.surface}; color: {t.muted}; min-height: 18px;
}}
QPushButton#segLeft {{ border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
QPushButton#segRight {{ border-top-right-radius: 8px; border-bottom-right-radius: 8px; border-left: none; }}
QPushButton#segLeft:checked, QPushButton#segRight:checked {{
    background: {t.accent}; border-color: {t.accent}; color: {t.on_accent}; font-weight: 600;
}}

QLineEdit, QComboBox, QSpinBox, QKeySequenceEdit QLineEdit {{
    background: {t.surface}; border: 1px solid {t.border_strong}; border-radius: 8px;
    padding: 6px 10px; min-height: 20px;
    selection-background-color: {t.accent}; selection-color: {t.on_accent};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {t.accent}; }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ color: {t.muted}; background: {t.surface2}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: url("{chev_d}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {t.surface}; border: 1px solid {t.border}; border-radius: 8px; padding: 4px; outline: 0;
    selection-background-color: {t.accent_weak}; selection-color: {t.text};
}}
QSpinBox {{ padding-right: 26px; }}
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: border; width: 24px; border: none; background: transparent;
}}
QSpinBox::up-button {{ subcontrol-position: top right; margin-top: 3px; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; margin-bottom: 3px; }}
QSpinBox::up-arrow {{ image: url("{chev_u}"); width: 10px; height: 10px; }}
QSpinBox::down-arrow {{ image: url("{chev_d}"); width: 10px; height: 10px; }}

QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {t.border_strong}; border-radius: 5px; background: {t.surface};
}}
QCheckBox::indicator:hover {{ border-color: {t.accent}; }}
QCheckBox::indicator:checked {{ background: {t.accent}; border-color: {t.accent}; image: url("{check}"); }}

QTabWidget::pane {{
    background: {t.surface}; border: 1px solid {t.border}; border-radius: 12px; top: -1px; padding: 10px;
}}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent; color: {t.muted}; padding: 8px 14px; margin-right: 2px;
    border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: {t.text}; }}
QTabBar::tab:selected {{ color: {t.text}; border-bottom-color: {t.accent}; font-weight: 600; }}

QToolBar {{ background: {t.surface}; border: none; border-bottom: 1px solid {t.border}; padding: 6px 8px; spacing: 2px; }}
QToolBar::separator {{ background: {t.border}; width: 1px; margin: 6px 6px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 5px 10px; }}
QToolButton:hover {{ background: {t.surface2}; }}
QToolButton:pressed {{ background: {t.border}; }}
QToolButton:checked {{ background: {t.accent_weak}; color: {t.accent}; font-weight: 600; }}
QToolButton:disabled {{ color: {t.muted}; }}

QStatusBar {{ background: {t.surface}; border-top: 1px solid {t.border}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {t.muted}; padding: 2px 6px; }}

QMenu {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 16px 7px 8px; border-radius: 6px; }}
QMenu::item:selected {{ background: {t.accent_weak}; }}
QMenu::item:disabled {{ color: {t.muted}; }}
QMenu::icon {{ padding-left: 8px; }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle {{ background: {t.scroll}; border-radius: 4px; }}
QScrollBar::handle:hover {{ background: {t.scroll_hover}; }}
QScrollBar::handle:vertical {{ min-height: 32px; }}
QScrollBar::handle:horizontal {{ min-width: 32px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QToolTip {{ background: {t.text}; color: {t.bg}; border: none; padding: 5px 8px; border-radius: 6px; }}
QDialogButtonBox QPushButton {{ min-width: 84px; }}
"""


def palette(t: Tokens) -> QPalette:
    p = QPalette()
    c = QColor
    p.setColor(QPalette.ColorRole.Window, c(t.bg))
    p.setColor(QPalette.ColorRole.WindowText, c(t.text))
    p.setColor(QPalette.ColorRole.Base, c(t.surface))
    p.setColor(QPalette.ColorRole.AlternateBase, c(t.surface2))
    p.setColor(QPalette.ColorRole.Text, c(t.text))
    p.setColor(QPalette.ColorRole.Button, c(t.surface))
    p.setColor(QPalette.ColorRole.ButtonText, c(t.text))
    p.setColor(QPalette.ColorRole.Highlight, c(t.accent))
    p.setColor(QPalette.ColorRole.HighlightedText, c(t.on_accent))
    p.setColor(QPalette.ColorRole.PlaceholderText, c(t.muted))
    p.setColor(QPalette.ColorRole.ToolTipBase, c(t.text))
    p.setColor(QPalette.ColorRole.ToolTipText, c(t.bg))
    p.setColor(QPalette.ColorRole.Link, c(t.accent))
    p.setColor(QPalette.ColorRole.Mid, c(t.border_strong))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, c(t.muted))
    return p


class Theme(QObject):
    """Applies the style and re-applies it when Windows switches light/dark."""
    changed = Signal()

    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app = app
        self.t = tokens()
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(lambda *_: self.apply())
        except Exception:
            pass

    def apply(self) -> None:
        self.t = tokens()
        self.app.setStyle("Fusion")
        self.app.setPalette(palette(self.t))
        self.app.setStyleSheet(build_qss(self.t))
        self.changed.emit()

    def icon(self, name: str, color: str | None = None):
        return icons.icon(name, color or self.t.text, disabled=self.t.muted)


_theme: Theme | None = None


def install(app: QApplication) -> Theme:
    global _theme
    family = load_fonts()
    app.setFont(font())
    log.info("UI font: %s", family)
    _theme = Theme(app)
    _theme.apply()
    return _theme


def current() -> Theme:
    assert _theme is not None, "theme.install() not called"
    return _theme
