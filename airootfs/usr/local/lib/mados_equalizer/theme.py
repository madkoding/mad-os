"""
madOS Audio Equalizer - Nord Theme CSS
=======================================

Provides a complete Nord color theme for the GTK3 equalizer application.
Uses the official Nord color palette for a cohesive dark appearance
matching the madOS desktop environment.

Nord Palette Reference:
    Polar Night: nord0-3 (dark backgrounds)
    Snow Storm:  nord4-6 (light text/foregrounds)
    Frost:       nord7-10 (blue accent colors)
    Aurora:      nord11-15 (status/highlight colors)
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

# Convenience flat dictionary with all colors
NORD = {}
NORD.update(NORD_POLAR_NIGHT)
NORD.update(NORD_SNOW_STORM)
NORD.update(NORD_FROST)
NORD.update(NORD_AURORA)


# Complete GTK3 CSS theme for the equalizer
THEME_CSS = """
/* ============================================
   madOS Audio Equalizer - Nord Theme
   ============================================ */

/* Main window background */
window,
.background {
    background-color: #2E3440;
    color: #D8DEE9;
}

/* Header bar styling */
headerbar,
.titlebar {
    background-color: #2E3440;
    border-bottom: 1px solid #3B4252;
    color: #ECEFF4;
    padding: 4px 8px;
    min-height: 36px;
}

headerbar .title,
.titlebar .title {
    color: #ECEFF4;
    font-weight: bold;
    font-size: 14px;
}

/* General label styling */
label {
    color: #D8DEE9;
}

label.title-label {
    color: #ECEFF4;
    font-weight: bold;
    font-size: 16px;
}

label.subtitle-label {
    color: #81A1C1;
    font-size: 11px;
}

label.freq-label {
    color: #88C0D0;
    font-size: 10px;
    font-weight: bold;
}

label.db-label {
    color: #D8DEE9;
    font-size: 10px;
    font-family: monospace;
}

label.section-label {
    color: #81A1C1;
    font-weight: bold;
    font-size: 12px;
}

label.status-label {
    color: #8FBCBB;
    font-size: 11px;
}

label.device-label {
    color: #88C0D0;
    font-size: 11px;
}

