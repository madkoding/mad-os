"""Track open windows via Sway/Hyprland IPC to show running/urgent state."""

import json
import os
import shutil
import subprocess


def _detect_compositor():
    """Detect which Wayland compositor is running: 'sway', 'hyprland', or None."""
    # Check environment variables
    xdg = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "hyprland" in xdg:
        return "hyprland"
    if "sway" in xdg:
        return "sway"
    # Check for running processes
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"
    if os.environ.get("SWAYSOCK"):
        return "sway"
    # Check binary availability as last resort
    if shutil.which("swaymsg"):
        return "sway"
    if shutil.which("hyprctl"):
        return "hyprland"
    return None


def _query_sway_windows():
    """Query Sway IPC for all open windows. Returns list of dicts with app_id, name, urgent."""
    try:
        result = subprocess.run(
            ["swaymsg", "-t", "get_tree"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode != 0:
            return []
        tree = json.loads(result.stdout)
        return _extract_sway_nodes(tree)
    except Exception:
        return []


def _extract_sway_nodes(node):
    """Recursively extract window info from Sway's tree."""
    windows = []
    # A leaf node with an app_id or window_properties is a window
    app_id = node.get("app_id") or ""
    wp = node.get("window_properties", {})
    wm_class = wp.get("class", "")
    name = node.get("name") or ""
    urgent = node.get("urgent", False)
    pid = node.get("pid", 0)

    if (app_id or wm_class) and node.get("type") == "con" and not node.get("nodes"):
        windows.append({
            "app_id": app_id.lower(),
            "wm_class": wm_class.lower(),
            "name": name,
            "urgent": urgent,
            "pid": pid,
            "focused": node.get("focused", False),
        })

    # Recurse into child nodes
    for child in node.get("nodes", []):
        windows.extend(_extract_sway_nodes(child))
    for child in node.get("floating_nodes", []):
        windows.extend(_extract_sway_nodes(child))

    return windows


def _query_hyprland_windows():
    """Query Hyprland IPC for all open windows."""
    try:
        result = subprocess.run(
            ["hyprctl", "clients", "-j"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode != 0:
            return []
        clients = json.loads(result.stdout)
        windows = []
        for c in clients:
            windows.append({
                "app_id": (c.get("class") or "").lower(),
                "wm_class": (c.get("class") or "").lower(),
                "name": c.get("title", ""),
                "urgent": c.get("urgent", False),
                "pid": c.get("pid", 0),
                "focused": c.get("focusHistoryID", -1) == 0,
            })
        return windows
    except Exception:
        return []


def _exec_to_match_key(exec_cmd):
    """Extract the base binary name from an Exec command for matching.

    E.g. '/usr/bin/chromium --no-sandbox' -> 'chromium'
         'env VAR=val firefox' -> 'firefox'
         'python3 -m mados_equalizer' -> 'mados-equalizer' (heuristic)
    """
    if not exec_cmd:
        return ""
    parts = exec_cmd.split()
    # Skip env-style prefixes (env, KEY=val)
    i = 0
    while i < len(parts):
        if parts[i] == "env":
            i += 1
            continue
        if "=" in parts[i]:
            i += 1
            continue
        break

    if i >= len(parts):
        return ""

    binary = os.path.basename(parts[i])

    # Special case: python3 -m module_name -> convert module to app-id style
    if binary in ("python3", "python") and i + 2 <= len(parts) and parts[i + 1] == "-m":
        module = parts[i + 2] if i + 2 < len(parts) else ""
        return module.replace("_", "-")

    return binary.lower()


class WindowTracker:
    """Tracks running and urgent windows by querying the compositor."""

    def __init__(self):
        self._compositor = _detect_compositor()
        self._running = set()     # Set of match keys that are running
        self._urgent = set()      # Set of match keys that are urgent
        self._focused = set()     # Set of match keys that are focused

    @property
    def compositor(self):
        return self._compositor

    def update(self):
        """Query compositor and update running/urgent sets. Returns True if state changed."""
        if self._compositor == "sway":
            windows = _query_sway_windows()
        elif self._compositor == "hyprland":
            windows = _query_hyprland_windows()
        else:
            return False

        old_running = self._running.copy()
        old_urgent = self._urgent.copy()
        old_focused = self._focused.copy()

        self._running = set()
        self._urgent = set()
        self._focused = set()

        for w in windows:
            # Use app_id as primary match, fallback to wm_class
            key = w["app_id"] or w["wm_class"]
            if key:
                self._running.add(key)
                if w.get("urgent"):
                    self._urgent.add(key)
                if w.get("focused"):
                    self._focused.add(key)

        return (self._running != old_running
                or self._urgent != old_urgent
                or self._focused != old_focused)

    def is_running(self, exec_cmd, desktop_filename=""):
        """Check if an application appears to be running."""
        match_key = _exec_to_match_key(exec_cmd)
        if not match_key:
            return False

        # Direct match against app_id/wm_class
        if match_key in self._running:
            return True

        # Also try the desktop filename without extension as app_id
        if desktop_filename:
            base = desktop_filename.replace(".desktop", "").lower()
            if base in self._running:
                return True

        return False

    def is_urgent(self, exec_cmd, desktop_filename=""):
        """Check if an application has urgency/attention flag."""
        match_key = _exec_to_match_key(exec_cmd)
        if not match_key:
            return False

        if match_key in self._urgent:
            return True

        if desktop_filename:
            base = desktop_filename.replace(".desktop", "").lower()
            if base in self._urgent:
                return True

        return False

    def is_focused(self, exec_cmd, desktop_filename=""):
        """Check if an application is currently focused."""
        match_key = _exec_to_match_key(exec_cmd)
        if not match_key:
            return False

        if match_key in self._focused:
            return True

        if desktop_filename:
            base = desktop_filename.replace(".desktop", "").lower()
            if base in self._focused:
                return True

        return False
