"""
Theme - Uniform Forest Dark Green & Brass Palette for SpatialSight.

Exact design specifications:
- Backgrounds & Primary Surfaces: #15370D (Deep forest dark green)
- Secondary Panels & Cards: #1E4714 / #2D5E1E
- Borders, Accents & Highlights: #E5CD82 (Warm sand / brass gold)
- Headers, Titles & Primary Text: #FFF2B4 (Soft cream / butter yellow)
- Secondary / Value Text: #E5CD82
- Dynamic Alerts: Green (#30D158), Yellow (#FFD60A), Red (#FF453A)
- Zero emojis anywhere in the UI.
"""

# Color Palette Constants
BG            = "#15370D"   # Main background
SURFACE       = "#1E4714"   # Secondary panels, cards, containers
SURFACE_HOVER = "#2D5E1E"   # Hover fills, active buttons
SURFACE_DARK  = "#0E2409"   # Inset deep dark containers / video background
BORDER        = "#E5CD82"   # Brass gold borders and active outlines
BORDER_MUTED  = "#E5CD8255" # Subtle border / divider
BORDER_FAINT  = "#E5CD8222" # Hairline divider

TEXT          = "#FFF2B4"   # Primary text, titles, headers
TEXT_MUTED    = "#E5CD82"   # Secondary text, values, subtitles
TEXT_DIM      = "#99A87B"   # Tertiary / disabled text

ACCENT        = "#E5CD82"   # Primary accent
ACCENT_BRIGHT = "#FFF2B4"

# Alert and indicator status colors
GREEN         = "#30D158"   # Safe / Connected indicator
YELLOW        = "#FFD60A"   # Caution hazard
RED           = "#FF453A"   # Imminent hazard

# Clean vector font stack
FONT_STACK = "'SF Pro Display', 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Inter, sans-serif"
MONO_STACK = "'SF Mono', 'Menlo', 'Consolas', 'Courier New', monospace"


def pill(bg_color: str, fg_color: str, bold: bool = True) -> str:
    """Rounded status-pill style for HUD tags and status indicators."""
    weight = "700" if bold else "500"
    return (
        f"background-color: {bg_color}; color: {fg_color}; border-radius: 6px; "
        f"padding: 4px 10px; font-size: 11px; font-weight: {weight}; border: 1px solid {BORDER_MUTED};"
    )


GLOBAL_STYLESHEET = f"""
* {{
    font-family: {FONT_STACK};
    outline: none;
}}

QMainWindow, QDialog, QWidget#RootBackground {{
    background-color: {BG};
    color: {TEXT};
}}

QWidget {{
    background-color: transparent;
    color: {TEXT};
    font-size: 13px;
}}

QWidget:disabled {{
    color: {TEXT_DIM};
}}

/* Top Bar and Navigation */
QToolBar {{
    background-color: {BG};
    border: none;
    border-bottom: 1px solid {BORDER_MUTED};
    spacing: 12px;
    padding: 10px 16px;
}}

/* Styled Panels and Cards */
QFrame#SidebarCard, QFrame#CardPanel {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QFrame#InnerPanel {{
    background-color: {SURFACE_DARK};
    border: 1px solid {BORDER_MUTED};
    border-radius: 8px;
}}

/* Labels */
QLabel {{
    background-color: transparent;
    color: {TEXT};
}}

QLabel#HeaderTitle {{
    color: {TEXT};
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
}}

QLabel#SubTitle {{
    color: {TEXT_MUTED};
    font-size: 12px;
    font-weight: 500;
}}

QLabel#CategoryName {{
    color: {TEXT};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#CategoryCount {{
    color: {TEXT_MUTED};
    font-size: 13px;
    font-weight: 700;
}}

QLabel#CategoryDist {{
    color: {TEXT};
    font-size: 12px;
    font-family: {MONO_STACK};
}}

/* Checkboxes */
QCheckBox {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 600;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid {BORDER};
    background-color: {SURFACE};
}}

QCheckBox::indicator:hover {{
    border-color: {TEXT};
    background-color: {SURFACE_HOVER};
}}

QCheckBox::indicator:checked {{
    background-color: {BORDER};
    image: none;
}}

/* Buttons */
QPushButton {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {SURFACE_HOVER};
    border-color: {TEXT};
    color: {TEXT};
}}

QPushButton:pressed {{
    background-color: {SURFACE_DARK};
    border-color: {BORDER};
}}

QPushButton:disabled {{
    background-color: {SURFACE_DARK};
    border-color: {BORDER_FAINT};
    color: {TEXT_DIM};
}}

/* Start / Stop Hero Buttons */
QPushButton#StartHeroButton {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 2px solid {BORDER};
    border-radius: 12px;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 16px 48px;
}}

QPushButton#StartHeroButton:hover {{
    background-color: {SURFACE_HOVER};
    border-color: {TEXT};
    color: {TEXT};
}}

QPushButton#StartHeroButton:pressed {{
    background-color: {SURFACE_DARK};
}}

QPushButton#StopButton {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 2px solid {BORDER};
    border-radius: 10px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 12px 24px;
}}

QPushButton#StopButton:hover {{
    background-color: #3D1A1A;
    border-color: {RED};
    color: #FFAAAA;
}}

QPushButton#StopButton:pressed {{
    background-color: #240E0E;
}}

/* Scrollbar */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    border: none;
    background: {SURFACE_DARK};
    width: 8px;
    border-radius: 4px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_MUTED};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {BORDER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