/* Buttons - Frost gradient style */
button {
    background-image: linear-gradient(to bottom, #434C5E, #3B4252);
    border: 1px solid #4C566A;
    border-radius: 4px;
    color: #D8DEE9;
    padding: 4px 12px;
    min-height: 28px;
    transition: all 200ms ease;
}

button:hover {
    background-image: linear-gradient(to bottom, #4C566A, #434C5E);
    border-color: #81A1C1;
    color: #ECEFF4;
}

button:active {
    background-image: linear-gradient(to bottom, #3B4252, #2E3440);
    border-color: #88C0D0;
}

button:disabled {
    background-image: linear-gradient(to bottom, #3B4252, #2E3440);
    color: #4C566A;
    border-color: #3B4252;
}

button.primary-button {
    background-image: linear-gradient(to bottom, #5E81AC, #4C6A8F);
    border-color: #81A1C1;
    color: #ECEFF4;
    font-weight: bold;
}

button.primary-button:hover {
    background-image: linear-gradient(to bottom, #81A1C1, #5E81AC);
    border-color: #88C0D0;
}

button.danger-button {
    background-image: linear-gradient(to bottom, #BF616A, #A54E56);
    border-color: #BF616A;
    color: #ECEFF4;
}

button.danger-button:hover {
    background-image: linear-gradient(to bottom, #D06A73, #BF616A);
    border-color: #D08770;
}

button.toggle-enabled {
    background-image: linear-gradient(to bottom, #A3BE8C, #8FAA78);
    border-color: #A3BE8C;
    color: #2E3440;
    font-weight: bold;
}

button.toggle-enabled:hover {
    background-image: linear-gradient(to bottom, #B4CF9D, #A3BE8C);
}

button.toggle-disabled {
    background-image: linear-gradient(to bottom, #434C5E, #3B4252);
    border-color: #4C566A;
    color: #D8DEE9;
}

/* Combo box styling */
combobox,
combobox button {
    background-image: linear-gradient(to bottom, #434C5E, #3B4252);
    border: 1px solid #4C566A;
    border-radius: 4px;
    color: #D8DEE9;
    min-height: 28px;
}

combobox button:hover {
    border-color: #81A1C1;
}

combobox window,
combobox window menu {
    background-color: #3B4252;
    border: 1px solid #4C566A;
}

combobox window menu menuitem {
    color: #D8DEE9;
    padding: 4px 8px;
}

combobox window menu menuitem:hover {
    background-color: #434C5E;
    color: #ECEFF4;
}

/* Vertical scale (slider) styling */
scale {
    padding: 0;
    margin: 0;
}

scale trough {
    background-color: #3B4252;
    border: 1px solid #434C5E;
    border-radius: 4px;
    min-width: 8px;
}

scale slider {
    background-image: linear-gradient(to bottom, #88C0D0, #5E81AC);
    border: 1px solid #81A1C1;
    border-radius: 50%;
    min-width: 18px;
    min-height: 18px;
    margin: -5px;
}

scale slider:hover {
    background-image: linear-gradient(to bottom, #8FBCBB, #88C0D0);
    border-color: #8FBCBB;
}

scale slider:active {
    background-image: linear-gradient(to bottom, #8FBCBB, #88C0D0);
    border-color: #ECEFF4;
}

scale.master-volume trough {
    background-color: #3B4252;
    min-width: 8px;
}

scale.master-volume highlight {
    background-color: #A3BE8C;
    border-radius: 4px;
}

scale.master-volume slider {
    background-image: linear-gradient(to bottom, #A3BE8C, #8FAA78);
    border: 1px solid #A3BE8C;
}

/* Scale marks */
scale marks mark {
    color: #4C566A;
}

/* Toggle switch styling */
switch {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 12px;
    min-width: 48px;
    min-height: 24px;
}

switch:checked {
    background-color: #A3BE8C;
    border-color: #A3BE8C;
}

switch slider {
    background-color: #ECEFF4;
    border-radius: 50%;
    min-width: 20px;
    min-height: 20px;
    margin: 1px;
}

/* Frame and separator styling */
frame {
    border: 1px solid #3B4252;
    border-radius: 6px;
    padding: 4px;
}

frame > border {
    border: 1px solid #3B4252;
    border-radius: 6px;
}

separator {
    background-color: #3B4252;
    min-height: 1px;
    min-width: 1px;
}

/* Entry (text input) styling */
entry {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 4px;
    color: #D8DEE9;
    padding: 4px 8px;
    min-height: 28px;
    caret-color: #88C0D0;
    selection-background-color: #5E81AC;
    selection-color: #ECEFF4;
}

entry:focus {
    border-color: #88C0D0;
    box-shadow: 0 0 0 1px rgba(136, 192, 208, 0.3);
}

/* Scrollbar styling */
scrollbar {
    background-color: #2E3440;
}

scrollbar slider {
    background-color: #4C566A;
    border-radius: 4px;
    min-width: 6px;
    min-height: 6px;
}

scrollbar slider:hover {
    background-color: #81A1C1;
}

/* Tooltip styling */
tooltip,
tooltip.background {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 4px;
    color: #D8DEE9;
    padding: 4px 8px;
}

/* Dialog styling */
dialog,
messagedialog {
    background-color: #2E3440;
}

messagedialog .dialog-action-area button {
    min-width: 80px;
}

/* Box containers */
.eq-band-box {
    background-color: #3B4252;
    border: 1px solid #434C5E;
    border-radius: 6px;
    padding: 4px;
}

.eq-container {
    background-color: #2E3440;
    padding: 8px;
}

.preset-bar {
    background-color: #3B4252;
    border: 1px solid #434C5E;
    border-radius: 6px;
    padding: 6px 10px;
}

.status-bar {
    background-color: #3B4252;
    border-top: 1px solid #434C5E;
    padding: 4px 10px;
}

.volume-box {
    background-color: #3B4252;
    border: 1px solid #434C5E;
    border-radius: 6px;
    padding: 8px;
}

/* Gain indicator drawing areas */
.gain-positive {
    background-color: #A3BE8C;
}

.gain-negative {
    background-color: #81A1C1;
}

.gain-zero {
    background-color: #4C566A;
}

/* Menu styling */
menu {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 4px;
    padding: 4px 0;
}

menu menuitem {
    color: #D8DEE9;
    padding: 4px 12px;
}

menu menuitem:hover {
    background-color: #434C5E;
    color: #ECEFF4;
}

/* Popover styling */
popover,
popover.background {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 6px;
}
"""


def apply_theme():
    """Apply the Nord theme CSS to the GTK3 application.

    Loads the CSS stylesheet and applies it to the default screen
    with APPLICATION priority so it overrides the default theme
    but can still be overridden by user stylesheets.

    Returns:
        True if the theme was applied successfully, False otherwise.
    """
    try:
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(THEME_CSS.encode('utf-8'))

        screen = Gdk.Screen.get_default()
        if screen is None:
            print("Warning: No default screen available for theme application")
            return False

        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        return True
    except Exception as e:
        print(f"Warning: Could not apply theme: {e}")
        return False


def get_gain_color(gain_db):
    """Get the appropriate color for a gain level indicator.

    Args:
        gain_db: The gain value in decibels.

    Returns:
        A Gdk.RGBA color object representing the gain level:
            - Positive gains: green (#A3BE8C) to yellow (#EBCB8B) gradient
            - Negative gains: blue (#81A1C1)
            - Zero: gray (#4C566A)
    """
    color = Gdk.RGBA()

    if abs(gain_db) < 0.1:
        # Zero / near-zero: gray
        color.parse('#4C566A')
    elif gain_db > 0:
        # Positive: interpolate from green to yellow based on intensity
        ratio = min(gain_db / 12.0, 1.0)
        # Green: #A3BE8C = (163, 190, 140)
        # Yellow: #EBCB8B = (235, 203, 139)
        r = (163 + (235 - 163) * ratio) / 255.0
        g = (190 + (203 - 190) * ratio) / 255.0
        b = (140 + (139 - 140) * ratio) / 255.0
        color.red = r
        color.green = g
        color.blue = b
        color.alpha = 1.0
    else:
        # Negative: blue with variable intensity
        ratio = min(abs(gain_db) / 12.0, 1.0)
        # Base blue: #81A1C1 = (129, 161, 193)
        # Darker blue: #5E81AC = (94, 129, 172)
        r = (94 + (129 - 94) * (1.0 - ratio)) / 255.0
        g = (129 + (161 - 129) * (1.0 - ratio)) / 255.0
        b = (172 + (193 - 172) * (1.0 - ratio)) / 255.0
        color.red = r
        color.green = g
        color.blue = b
        color.alpha = 1.0

    return color


def get_gain_color_hex(gain_db):
    """Get the appropriate hex color string for a gain level.

    Args:
        gain_db: The gain value in decibels.

    Returns:
        A hex color string (e.g., '#A3BE8C').
    """
    if abs(gain_db) < 0.1:
        return '#4C566A'
    elif gain_db > 0:
        ratio = min(gain_db / 12.0, 1.0)
        r = int(163 + (235 - 163) * ratio)
        g = int(190 + (203 - 190) * ratio)
        b = int(140 + (139 - 140) * ratio)
        return f'#{r:02X}{g:02X}{b:02X}'
    else:
        ratio = min(abs(gain_db) / 12.0, 1.0)
        r = int(94 + (129 - 94) * (1.0 - ratio))
        g = int(129 + (161 - 129) * (1.0 - ratio))
        b = int(172 + (193 - 172) * (1.0 - ratio))
        return f'#{r:02X}{g:02X}{b:02X}'
