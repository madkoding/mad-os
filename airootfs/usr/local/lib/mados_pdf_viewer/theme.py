"""
madOS PDF Viewer - Nord Theme

Applies the Nord color palette to the GTK3 application via CSS.

Nord Palette:
  Polar Night: #2E3440, #3B4252, #434C5E, #4C566A
  Snow Storm:  #D8DEE9, #E5E9F0, #ECEFF4
  Frost:       #8FBCBB, #88C0D0, #81A1C1, #5E81AC
  Aurora:      #BF616A, #D08770, #EBCB8B, #A3BE8C, #B48EAD
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

# ── Nord Color Constants ──────────────────────────────────────────────────────

NORD_POLAR_NIGHT = {
    'nord0': '#2E3440',
    'nord1': '#3B4252',
    'nord2': '#434C5E',
    'nord3': '#4C566A',
}

NORD_SNOW_STORM = {
    'nord4': '#D8DEE9',
    'nord5': '#E5E9F0',
    'nord6': '#ECEFF4',
}

NORD_FROST = {
    'nord7': '#8FBCBB',
    'nord8': '#88C0D0',
    'nord9': '#81A1C1',
    'nord10': '#5E81AC',
}

NORD_AURORA = {
    'nord11': '#BF616A',
    'nord12': '#D08770',
    'nord13': '#EBCB8B',
    'nord14': '#A3BE8C',
    'nord15': '#B48EAD',
}

# ── CSS Stylesheet ────────────────────────────────────────────────────────────

NORD_CSS = """
/* ─── Global ──────────────────────────────────────────────────────────────── */
* {
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
}

/* ─── Window ──────────────────────────────────────────────────────────────── */
window {
    background-color: #2E3440;
    color: #D8DEE9;
}

/* ─── Header Bar ──────────────────────────────────────────────────────────── */
headerbar {
    background-color: #3B4252;
    border-bottom: 1px solid #434C5E;
    color: #ECEFF4;
    min-height: 38px;
    padding: 0 6px;
}

headerbar .title {
    color: #ECEFF4;
    font-weight: bold;
}

headerbar .subtitle {
    color: #D8DEE9;
    font-size: 0.85em;
}

/* ─── Toolbar / Action Bar ────────────────────────────────────────────────── */
toolbar, .toolbar, actionbar {
    background-color: #3B4252;
    border-bottom: 1px solid #434C5E;
    padding: 2px 4px;
}

