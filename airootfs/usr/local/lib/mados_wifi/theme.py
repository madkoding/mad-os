"""madOS WiFi Configuration - Nord theme CSS for GTK3.

Implements the Nord color palette across all GTK3 widgets used
in the WiFi configuration utility.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

# Nord Color Palette
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

# Convenient flat access
NORD = {**NORD_POLAR_NIGHT, **NORD_SNOW_STORM, **NORD_FROST, **NORD_AURORA}

THEME_CSS = """
/* ===== Global Window ===== */
window, .background {
    background-color: """ + NORD['nord0'] + """;
    color: """ + NORD['nord4'] + """;
}

/* ===== Header Bar ===== */
headerbar, .titlebar {
    background: linear-gradient(to bottom, """ + NORD['nord1'] + """, """ + NORD['nord0'] + """);
    border-bottom: 1px solid """ + NORD['nord2'] + """;
    color: """ + NORD['nord6'] + """;
    padding: 4px 8px;
}

headerbar .title {
    color: """ + NORD['nord6'] + """;
    font-weight: bold;
}

/* ===== Buttons ===== */
button {
    background: linear-gradient(to bottom, """ + NORD['nord9'] + """, """ + NORD['nord10'] + """);
    color: """ + NORD['nord6'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 500;
    transition: all 200ms ease;
}

button:hover {
    background: linear-gradient(to bottom, """ + NORD['nord8'] + """, """ + NORD['nord9'] + """);
    border-color: """ + NORD['nord8'] + """;
}

button:active {
    background: """ + NORD['nord10'] + """;
}

button:disabled {
    background: """ + NORD['nord2'] + """;
    color: """ + NORD['nord3'] + """;
    border-color: """ + NORD['nord2'] + """;
}

button.destructive-action {
    background: linear-gradient(to bottom, """ + NORD['nord11'] + """, #a5525a);
    border-color: """ + NORD['nord11'] + """;
}

button.destructive-action:hover {
    background: linear-gradient(to bottom, #d06a73, """ + NORD['nord11'] + """);
}

button.suggested-action {
    background: linear-gradient(to bottom, """ + NORD['nord14'] + """, #8daa76);
    color: """ + NORD['nord0'] + """;
    border-color: """ + NORD['nord14'] + """;
}

button.suggested-action:hover {
    background: linear-gradient(to bottom, #b3ce9c, """ + NORD['nord14'] + """);
}

button.flat {
    background: transparent;
    border: none;
    color: """ + NORD['nord4'] + """;
}

button.flat:hover {
    background: """ + NORD['nord2'] + """;
}

/* ===== Network List Rows ===== */
list, listbox {
    background-color: """ + NORD['nord0'] + """;
    border: none;
}

list row, listbox row {
    background-color: """ + NORD['nord1'] + """;
    border-bottom: 1px solid """ + NORD['nord0'] + """;
    padding: 8px 12px;
    transition: background-color 150ms ease;
}

list row:hover, listbox row:hover {
    background-color: """ + NORD['nord2'] + """;
}

list row:selected, listbox row:selected {
    background-color: """ + NORD['nord10'] + """;
    color: """ + NORD['nord6'] + """;
}

list row:selected:hover, listbox row:selected:hover {
    background-color: """ + NORD['nord9'] + """;
}

/* ===== Signal Strength Indicators ===== */
.signal-excellent {
    color: """ + NORD['nord14'] + """;
}

.signal-good {
    color: """ + NORD['nord7'] + """;
}

.signal-fair {
    color: """ + NORD['nord13'] + """;
}

.signal-weak {
    color: """ + NORD['nord12'] + """;
}

.signal-none {
    color: """ + NORD['nord11'] + """;
}

/* ===== Status Indicators ===== */
.status-connected {
    color: """ + NORD['nord14'] + """;
}

.status-connecting {
    color: """ + NORD['nord13'] + """;
}

.status-error {
    color: """ + NORD['nord11'] + """;
}

.status-disconnected {
    color: """ + NORD['nord3'] + """;
}

/* ===== Entry Fields ===== */
entry {
    background-color: """ + NORD['nord1'] + """;
    color: """ + NORD['nord6'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 4px;
    padding: 6px 10px;
    caret-color: """ + NORD['nord8'] + """;
}

entry:focus {
    border-color: """ + NORD['nord8'] + """;
    box-shadow: 0 0 0 1px """ + NORD['nord8'] + """;
}

entry:disabled {
    background-color: """ + NORD['nord2'] + """;
    color: """ + NORD['nord3'] + """;
}

/* ===== Labels ===== */
label {
    color: """ + NORD['nord4'] + """;
}

label.heading {
    color: """ + NORD['nord6'] + """;
    font-weight: bold;
    font-size: 14px;
}

label.caption {
    color: """ + NORD['nord3'] + """;
    font-size: 11px;
}

label.ssid-label {
    color: """ + NORD['nord6'] + """;
    font-weight: 600;
    font-size: 13px;
}

label.security-label {
    color: """ + NORD['nord9'] + """;
    font-size: 11px;
}

label.connected-label {
    color: """ + NORD['nord14'] + """;
    font-weight: bold;
    font-size: 11px;
}

label.detail-key {
    color: """ + NORD['nord3'] + """;
    font-size: 12px;
}

label.detail-value {
    color: """ + NORD['nord4'] + """;
    font-size: 12px;
}

label.ip-label {
    color: """ + NORD['nord8'] + """;
    font-size: 11px;
    font-family: monospace;
}

/* ===== Switches ===== */
switch {
    background-color: """ + NORD['nord3'] + """;
    border-radius: 12px;
    border: none;
}

switch:checked {
    background-color: """ + NORD['nord14'] + """;
}

switch slider {
    background-color: """ + NORD['nord6'] + """;
    border-radius: 50%;
    border: none;
    min-width: 20px;
    min-height: 20px;
}

/* ===== Scales / Sliders ===== */
scale trough {
    background-color: """ + NORD['nord2'] + """;
    border-radius: 4px;
    min-height: 6px;
}

scale trough highlight {
    background-color: """ + NORD['nord8'] + """;
    border-radius: 4px;
}

scale slider {
    background-color: """ + NORD['nord6'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 50%;
    min-width: 16px;
    min-height: 16px;
}

/* ===== Combo Boxes ===== */
combobox, combobox button {
    background-color: """ + NORD['nord1'] + """;
    color: """ + NORD['nord4'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 4px;
}

combobox button:hover {
    background-color: """ + NORD['nord2'] + """;
}

/* ===== Scrollbars ===== */
scrollbar {
    background-color: """ + NORD['nord0'] + """;
}

scrollbar slider {
    background-color: """ + NORD['nord3'] + """;
    border-radius: 4px;
    min-width: 6px;
    min-height: 6px;
}

scrollbar slider:hover {
    background-color: """ + NORD['nord9'] + """;
}

scrollbar slider:active {
    background-color: """ + NORD['nord8'] + """;
}

/* ===== Separators ===== */
separator {
    background-color: """ + NORD['nord2'] + """;
    min-height: 1px;
}

/* ===== Frames ===== */
frame {
    border: 1px solid """ + NORD['nord2'] + """;
    border-radius: 6px;
}

frame > label {
    color: """ + NORD['nord9'] + """;
    font-weight: bold;
}

/* ===== Notebooks / Tabs ===== */
notebook {
    background-color: """ + NORD['nord0'] + """;
}

notebook header {
    background-color: """ + NORD['nord1'] + """;
    border-bottom: 1px solid """ + NORD['nord2'] + """;
}

notebook tab {
    background-color: """ + NORD['nord1'] + """;
    color: """ + NORD['nord3'] + """;
    padding: 6px 14px;
    border: none;
}

notebook tab:checked {
    background-color: """ + NORD['nord0'] + """;
    color: """ + NORD['nord8'] + """;
    border-bottom: 2px solid """ + NORD['nord8'] + """;
}

notebook tab:hover:not(:checked) {
    color: """ + NORD['nord4'] + """;
    background-color: """ + NORD['nord2'] + """;
}

/* ===== Spinner ===== */
spinner {
    color: """ + NORD['nord8'] + """;
}

/* ===== Dialogs ===== */
dialog .dialog-vbox {
    background-color: """ + NORD['nord0'] + """;
}

messagedialog .dialog-vbox {
    background-color: """ + NORD['nord0'] + """;
}

messagedialog label {
    color: """ + NORD['nord4'] + """;
}

/* ===== Progress Bar ===== */
progressbar trough {
    background-color: """ + NORD['nord2'] + """;
    border-radius: 4px;
    min-height: 8px;
}

progressbar progress {
    background-color: """ + NORD['nord8'] + """;
    border-radius: 4px;
}

/* ===== Check Buttons ===== */
checkbutton check {
    background-color: """ + NORD['nord1'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 3px;
}

checkbutton check:checked {
    background-color: """ + NORD['nord8'] + """;
    border-color: """ + NORD['nord8'] + """;
}

checkbutton label {
    color: """ + NORD['nord4'] + """;
}

/* ===== Tooltip ===== */
tooltip {
    background-color: """ + NORD['nord1'] + """;
    color: """ + NORD['nord4'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 4px;
}

/* ===== Status Bar Area ===== */
.statusbar {
    background-color: """ + NORD['nord1'] + """;
    border-top: 1px solid """ + NORD['nord2'] + """;
    padding: 4px 12px;
}

.statusbar label {
    font-size: 11px;
}

/* ===== Detail Panel ===== */
.detail-panel {
    background-color: """ + NORD['nord1'] + """;
    border-radius: 6px;
    padding: 12px;
}

/* ===== Network Row Specific ===== */
.network-row {
    padding: 10px 14px;
}

.network-row-connected {
    border-left: 3px solid """ + NORD['nord14'] + """;
}
"""


def apply_theme():
    """Apply the Nord GTK3 CSS theme to the application.

    Loads the CSS stylesheet and applies it to the default
    screen with the highest priority so it overrides any
    system theme.
    """
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(THEME_CSS.encode('utf-8'))

    screen = Gdk.Screen.get_default()
    if screen is not None:
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 100
        )
