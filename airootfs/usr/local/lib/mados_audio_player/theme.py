"""
madOS Audio Player - Nord Theme CSS (Winamp-inspired)
=====================================================

Provides a complete Nord color theme for the GTK3 audio player.
The design is inspired by Winamp's classic compact layout with
the official Nord color palette for madOS desktop integration.

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

# Convenience flat dictionary
NORD = {}
NORD.update(NORD_POLAR_NIGHT)
NORD.update(NORD_SNOW_STORM)
NORD.update(NORD_FROST)
NORD.update(NORD_AURORA)


THEME_CSS = """
/* ============================================
   madOS Audio Player - Nord Winamp Theme
   ============================================ */

/* --- Base Window --- */
window, .background {
    background-color: """ + NORD['nord0'] + """;
    color: """ + NORD['nord4'] + """;
}

/* --- Header Bar --- */
headerbar {
    background-color: """ + NORD['nord1'] + """;
    border-bottom: 1px solid """ + NORD['nord0'] + """;
    padding: 2px 6px;
    min-height: 28px;
}
headerbar .title {
    color: """ + NORD['nord8'] + """;
    font-weight: bold;
    font-size: 11px;
}

/* --- Track Info Display (Winamp title bar style) --- */
.track-display {
    background-color: transparent;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 3px;
    padding: 10px 10px 6px 10px;
}
.track-title {
    color: """ + NORD['nord8'] + """;
    font-family: "Doto", "DSEG14 Classic", "JetBrainsMono Nerd Font", monospace;
    font-size: 13px;
    font-weight: 400;
    letter-spacing: 1px;
    text-shadow:
        0 0 6px """ + NORD['nord8'] + """,
        0 0 10px rgba(136, 192, 208, 0.6),
        0 0 14px rgba(136, 192, 208, 0.4);
}
.track-artist {
    color: """ + NORD['nord9'] + """;
    font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", monospace;
    font-size: 10px;
}
.track-info {
    color: """ + NORD['nord3'] + """;
    font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", monospace;
    font-size: 9px;
}
.time-display {
    color: #ff3366;
    font-family: "DSEG7 Classic", "JetBrainsMono Nerd Font", monospace;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-shadow:
        0 0 8px #ff3366,
        0 0 12px #ff3366,
        0 0 16px rgba(255, 51, 102, 0.8),
        0 0 20px rgba(255, 51, 102, 0.5);
    background: linear-gradient(135deg, rgba(255, 51, 102, 0.08), rgba(220, 30, 80, 0.04));
    border-radius: 4px;
    padding: 2px 8px;
}
.time-total {
    color: #ff3366;
    font-family: "DSEG7 Classic", "JetBrainsMono Nerd Font", monospace;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 1px;
    text-shadow:
        0 0 8px #ff3366,
        0 0 12px #ff3366,
        0 0 16px rgba(255, 51, 102, 0.8),
        0 0 20px rgba(255, 51, 102, 0.5);
}
.audio-info-box {
    padding: 3px 8px;
}
.bitrate-label {
    color: """ + NORD['nord13'] + """;
    font-family: "DSEG14 Classic", "JetBrainsMono Nerd Font", monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-shadow:
        0 0 6px """ + NORD['nord13'] + """,
        0 0 10px rgba(235, 203, 139, 0.6),
        0 0 14px rgba(235, 203, 139, 0.3);
}
.samplerate-label {
    color: """ + NORD['nord15'] + """;
    font-family: "DSEG14 Classic", "JetBrainsMono Nerd Font", monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-shadow:
        0 0 6px """ + NORD['nord15'] + """,
        0 0 10px rgba(180, 142, 173, 0.6),
        0 0 14px rgba(180, 142, 173, 0.3);
}
.info-unit-label {
    color: """ + NORD['nord4'] + """;
    font-family: "Nimbus Sans", "Nimbus Sans L", "Helvetica", "Arial", sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

/* --- Seek Bar --- */
.seek-bar trough {
    background-color: """ + NORD['nord1'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 2px;
    min-height: 8px;
}
.seek-bar highlight {
    background-color: """ + NORD['nord8'] + """;
    border-radius: 2px;
    min-height: 8px;
}
.seek-bar slider {
    background-color: """ + NORD['nord6'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 50%;
    min-width: 14px;
    min-height: 14px;
    margin: -4px;
}
.seek-bar slider:hover {
    background-color: """ + NORD['nord8'] + """;
}

/* --- Transport Controls (Play, Pause, Stop, etc.) --- */
.transport-btn {
    background-color: """ + NORD['nord1'] + """;
    color: """ + NORD['nord4'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 3px;
    padding: 4px 8px;
    min-width: 32px;
    min-height: 32px;    font-family: "JetBrainsMono Nerd Font", "Symbols Nerd Font", monospace;    font-size: 16px;
}
.transport-btn:hover {
    background-color: """ + NORD['nord2'] + """;
    color: """ + NORD['nord8'] + """;
    border-color: """ + NORD['nord8'] + """;
}
.transport-btn:active {
    background-color: """ + NORD['nord10'] + """;
}
.transport-btn.play-btn {
    color: """ + NORD['nord14'] + """;
}
.transport-btn.play-btn:hover {
    color: """ + NORD['nord14'] + """;
    border-color: """ + NORD['nord14'] + """;
}
.transport-btn.stop-btn {
    color: """ + NORD['nord11'] + """;
}
.transport-btn.stop-btn:hover {
    color: """ + NORD['nord11'] + """;
    border-color: """ + NORD['nord11'] + """;
}

/* --- Mode buttons (shuffle, repeat) --- */
.mode-btn {
    background-color: transparent;
    color: """ + NORD['nord3'] + """;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 2px 6px;
    min-width: 24px;
    min-height: 24px;
    font-family: "JetBrainsMono Nerd Font", "Symbols Nerd Font", monospace;
    font-size: 14px;
}
.mode-btn:hover {
    color: """ + NORD['nord4'] + """;
    border-color: """ + NORD['nord3'] + """;
}
.mode-btn.active {
    color: """ + NORD['nord8'] + """;
    border-color: """ + NORD['nord8'] + """;
    background-color: rgba(136, 192, 208, 0.1);
}

/* --- Volume Slider --- */
.volume-bar trough {
    background-color: """ + NORD['nord1'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 2px;
    min-height: 6px;
}
.volume-bar highlight {
    background-color: """ + NORD['nord14'] + """;
    border-radius: 2px;
    min-height: 6px;
}
.volume-bar slider {
    background-color: """ + NORD['nord6'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 50%;
    min-width: 12px;
    min-height: 12px;
    margin: -4px;
}
.volume-bar slider:hover {
    background-color: """ + NORD['nord14'] + """;
}
.volume-icon {
    color: """ + NORD['nord4'] + """;
    font-family: "JetBrainsMono Nerd Font", "Symbols Nerd Font", monospace;
    font-size: 16px;
    min-width: 24px;
    padding: 0 4px;
}
.volume-icon.muted {
    color: """ + NORD['nord11'] + """;
}

/* --- Playlist --- */
.playlist-view {
    background-color: """ + NORD['nord0'] + """;
    color: """ + NORD['nord4'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 3px;
    font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", monospace;
    font-size: 10px;
}
.playlist-view:selected {
    background-color: """ + NORD['nord10'] + """;
    color: """ + NORD['nord6'] + """;
}
.playlist-view row:hover {
    background-color: """ + NORD['nord1'] + """;
}
.playlist-view .playing-row {
    color: """ + NORD['nord8'] + """;
    font-weight: bold;
}
.playlist-header {
    background-color: """ + NORD['nord1'] + """;
    border-bottom: 1px solid """ + NORD['nord3'] + """;
    padding: 4px 8px;
}
.playlist-header label {
    color: """ + NORD['nord8'] + """;    font-family: "JetBrainsMono Nerd Font", "Symbols Nerd Font", monospace;    font-weight: bold;
    font-size: 10px;
}
.playlist-count {
    color: """ + NORD['nord3'] + """;
    font-size: 9px;
}
.playlist-duration {
    color: """ + NORD['nord3'] + """;
    font-size: 9px;
    font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", monospace;
}

/* --- Playlist Action Buttons --- */
.playlist-action-btn {
    background-color: """ + NORD['nord1'] + """;
    color: """ + NORD['nord4'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 3px;
    padding: 2px 8px;
    min-height: 22px;    font-family: "JetBrainsMono Nerd Font", "Symbols Nerd Font", monospace;    font-size: 10px;
}
.playlist-action-btn:hover {
    background-color: """ + NORD['nord2'] + """;
    color: """ + NORD['nord8'] + """;
    border-color: """ + NORD['nord8'] + """;
}

/* --- Status Bar --- */
.status-bar {
    background-color: """ + NORD['nord1'] + """;
    border-top: 1px solid """ + NORD['nord0'] + """;
    padding: 2px 8px;
    min-height: 20px;
}
.status-bar label {
    color: """ + NORD['nord3'] + """;
    font-size: 9px;
    font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", monospace;
}

/* --- Scrollbar --- */
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

/* --- Separator --- */
separator {
    background-color: """ + NORD['nord3'] + """;
    min-height: 1px;
    min-width: 1px;
}

/* --- File Chooser --- */
filechooser {
    background-color: """ + NORD['nord0'] + """;
    color: """ + NORD['nord4'] + """;
}

/* --- Tooltip --- */
tooltip {
    background-color: """ + NORD['nord1'] + """;
    color: """ + NORD['nord4'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 3px;
    padding: 4px 8px;
}

/* --- Dialog --- */
dialog .dialog-action-area button {
    background-color: """ + NORD['nord1'] + """;
    color: """ + NORD['nord4'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 3px;
    padding: 4px 12px;
}
dialog .dialog-action-area button:hover {
    background-color: """ + NORD['nord2'] + """;
    color: """ + NORD['nord8'] + """;
}

/* --- VU Meter style visualization --- */
.vu-meter {
    background-color: """ + NORD['nord0'] + """;
    border: 1px solid """ + NORD['nord3'] + """;
    border-radius: 2px;
}

/* --- Logo area --- */
.logo-area {
    color: """ + NORD['nord8'] + """;
    font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", monospace;
    font-size: 9px;
    font-weight: bold;
}
"""


def apply_theme():
    """Apply the Nord Winamp theme CSS to the current GTK screen.

    Creates a CssProvider, loads the theme CSS, and applies it to
    the default Gdk.Screen with APPLICATION priority.
    """
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(THEME_CSS.encode('utf-8'))

    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