/* ─── Buttons ─────────────────────────────────────────────────────────────── */
button {
    background-image: linear-gradient(to bottom, #5E81AC, #81A1C1);
    color: #ECEFF4;
    border: 1px solid #4C566A;
    border-radius: 4px;
    padding: 4px 10px;
    min-height: 24px;
    transition: all 150ms ease;
}

button:hover {
    background-image: linear-gradient(to bottom, #81A1C1, #88C0D0);
    border-color: #88C0D0;
}

button:active, button:checked {
    background-image: linear-gradient(to bottom, #4C566A, #5E81AC);
    border-color: #81A1C1;
}

button:disabled {
    background-image: none;
    background-color: #434C5E;
    color: #4C566A;
    border-color: #3B4252;
}

button.flat {
    background-image: none;
    background-color: transparent;
    border: 1px solid transparent;
    color: #D8DEE9;
}

button.flat:hover {
    background-color: #434C5E;
    border-color: #4C566A;
}

button.destructive-action {
    background-image: linear-gradient(to bottom, #BF616A, #D08770);
    border-color: #BF616A;
}

button.destructive-action:hover {
    background-image: linear-gradient(to bottom, #D08770, #EBCB8B);
}

button.suggested-action {
    background-image: linear-gradient(to bottom, #5E81AC, #88C0D0);
    border-color: #5E81AC;
}

/* ─── Toggle / Check / Radio Buttons ──────────────────────────────────────── */
checkbutton, radiobutton {
    color: #D8DEE9;
}

check, radio {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 3px;
    color: #88C0D0;
    min-width: 16px;
    min-height: 16px;
}

check:checked, radio:checked {
    background-color: #5E81AC;
    border-color: #81A1C1;
    color: #ECEFF4;
}

/* ─── Entries / Text Input ────────────────────────────────────────────────── */
entry {
    background-color: #3B4252;
    color: #ECEFF4;
    border: 1px solid #4C566A;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 26px;
    caret-color: #88C0D0;
}

entry:focus {
    border-color: #88C0D0;
    box-shadow: 0 0 0 1px rgba(136, 192, 208, 0.3);
}

entry:disabled {
    background-color: #2E3440;
    color: #4C566A;
}

/* ─── Spin Button ─────────────────────────────────────────────────────────── */
spinbutton {
    background-color: #3B4252;
    color: #ECEFF4;
    border: 1px solid #4C566A;
    border-radius: 4px;
}

spinbutton button {
    background-image: none;
    background-color: #434C5E;
    border: none;
    border-radius: 0;
    min-width: 24px;
    padding: 2px;
}

spinbutton button:hover {
    background-color: #5E81AC;
}

/* ─── Labels ──────────────────────────────────────────────────────────────── */
label {
    color: #D8DEE9;
}

label.title {
    color: #ECEFF4;
    font-weight: bold;
}

label.dim-label {
    color: #4C566A;
}

/* ─── Scrolled Window / Viewport ──────────────────────────────────────────── */
scrolledwindow {
    background-color: #2E3440;
    border: none;
}

scrolledwindow viewport {
    background-color: #2E3440;
}

/* ─── Scrollbar ───────────────────────────────────────────────────────────── */
scrollbar {
    background-color: #2E3440;
}

scrollbar slider {
    background-color: #4C566A;
    border-radius: 8px;
    min-width: 8px;
    min-height: 8px;
}

scrollbar slider:hover {
    background-color: #5E81AC;
}

scrollbar slider:active {
    background-color: #81A1C1;
}

/* ─── Scales / Sliders ────────────────────────────────────────────────────── */
scale {
    color: #D8DEE9;
}

scale trough {
    background-color: #3B4252;
    border-radius: 4px;
    min-height: 6px;
}

scale trough highlight {
    background-color: #5E81AC;
    border-radius: 4px;
}

scale slider {
    background-color: #88C0D0;
    border: 1px solid #5E81AC;
    border-radius: 50%;
    min-width: 16px;
    min-height: 16px;
}

scale slider:hover {
    background-color: #8FBCBB;
}

/* ─── Separators ──────────────────────────────────────────────────────────── */
separator {
    background-color: #434C5E;
    min-width: 1px;
    min-height: 1px;
}

/* ─── Drawing Area ────────────────────────────────────────────────────────── */
drawingarea {
    background-color: #2E3440;
}

/* ─── Combo Box ───────────────────────────────────────────────────────────── */
combobox button {
    background-image: none;
    background-color: #3B4252;
    border: 1px solid #4C566A;
    color: #D8DEE9;
    padding: 4px 8px;
}

combobox button:hover {
    background-color: #434C5E;
    border-color: #88C0D0;
}

combobox window menu {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 4px;
}

/* ─── Menus / Popovers ────────────────────────────────────────────────────── */
menu, .menu, popover, .popover {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 6px;
    padding: 4px 0;
    color: #D8DEE9;
}

menuitem, .menuitem {
    padding: 6px 12px;
    color: #D8DEE9;
}

menuitem:hover, .menuitem:hover {
    background-color: #5E81AC;
    color: #ECEFF4;
}

popover button {
    background-image: none;
    background-color: transparent;
    border: none;
    color: #D8DEE9;
    border-radius: 4px;
    padding: 6px 12px;
}

popover button:hover {
    background-color: #434C5E;
}

/* ─── Notebook (Tabs) ─────────────────────────────────────────────────────── */
notebook {
    background-color: #2E3440;
}

notebook header {
    background-color: #3B4252;
    border-bottom: 1px solid #434C5E;
}

notebook tab {
    background-color: #3B4252;
    color: #D8DEE9;
    padding: 6px 14px;
    border: 1px solid transparent;
}

notebook tab:checked {
    background-color: #2E3440;
    color: #88C0D0;
    border-bottom: 2px solid #88C0D0;
}

notebook tab:hover {
    background-color: #434C5E;
}

/* ─── Frame ───────────────────────────────────────────────────────────────── */
frame {
    border: 1px solid #434C5E;
    border-radius: 6px;
}

frame > label {
    color: #88C0D0;
    font-weight: bold;
}

/* ─── InfoBar ─────────────────────────────────────────────────────────────── */
infobar {
    background-color: #434C5E;
    border-bottom: 1px solid #4C566A;
}

infobar.info {
    background-color: #5E81AC;
}

infobar.warning {
    background-color: #EBCB8B;
    color: #2E3440;
}

infobar.error {
    background-color: #BF616A;
}

/* ─── Dialog ──────────────────────────────────────────────────────────────── */
dialog, messagedialog {
    background-color: #2E3440;
}

dialog headerbar, messagedialog headerbar {
    background-color: #3B4252;
}

/* ─── File Chooser ────────────────────────────────────────────────────────── */
filechooser {
    background-color: #2E3440;
    color: #D8DEE9;
}

filechooser .path-bar button {
    background-image: none;
    background-color: #434C5E;
    color: #D8DEE9;
}

/* ─── Print Dialog ────────────────────────────────────────────────────────── */
printdialog {
    background-color: #2E3440;
    color: #D8DEE9;
}

printdialog notebook {
    background-color: #2E3440;
}

printdialog entry {
    background-color: #3B4252;
    color: #ECEFF4;
    border: 1px solid #4C566A;
}

printdialog spinbutton {
    background-color: #3B4252;
    color: #ECEFF4;
}

/* ─── Tooltip ─────────────────────────────────────────────────────────────── */
tooltip {
    background-color: #3B4252;
    color: #ECEFF4;
    border: 1px solid #4C566A;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ─── Progress Bar ────────────────────────────────────────────────────────── */
progressbar trough {
    background-color: #3B4252;
    border-radius: 4px;
    min-height: 6px;
}

progressbar progress {
    background-color: #5E81AC;
    border-radius: 4px;
}

/* ─── Status bar ──────────────────────────────────────────────────────────── */
.statusbar {
    background-color: #3B4252;
    color: #D8DEE9;
    padding: 2px 8px;
    border-top: 1px solid #434C5E;
    font-size: 0.9em;
}

/* ─── Custom Classes ──────────────────────────────────────────────────────── */
.pdf-canvas {
    background-color: #434C5E;
}

.signature-pad {
    background-color: #ECEFF4;
    border: 2px solid #88C0D0;
    border-radius: 6px;
}

.annotation-toolbar {
    background-color: #3B4252;
    border: 1px solid #434C5E;
    border-radius: 6px;
    padding: 4px;
}

.page-indicator {
    color: #88C0D0;
    font-weight: bold;
    font-size: 1.0em;
}

.zoom-indicator {
    color: #8FBCBB;
    font-size: 0.9em;
}
"""


def apply_theme():
    """
    Apply the Nord GTK3 theme to the entire application.

    This loads the CSS stylesheet into a CssProvider and adds it at
    the FALLBACK priority so it styles all widgets application-wide.
    """
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(NORD_CSS.encode('utf-8'))

    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


def get_nord_rgba(color_name):
    """
    Convert a Nord color name to a Gdk.RGBA object.

    Args:
        color_name: e.g. 'nord0', 'nord8', 'nord14'

    Returns:
        Gdk.RGBA with the matching color, or white if not found.
    """
    all_colors = {}
    all_colors.update(NORD_POLAR_NIGHT)
    all_colors.update(NORD_SNOW_STORM)
    all_colors.update(NORD_FROST)
    all_colors.update(NORD_AURORA)

    hex_val = all_colors.get(color_name, '#FFFFFF')
    rgba = Gdk.RGBA()
    rgba.parse(hex_val)
    return rgba


def hex_to_rgb_float(hex_color):
    """
    Convert a hex color string to (r, g, b) floats in [0..1].

    Args:
        hex_color: e.g. '#2E3440'

    Returns:
        Tuple of (red, green, blue) floats.
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)
