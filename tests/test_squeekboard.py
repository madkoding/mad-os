#!/usr/bin/env python3
"""
Tests for squeekboard (on-screen virtual keyboard) integration in madOS.

Validates:
  - squeekboard is listed in packages.x86_64
  - mados-squeekboard script exists with correct bash syntax
  - Script properly detects physical keyboards
  - Script has auto/start/stop/toggle/status commands
  - profiledef.sh has correct permissions
  - Both Sway and Hyprland configs launch the monitor
  - Both Sway and Hyprland have window rules for squeekboard
  - Both Sway and Hyprland have a toggle keybinding
"""

import os
import subprocess
import unittest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SWAY_CONFIG = os.path.join(AIROOTFS, "etc", "skel", ".config", "sway", "config")
HYPRLAND_CONFIG = os.path.join(
    AIROOTFS, "etc", "skel", ".config", "hypr", "hyprland.conf"
)
PROFILEDEF = os.path.join(REPO_DIR, "profiledef.sh")
PACKAGES = os.path.join(REPO_DIR, "packages.x86_64")
SQUEEKBOARD_SCRIPT = os.path.join(BIN_DIR, "mados-squeekboard")


class TestSqueekboardPackage(unittest.TestCase):
    """Validate squeekboard is included in the ISO packages."""

    def test_squeekboard_in_packages(self):
        with open(PACKAGES) as f:
            lines = [line.strip() for line in f if not line.startswith("#")]
        self.assertIn("squeekboard", lines, "squeekboard must be in packages.x86_64")


class TestSqueekboardScript(unittest.TestCase):
    """Validate the mados-squeekboard helper script."""

    def test_script_exists(self):
        self.assertTrue(
            os.path.isfile(SQUEEKBOARD_SCRIPT),
            "mados-squeekboard script should exist",
        )

    def test_script_has_shebang(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            first_line = f.readline()
        self.assertTrue(
            first_line.startswith("#!/"), "Script should start with a shebang line"
        )

    def test_script_valid_bash_syntax(self):
        result = subprocess.run(
            ["bash", "-n", SQUEEKBOARD_SCRIPT], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")

    def test_script_has_auto_command(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn("auto|monitor", content, "Script must support 'auto' command")

    def test_script_has_start_command(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn("start_squeekboard", content)

    def test_script_has_stop_command(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn("stop_squeekboard", content)

    def test_script_has_toggle_command(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn("toggle_squeekboard", content)
        self.assertIn("toggle)", content, "Script must handle 'toggle' argument")

    def test_script_has_status_command(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn("show_status", content)
        self.assertIn("status)", content, "Script must handle 'status' argument")

    def test_script_detects_physical_keyboard(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "has_physical_keyboard", content,
            "Script must have keyboard detection function",
        )

    def test_script_checks_input_devices(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "/sys/class/input", content,
            "Script should check /sys/class/input for keyboard devices",
        )

    def test_script_filters_non_keyboard_devices(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        for device in ["Power Button", "Sleep Button", "gamepad"]:
            self.assertIn(
                device, content,
                f"Script should filter out '{device}' from keyboard detection",
            )

    def test_script_monitors_udev_events(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "udevadm monitor", content,
            "Script should use udevadm monitor for hotplug detection",
        )

    def test_script_uses_logger(self):
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn("logger", content, "Script should log via logger")

    def test_script_skips_virtual_keyboard_in_detection(self):
        """Ensure squeekboard itself is not counted as a physical keyboard."""
        with open(SQUEEKBOARD_SCRIPT) as f:
            content = f.read()
        self.assertIn("squeekboard", content.lower())
        # The filter section should mention squeekboard/Virtual
        self.assertIn(
            "Virtual", content,
            "Script should skip virtual keyboard devices in detection",
        )


class TestSqueekboardProfiledef(unittest.TestCase):
    """Validate profiledef.sh permissions for the script."""

    def test_profiledef_has_permissions(self):
        with open(PROFILEDEF) as f:
            content = f.read()
        self.assertIn(
            "mados-squeekboard", content,
            "profiledef.sh must include mados-squeekboard permissions",
        )

    def test_profiledef_permissions_are_755(self):
        with open(PROFILEDEF) as f:
            content = f.read()
        self.assertIn(
            '["/usr/local/bin/mados-squeekboard"]="0:0:755"', content,
            "mados-squeekboard must have 0:0:755 permissions",
        )


class TestSqueekboardSwayIntegration(unittest.TestCase):
    """Validate squeekboard integration in Sway config."""

    def test_sway_launches_squeekboard_monitor(self):
        with open(SWAY_CONFIG) as f:
            content = f.read()
        self.assertIn(
            "mados-squeekboard", content,
            "Sway config must launch mados-squeekboard",
        )

    def test_sway_launches_in_auto_mode(self):
        with open(SWAY_CONFIG) as f:
            content = f.read()
        self.assertIn(
            "mados-squeekboard auto", content,
            "Sway should launch squeekboard in auto-detect mode",
        )

    def test_sway_has_window_rule(self):
        with open(SWAY_CONFIG) as f:
            content = f.read()
        self.assertIn(
            "sm.puri.Squeekboard", content,
            "Sway should have window rules for squeekboard app_id",
        )

    def test_sway_has_toggle_keybinding(self):
        with open(SWAY_CONFIG) as f:
            content = f.read()
        self.assertIn(
            "mados-squeekboard toggle", content,
            "Sway should have a keybinding to toggle squeekboard",
        )


class TestSqueekboardHyprlandIntegration(unittest.TestCase):
    """Validate squeekboard integration in Hyprland config."""

    def test_hyprland_launches_squeekboard_monitor(self):
        with open(HYPRLAND_CONFIG) as f:
            content = f.read()
        self.assertIn(
            "mados-squeekboard", content,
            "Hyprland config must launch mados-squeekboard",
        )

    def test_hyprland_launches_in_auto_mode(self):
        with open(HYPRLAND_CONFIG) as f:
            content = f.read()
        self.assertIn(
            "mados-squeekboard auto", content,
            "Hyprland should launch squeekboard in auto-detect mode",
        )

    def test_hyprland_has_window_rule(self):
        with open(HYPRLAND_CONFIG) as f:
            content = f.read()
        self.assertIn(
            "sm.puri.Squeekboard", content,
            "Hyprland should have window rules for squeekboard class",
        )

    def test_hyprland_has_toggle_keybinding(self):
        with open(HYPRLAND_CONFIG) as f:
            content = f.read()
        self.assertIn(
            "mados-squeekboard toggle", content,
            "Hyprland should have a keybinding to toggle squeekboard",
        )


if __name__ == "__main__":
    unittest.main()
