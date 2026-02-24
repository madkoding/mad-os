"""Configuration constants for madOS Launcher."""

import os

# --- Nord Color Palette ---
NORD = {
    # Polar Night (dark backgrounds)
    "nord0": "#2E3440",
    "nord1": "#3B4252",
    "nord2": "#434C5E",
    "nord3": "#4C566A",
    # Snow Storm (light text)
    "nord4": "#D8DEE9",
    "nord5": "#E5E9F0",
    "nord6": "#ECEFF4",
    # Frost (accent blues)
    "nord7": "#8FBCBB",
    "nord8": "#88C0D0",
    "nord9": "#81A1C1",
    "nord10": "#5E81AC",
    # Aurora (states)
    "nord11": "#BF616A",
    "nord12": "#D08770",
    "nord13": "#EBCB8B",
    "nord14": "#A3BE8C",
    "nord15": "#B48EAD",
}

# --- Dock Dimensions ---
ICON_SIZE = 24          # Icon pixel size
TAB_WIDTH = 14          # Width of the grip tab in pixels
DOCK_WIDTH = 35         # Width of the icon area (icon + padding)
TAB_HEIGHT = 54         # Height of the grip tab
ICON_PADDING = 3        # Padding around each icon button
ICON_SPACING = 2        # Spacing between icon buttons

# --- Animation ---
ANIMATION_DURATION = 250  # Revealer transition in milliseconds

# --- Grip Visual ---
GRIP_DOT_RADIUS = 1.5     # Cairo dot radius
GRIP_DOT_SPACING = 7      # Vertical spacing between grip dot pairs
GRIP_DOT_COLS = 2         # Number of dot columns
GRIP_DOT_COL_GAP = 4      # Horizontal gap between dot columns

# --- Drag Behavior ---
DRAG_THRESHOLD = 5        # Pixels moved before a drag is recognized
MIN_MARGIN_TOP = 0        # Minimum top margin
DEFAULT_MARGIN_TOP = 200  # Default vertical position

# --- Shadow ---
SHADOW_SIZE = 8            # Shadow spread in pixels
SHADOW_OFFSET_X = 2        # Horizontal shadow offset
SHADOW_OFFSET_Y = 3        # Vertical shadow offset
SHADOW_LAYERS = 5          # Number of blur layers for shadow
SHADOW_BASE_ALPHA = 0.4    # Maximum combined shadow opacity

# --- Desktop Entry Scanning ---
DESKTOP_DIRS = [
    "/usr/share/applications",
    "/usr/local/share/applications",
    os.path.expanduser("~/.local/share/applications"),
]
EXCLUDED_DESKTOP = {
    "mados-launcher.desktop",
    "nm-connection-editor.desktop",
    "blueman-adapters.desktop",
    "blueman-manager.desktop",
    "foot.desktop",
    "foot-server.desktop",
    "footclient.desktop",
    "htop.desktop",
    "mados-equalizer.desktop",
    "vim.desktop",
}

# --- State Persistence ---
CONFIG_DIR = os.path.expanduser("~/.config/mados-launcher")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")

# --- Icon Zoom on Hover ---
ICON_ZOOM_SIZE = 32            # Target icon size on hover (pixels)
ICON_ZOOM_STEP = 2             # Pixels per animation frame
ICON_ZOOM_INTERVAL_MS = 25     # Milliseconds between animation frames

# --- Service-Dependent Filtering ---
# Desktop entry filenames to hide when avahi-daemon is not running
AVAHI_DESKTOP_FILES = {
    "avahi-discover.desktop",
    "bvnc.desktop",
    "bssh.desktop",
}

# --- Refresh ---
REFRESH_INTERVAL_SECONDS = 30  # Rescan .desktop files every N seconds
