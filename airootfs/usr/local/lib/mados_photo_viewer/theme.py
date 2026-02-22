"""
madOS Photo Viewer - Nord Theme
================================

Applies Nord color scheme CSS to GTK3 widgets. Covers window backgrounds,
buttons, toolbars, scales/sliders, labels, entries, scrollbars, menus,
and various interactive elements.

Nord palette reference:
    Polar Night: #2E3440 #3B4252 #434C5E #4C566A
    Snow Storm:  #D8DEE9 #E5E9F0 #ECEFF4
    Frost:       #8FBCBB #88C0D0 #81A1C1 #5E81AC
    Aurora:      #BF616A #D08770 #EBCB8B #A3BE8C #B48EAD
"""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

# Nord color constants
NORD_POLAR_NIGHT = {
    "nord0": "#2E3440",
    "nord1": "#3B4252",
    "nord2": "#434C5E",
    "nord3": "#4C566A",
}

NORD_SNOW_STORM = {
    "nord4": "#D8DEE9",
    "nord5": "#E5E9F0",
    "nord6": "#ECEFF4",
}

NORD_FROST = {
    "nord7": "#8FBCBB",
    "nord8": "#88C0D0",
    "nord9": "#81A1C1",
    "nord10": "#5E81AC",
}

NORD_AURORA = {
    "nord11": "#BF616A",
    "nord12": "#D08770",
    "nord13": "#EBCB8B",
    "nord14": "#A3BE8C",
    "nord15": "#B48EAD",
}

# Flattened for easy access
NORD = {}
NORD.update(NORD_POLAR_NIGHT)
NORD.update(NORD_SNOW_STORM)
NORD.update(NORD_FROST)
NORD.update(NORD_AURORA)

_CSS_END_COLOR = ';\n    color: '
_CSS_END_COLOR_CLOSE = ');\n    color: '
_CSS_END_BORDER = ';\n    border: 1px solid '
_CSS_END_BORDER_COLOR = ';\n    border-color: '
_CSS_END_BORDER_COLOR_CLOSE = ');\n    border-color: '

