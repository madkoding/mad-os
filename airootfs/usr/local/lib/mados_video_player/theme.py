"""
madOS Video Player - Nord Theme
================================

Applies Nord color scheme CSS to GTK3 widgets. The video player uses
a dark VLC-inspired interface with Nord color accents.

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
NORD = {
    "nord0": "#2E3440",
    "nord1": "#3B4252",
    "nord2": "#434C5E",
    "nord3": "#4C566A",
    "nord4": "#D8DEE9",
    "nord5": "#E5E9F0",
    "nord6": "#ECEFF4",
    "nord7": "#8FBCBB",
    "nord8": "#88C0D0",
    "nord9": "#81A1C1",
    "nord10": "#5E81AC",
    "nord11": "#BF616A",
    "nord12": "#D08770",
    "nord13": "#EBCB8B",
    "nord14": "#A3BE8C",
    "nord15": "#B48EAD",
}

NORD_CSS = """
/* ===== madOS Video Player - Nord Theme ===== */

/* Window and general background */
window, .background {{
    background-color: {nord0};
    color: {nord4};
}}

/* Menu bar */
menubar {{
    background-color: {nord1};
    border-bottom: 1px solid {nord2};
    color: {nord4};
    padding: 0;
}}

menubar > menuitem {{
    padding: 4px 8px;
    color: {nord4};
}}

menubar > menuitem:hover {{
    background-color: {nord9};
    color: {nord6};
}}

/* Menus and Popovers */
menu, .context-menu, popover {{
    background-color: {nord1};
    border: 1px solid {nord3};
    border-radius: 4px;
    color: {nord4};
    padding: 4px 0;
}}

menuitem {{
    padding: 6px 12px;
    color: {nord4};
}}

menuitem:hover {{
    background-color: {nord9};
    color: {nord6};
}}

/* General buttons */
button {{
    background: linear-gradient(to bottom, {nord2}, {nord1});
    color: {nord4};
    border: 1px solid {nord3};
    border-radius: 4px;
    padding: 4px 10px;
    min-height: 24px;
    transition: all 200ms ease;
}}

button:hover {{
    background: linear-gradient(to bottom, {nord3}, {nord2});
    border-color: {nord8};
    color: {nord6};
}}

button:active, button:checked {{
    background: linear-gradient(to bottom, {nord10}, {nord9});
    border-color: {nord7};
    color: {nord6};
}}

button:disabled {{
    background: {nord1};
    color: {nord3};
    border-color: {nord2};
}}

/* Transport button (play/pause/stop) */
.transport-btn {{
    font-size: 22px;
    min-width: 44px;
    min-height: 44px;
    border-radius: 4px;
    padding: 4px;
}}

.transport-btn.play-btn {{
    background: linear-gradient(to bottom, {nord9}, {nord10});
    color: {nord6};
    border-color: {nord9};
}}

.transport-btn.play-btn:hover {{
    background: linear-gradient(to bottom, {nord8}, {nord9});
}}

/* Control bar at bottom */
.control-bar {{
    background-color: {nord1};
    border-top: 1px solid {nord2};
    padding: 4px 8px;
}}

/* Seek bar area */
.seek-bar {{
    background-color: {nord0};
    padding: 4px 8px 0 8px;
}}

/* Labels */
label {{
    color: {nord4};
}}

.time-label {{
    color: {nord8};
    font-family: "DSEG7 Classic", "DSEG7 Modern", "Digital-7", monospace;
    font-size: 14px;
    text-shadow: 0 0 6px rgba(136, 192, 208, 0.7), 0 0 12px rgba(136, 192, 208, 0.4);
    letter-spacing: 1px;
}}

.title-label {{
    color: {nord6};
    font-weight: bold;
    font-size: 13px;
}}

/* Scales (sliders) */
scale trough {{
    background-color: {nord2};
    border-radius: 4px;
    min-height: 6px;
}}

scale highlight {{
    background: linear-gradient(to right, {nord9}, {nord8});
    border-radius: 4px;
    min-height: 6px;
}}

scale slider {{
    background: {nord8};
    border: 2px solid {nord10};
    border-radius: 50%;
    min-width: 14px;
    min-height: 14px;
}}

scale slider:hover {{
    background: {nord7};
}}

/* Seek slider (wider) */
.seek-slider trough {{
    min-height: 8px;
}}

.seek-slider slider {{
    min-width: 16px;
    min-height: 16px;
}}

/* Volume slider */
.volume-slider {{
    min-width: 80px;
}}

.volume-slider trough {{
    min-height: 4px;
}}

.volume-slider slider {{
    min-width: 12px;
    min-height: 12px;
}}

/* Video area */
.video-area {{
    background-color: #000000;
}}

/* Placeholder area */
.video-placeholder {{
    background-color: {nord0};
}}

.placeholder-text {{
    color: {nord3};
    font-size: 18px;
}}

.placeholder-icon {{
    color: {nord3};
    font-size: 64px;
}}

/* Playlist panel */
.playlist-panel {{
    background-color: {nord1};
    border-left: 1px solid {nord2};
}}

.playlist-header {{
    background-color: {nord2};
    padding: 8px;
    border-bottom: 1px solid {nord3};
}}

.playlist-header label {{
    color: {nord6};
    font-weight: bold;
    font-size: 13px;
}}

/* TreeView (playlist items) */
treeview {{
    background-color: {nord1};
    color: {nord4};
}}

treeview:selected {{
    background-color: {nord9};
    color: {nord6};
}}

treeview:hover {{
    background-color: {nord2};
}}

treeview header button {{
    background-color: {nord2};
    color: {nord4};
    border: none;
    border-bottom: 1px solid {nord3};
    padding: 4px 8px;
}}

/* Scrollbars */
scrollbar {{
    background-color: {nord0};
}}

scrollbar slider {{
    background-color: {nord3};
    border-radius: 4px;
    min-width: 6px;
    min-height: 6px;
}}

scrollbar slider:hover {{
    background-color: {nord9};
}}

scrollbar slider:active {{
    background-color: {nord8};
}}

/* Separators */
separator {{
    background-color: {nord2};
    min-height: 1px;
    min-width: 1px;
}}

/* Status bar */
.status-bar {{
    background-color: {nord1};
    border-top: 1px solid {nord2};
    padding: 2px 8px;
    color: {nord4};
    font-size: 11px;
}}

/* Tooltips */
tooltip {{
    background-color: {nord1};
    border: 1px solid {nord3};
    border-radius: 4px;
    color: {nord4};
    padding: 4px 8px;
}}

/* Message dialogs */
messagedialog {{
    background-color: {nord0};
}}

messagedialog .titlebar {{
    background: {nord1};
}}

/* Playlist drag handle / toolbar buttons */
.playlist-toolbar button {{
    padding: 2px 6px;
    min-height: 20px;
    font-size: 11px;
}}

/* Active playlist item indicator */
.now-playing {{
    color: {nord8};
    font-weight: bold;
}}

/* Speed label */
.speed-label {{
    color: {nord13};
    font-size: 11px;
    font-weight: bold;
}}

/* Fullscreen overlay controls */
.fullscreen-controls {{
    background-color: rgba(46, 52, 64, 0.85);
    border-radius: 8px;
    padding: 8px 16px;
}}
""".format(**NORD)


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