NORD_CSS = (
    """
/* ===== madOS Photo Viewer - Nord Theme ===== */

/* Window and general background */
window, .background {
    background-color: """
    + NORD["nord0"]
    + _CSS_END_COLOR
    + NORD["nord4"]
    + """;
}

/* Header bar */
headerbar {
    background: linear-gradient(to bottom, """
    + NORD["nord1"]
    + """, """
    + NORD["nord0"]
    + """);
    border-bottom: 1px solid """
    + NORD["nord2"]
    + _CSS_END_COLOR
    + NORD["nord4"]
    + """;
    padding: 4px 8px;
}

headerbar .title {
    color: """
    + NORD["nord6"]
    + """;
    font-weight: bold;
}

/* General buttons */
button {
    background: linear-gradient(to bottom, """
    + NORD["nord9"]
    + """, """
    + NORD["nord10"]
    + _CSS_END_COLOR_CLOSE
    + NORD["nord6"]
    + _CSS_END_BORDER
    + NORD["nord3"]
    + """;
    border-radius: 4px;
    padding: 4px 10px;
    min-height: 24px;
    transition: all 200ms ease;
}

button:hover {
    background: linear-gradient(to bottom, """
    + NORD["nord8"]
    + """, """
    + NORD["nord9"]
    + _CSS_END_BORDER_COLOR_CLOSE
    + NORD["nord8"]
    + """;
}

button:active, button:checked {
    background: linear-gradient(to bottom, """
    + NORD["nord10"]
    + """, """
    + NORD["nord9"]
    + _CSS_END_BORDER_COLOR_CLOSE
    + NORD["nord7"]
    + """;
}

button:disabled {
    background: """
    + NORD["nord2"]
    + _CSS_END_COLOR
    + NORD["nord3"]
    + _CSS_END_BORDER_COLOR
    + NORD["nord2"]
    + """;
}

/* Toggle buttons (tool selection) */
togglebutton:checked, .toggle:checked {
    background: linear-gradient(to bottom, """
    + NORD["nord7"]
    + """, """
    + NORD["nord8"]
    + _CSS_END_COLOR_CLOSE
    + NORD["nord0"]
    + _CSS_END_BORDER_COLOR
    + NORD["nord7"]
    + """;
    font-weight: bold;
}

/* Toolbars */
toolbar, .toolbar {
    background-color: """
    + NORD["nord1"]
    + """;
    border-bottom: 1px solid """
    + NORD["nord2"]
    + """;
    padding: 2px 4px;
}

/* Box used as toolbar */
.tool-bar {
    background-color: """
    + NORD["nord1"]
    + """;
    border-bottom: 1px solid """
    + NORD["nord2"]
    + """;
    padding: 4px 8px;
}

/* Status bar */
.status-bar {
    background-color: """
    + NORD["nord1"]
    + """;
    border-top: 1px solid """
    + NORD["nord2"]
    + """;
    padding: 2px 8px;
    color: """
    + NORD["nord4"]
    + """;
    font-size: 12px;
}

/* Labels */
label {
    color: """
    + NORD["nord4"]
    + """;
}

.dim-label {
    color: """
    + NORD["nord3"]
    + """;
}

/* Entries (text input) */
entry {
    background-color: """
    + NORD["nord1"]
    + _CSS_END_COLOR
    + NORD["nord6"]
    + _CSS_END_BORDER
    + NORD["nord3"]
    + """;
    border-radius: 4px;
    padding: 4px 8px;
    caret-color: """
    + NORD["nord8"]
    + """;
}

entry:focus {
    border-color: """
    + NORD["nord8"]
    + """;
    box-shadow: 0 0 2px """
    + NORD["nord8"]
    + """;
}

/* Scales (sliders) */
scale trough {
    background-color: """
    + NORD["nord2"]
    + """;
    border-radius: 4px;
    min-height: 6px;
}

scale highlight {
    background: linear-gradient(to right, """
    + NORD["nord9"]
    + """, """
    + NORD["nord8"]
    + """);
    border-radius: 4px;
    min-height: 6px;
}

scale slider {
    background: """
    + NORD["nord8"]
    + """;
    border: 2px solid """
    + NORD["nord10"]
    + """;
    border-radius: 50%;
    min-width: 16px;
    min-height: 16px;
}

scale slider:hover {
    background: """
    + NORD["nord7"]
    + """;
}

/* Scrollbars */
scrollbar {
    background-color: """
    + NORD["nord0"]
    + """;
}

scrollbar slider {
    background-color: """
    + NORD["nord3"]
    + """;
    border-radius: 4px;
    min-width: 8px;
    min-height: 8px;
}

scrollbar slider:hover {
    background-color: """
    + NORD["nord9"]
    + """;
}

scrollbar slider:active {
    background-color: """
    + NORD["nord8"]
    + """;
}

/* Menus and Popovers */
menu, .context-menu, popover {
    background-color: """
    + NORD["nord1"]
    + _CSS_END_BORDER
    + NORD["nord3"]
    + """;
    border-radius: 4px;
    color: """
    + NORD["nord4"]
    + """;
    padding: 4px 0;
}

menuitem {
    padding: 6px 12px;
    color: """
    + NORD["nord4"]
    + """;
}

menuitem:hover {
    background-color: """
    + NORD["nord9"]
    + _CSS_END_COLOR
    + NORD["nord6"]
    + """;
}

/* Separators */
separator {
    background-color: """
    + NORD["nord2"]
    + """;
    min-height: 1px;
    min-width: 1px;
}

/* Combo boxes */
combobox button {
    background: """
    + NORD["nord1"]
    + _CSS_END_BORDER
    + NORD["nord3"]
    + _CSS_END_COLOR
    + NORD["nord4"]
    + """;
}

combobox button:hover {
    border-color: """
    + NORD["nord8"]
    + """;
}

/* Notebooks / Tabs */
notebook {
    background-color: """
    + NORD["nord0"]
    + """;
}

notebook tab {
    background-color: """
    + NORD["nord1"]
    + _CSS_END_COLOR
    + NORD["nord4"]
    + """;
    padding: 4px 12px;
    border: 1px solid """
    + NORD["nord2"]
    + """;
}

notebook tab:checked {
    background-color: """
    + NORD["nord0"]
    + """;
    border-bottom-color: """
    + NORD["nord0"]
    + _CSS_END_COLOR
    + NORD["nord8"]
    + """;
}

/* File chooser dialog */
.file-chooser, filechooser {
    background-color: """
    + NORD["nord0"]
    + """;
}

/* Tooltips */
tooltip {
    background-color: """
    + NORD["nord1"]
    + _CSS_END_BORDER
    + NORD["nord3"]
    + """;
    border-radius: 4px;
    color: """
    + NORD["nord4"]
    + """;
    padding: 4px 8px;
}

/* Message dialogs */
messagedialog {
    background-color: """
    + NORD["nord0"]
    + """;
}

messagedialog .titlebar {
    background: """
    + NORD["nord1"]
    + """;
}

/* Progress bars (for video seek) */
progressbar trough {
    background-color: """
    + NORD["nord2"]
    + """;
    border-radius: 4px;
    min-height: 8px;
}

progressbar progress {
    background: linear-gradient(to right, """
    + NORD["nord10"]
    + """, """
    + NORD["nord8"]
    + """);
    border-radius: 4px;
    min-height: 8px;
}

/* Specific app classes */
.nav-button {
    background: linear-gradient(to bottom, """
    + NORD["nord2"]
    + """, """
    + NORD["nord1"]
    + _CSS_END_COLOR_CLOSE
    + NORD["nord4"]
    + _CSS_END_BORDER_COLOR
    + NORD["nord3"]
    + """;
    font-size: 18px;
    min-width: 36px;
    min-height: 36px;
    border-radius: 18px;
}

.nav-button:hover {
    background: linear-gradient(to bottom, """
    + NORD["nord3"]
    + """, """
    + NORD["nord2"]
    + _CSS_END_COLOR_CLOSE
    + NORD["nord8"]
    + """;
}

.zoom-button {
    font-size: 14px;
    padding: 2px 8px;
    min-width: 30px;
}

.tool-button {
    padding: 4px 10px;
    min-height: 28px;
    font-size: 12px;
}

.tool-button:checked {
    background: linear-gradient(to bottom, """
    + NORD["nord7"]
    + """, """
    + NORD["nord8"]
    + _CSS_END_COLOR_CLOSE
    + NORD["nord0"]
    + """;
    font-weight: bold;
}

.destructive-action {
    background: linear-gradient(to bottom, """
    + NORD["nord11"]
    + """, #a5525a);
    color: """
    + NORD["nord6"]
    + _CSS_END_BORDER_COLOR
    + NORD["nord11"]
    + """;
}

.destructive-action:hover {
    background: linear-gradient(to bottom, #cf717a, """
    + NORD["nord11"]
    + """);
}

.suggested-action {
    background: linear-gradient(to bottom, """
    + NORD["nord14"]
    + """, #8fa87a);
    color: """
    + NORD["nord0"]
    + _CSS_END_BORDER_COLOR
    + NORD["nord14"]
    + """;
}

.canvas-area {
    background-color: """
    + NORD["nord0"]
    + """;
}

.video-controls {
    background-color: """
    + NORD["nord1"]
    + """;
    border-top: 1px solid """
    + NORD["nord2"]
    + """;
    padding: 6px 8px;
}
"""
)


def apply_theme():
    """Apply the Nord CSS theme to the GTK application.

    Loads the CSS and attaches it to the default screen so all windows
    and widgets inherit the Nord styling.
    """
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(NORD_CSS.encode("utf-8"))

    screen = Gdk.Screen.get_default()
    if screen is not None:
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def get_gdk_rgba(nord_key):
    """Convert a Nord color key to a Gdk.RGBA object.

    Args:
        nord_key: A key from the NORD dictionary (e.g. 'nord8').

    Returns:
        A Gdk.RGBA color object.
    """
    rgba = Gdk.RGBA()
    rgba.parse(NORD[nord_key])
    return rgba


def hex_to_rgb(hex_color):
    """Convert a hex color string to an (r, g, b) tuple with values 0.0-1.0.

    Args:
        hex_color: Color string like '#88C0D0'.

    Returns:
        Tuple of (red, green, blue) floats.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)
