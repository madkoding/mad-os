#!/usr/bin/env python3
"""
Tests for madOS Bluetooth and WiFi native tray app support.

Validates that native tray applications (blueman for Bluetooth,
network-manager-applet for WiFi) are properly configured in packages,
Waybar, Sway, and Hyprland configs. Also verifies that Bluetooth
packages and services remain correctly set up.

These tests verify file presence, syntax, and configuration correctness
without requiring actual hardware.
"""

import sys
import os
import unittest
import json

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")

# Add lib dir to path for imports
sys.path.insert(0, LIB_DIR)


class TestBluetoothPackages(unittest.TestCase):
    """Verify Bluetooth packages are included in the ISO package list."""

    def _read_packages(self):
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

    def test_packages_has_bluez(self):
        """packages.x86_64 should include bluez."""
        self.assertIn("bluez", self._read_packages())

    def test_packages_has_bluez_utils(self):
        """packages.x86_64 should include bluez-utils."""
        self.assertIn("bluez-utils", self._read_packages())

    def test_packages_has_blueman(self):
        """packages.x86_64 should include blueman for Bluetooth tray applet."""
        self.assertIn("blueman", self._read_packages())

    def test_packages_has_network_manager_applet(self):
        """packages.x86_64 should include network-manager-applet for WiFi tray."""
        self.assertIn("network-manager-applet", self._read_packages())

    def test_installer_config_has_bluez(self):
        """Installer config.py PACKAGES should include bluez."""
        from mados_installer.config import PACKAGES

        self.assertIn("bluez", PACKAGES)

    def test_installer_config_has_bluez_utils(self):
        """Installer config.py PACKAGES should include bluez-utils."""
        from mados_installer.config import PACKAGES

        self.assertIn("bluez-utils", PACKAGES)


class TestBluetoothService(unittest.TestCase):
    """Verify bluetooth.service is enabled in both live USB and post-install."""

    def test_live_usb_bluetooth_service_symlink(self):
        """bluetooth.service should be enabled in multi-user.target.wants."""
        service_link = os.path.join(
            AIROOTFS,
            "etc",
            "systemd",
            "system",
            "multi-user.target.wants",
            "bluetooth.service",
        )
        self.assertTrue(
            os.path.islink(service_link),
            "bluetooth.service must be enabled as a symlink for live USB",
        )

    def test_post_install_enables_bluetooth(self):
        """installation.py should enable bluetooth.service."""
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        with open(install_py) as f:
            content = f.read()
        self.assertIn("systemctl enable bluetooth", content)

    def test_bluetooth_main_conf_exists(self):
        """airootfs/etc/bluetooth/main.conf should exist."""
        main_conf = os.path.join(AIROOTFS, "etc", "bluetooth", "main.conf")
        self.assertTrue(os.path.isfile(main_conf))

    def test_bluetooth_main_conf_auto_enable(self):
        """main.conf should contain AutoEnable=true under [General]."""
        main_conf = os.path.join(AIROOTFS, "etc", "bluetooth", "main.conf")
        with open(main_conf) as f:
            content = f.read()
        self.assertIn("[General]", content)
        self.assertIn("AutoEnable=true", content)


class TestSwayTrayApplets(unittest.TestCase):
    """Verify Sway config autostarts native WiFi and Bluetooth tray applets."""

    def _read_sway_config(self):
        sway_config = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "sway", "config"
        )
        with open(sway_config) as f:
            return f.read()

    def test_sway_autostarts_nm_applet(self):
        """Sway config should autostart nm-applet."""
        content = self._read_sway_config()
        self.assertIn("nm-applet", content)

    def test_sway_autostarts_blueman_applet(self):
        """Sway config should autostart blueman-applet."""
        content = self._read_sway_config()
        self.assertIn("blueman-applet", content)

    def test_sway_no_mados_wifi_reference(self):
        """Sway config should not reference removed mados-wifi."""
        content = self._read_sway_config()
        self.assertNotIn("mados-wifi", content)

    def test_sway_no_mados_bluetooth_reference(self):
        """Sway config should not reference removed mados-bluetooth."""
        content = self._read_sway_config()
        self.assertNotIn("mados-bluetooth", content)


class TestHyprlandTrayApplets(unittest.TestCase):
    """Verify Hyprland config autostarts native WiFi and Bluetooth tray applets."""

    def _read_hyprland_config(self):
        hyprland_config = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "hypr", "hyprland.conf"
        )
        with open(hyprland_config) as f:
            return f.read()

    def test_hyprland_autostarts_nm_applet(self):
        """Hyprland config should autostart nm-applet."""
        content = self._read_hyprland_config()
        self.assertIn("nm-applet", content)

    def test_hyprland_autostarts_blueman_applet(self):
        """Hyprland config should autostart blueman-applet."""
        content = self._read_hyprland_config()
        self.assertIn("blueman-applet", content)

    def test_hyprland_no_mados_wifi_reference(self):
        """Hyprland config should not reference removed mados-wifi."""
        content = self._read_hyprland_config()
        self.assertNotIn("mados-wifi", content)

    def test_hyprland_no_mados_bluetooth_reference(self):
        """Hyprland config should not reference removed mados-bluetooth."""
        content = self._read_hyprland_config()
        self.assertNotIn("mados-bluetooth", content)


class TestWaybarConfig(unittest.TestCase):
    """Verify Waybar configuration uses native applets and tray."""

    def _read_waybar_config(self):
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            return json.load(f)

    def test_waybar_config_valid_json(self):
        """Waybar config should be valid JSON."""
        config = self._read_waybar_config()
        self.assertIsInstance(config, dict)

    def test_waybar_has_tray_module(self):
        """Waybar config should include tray module for nm-applet/blueman."""
        config = self._read_waybar_config()
        right_modules = config.get("modules-right", [])
        self.assertIn("tray", right_modules)

    def test_waybar_network_on_click_uses_nm_connection_editor(self):
        """Waybar network module on-click should use nm-connection-editor."""
        config = self._read_waybar_config()
        network_config = config.get("network", {})
        self.assertEqual(
            network_config.get("on-click"),
            "nm-connection-editor",
        )

    def test_waybar_no_custom_bluetooth_module(self):
        """Waybar config should not have custom/bluetooth module."""
        config = self._read_waybar_config()
        right_modules = config.get("modules-right", [])
        self.assertNotIn("custom/bluetooth", right_modules)

    def test_waybar_no_mados_wifi_reference(self):
        """Waybar config should not reference mados-wifi."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            content = f.read()
        self.assertNotIn("mados-wifi", content)

    def test_waybar_no_mados_bluetooth_reference(self):
        """Waybar config should not reference mados-bluetooth."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            content = f.read()
        self.assertNotIn("mados-bluetooth", content)


class TestRemovedFiles(unittest.TestCase):
    """Verify mados-wifi and mados-bluetooth files have been removed."""

    def test_no_mados_wifi_launcher(self):
        """mados-wifi launcher should not exist."""
        self.assertFalse(
            os.path.exists(os.path.join(BIN_DIR, "mados-wifi")),
            "mados-wifi launcher should have been removed",
        )

    def test_no_mados_bluetooth_launcher(self):
        """mados-bluetooth launcher should not exist."""
        self.assertFalse(
            os.path.exists(os.path.join(BIN_DIR, "mados-bluetooth")),
            "mados-bluetooth launcher should have been removed",
        )

    def test_no_mados_wifi_lib(self):
        """mados_wifi library should not exist."""
        self.assertFalse(
            os.path.exists(os.path.join(LIB_DIR, "mados_wifi")),
            "mados_wifi library should have been removed",
        )

    def test_no_mados_bluetooth_lib(self):
        """mados_bluetooth library should not exist."""
        self.assertFalse(
            os.path.exists(os.path.join(LIB_DIR, "mados_bluetooth")),
            "mados_bluetooth library should have been removed",
        )

    def test_no_mados_wifi_desktop(self):
        """mados-wifi.desktop should not exist."""
        self.assertFalse(
            os.path.exists(
                os.path.join(AIROOTFS, "usr", "share", "applications", "mados-wifi.desktop")
            ),
        )

    def test_no_mados_bluetooth_desktop(self):
        """mados-bluetooth.desktop should not exist."""
        self.assertFalse(
            os.path.exists(
                os.path.join(AIROOTFS, "usr", "share", "applications", "mados-bluetooth.desktop")
            ),
        )


class TestProfiledefPermissions(unittest.TestCase):
    """Verify profiledef.sh no longer includes removed app permissions."""

    def _read_profiledef(self):
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            return f.read()

    def test_profiledef_no_mados_wifi(self):
        """profiledef.sh should not have mados-wifi permission."""
        self.assertNotIn("mados-wifi", self._read_profiledef())

    def test_profiledef_no_mados_wifi_lib(self):
        """profiledef.sh should not have mados_wifi lib permission."""
        self.assertNotIn("mados_wifi", self._read_profiledef())

    def test_profiledef_no_mados_bluetooth(self):
        """profiledef.sh should not have mados-bluetooth permission."""
        self.assertNotIn("mados-bluetooth", self._read_profiledef())

    def test_profiledef_no_mados_bluetooth_lib(self):
        """profiledef.sh should not have mados_bluetooth lib permission."""
        self.assertNotIn("mados_bluetooth", self._read_profiledef())


class TestUdevWirelessRules(unittest.TestCase):
    """Verify udev rules for wireless hardware are properly configured."""

    def test_udev_rules_file_exists(self):
        """90-mados-wireless.rules should exist."""
        rules_path = os.path.join(
            AIROOTFS, "etc", "udev", "rules.d", "90-mados-wireless.rules"
        )
        self.assertTrue(os.path.isfile(rules_path))

    def test_udev_rules_has_rfkill_unblock_wifi(self):
        """udev rules should unblock WiFi via rfkill."""
        rules_path = os.path.join(
            AIROOTFS, "etc", "udev", "rules.d", "90-mados-wireless.rules"
        )
        with open(rules_path) as f:
            content = f.read()
        self.assertIn("rfkill unblock wifi", content)

    def test_udev_rules_has_rfkill_unblock_bluetooth(self):
        """udev rules should unblock Bluetooth via rfkill."""
        rules_path = os.path.join(
            AIROOTFS, "etc", "udev", "rules.d", "90-mados-wireless.rules"
        )
        with open(rules_path) as f:
            content = f.read()
        self.assertIn("rfkill unblock bluetooth", content)


class TestModprobeMediaTekConfig(unittest.TestCase):
    """Verify modprobe configuration for MediaTek MT7921 combo adapter."""

    def test_modprobe_mt7921_config_exists(self):
        """mt7921.conf modprobe config should exist."""
        conf_path = os.path.join(AIROOTFS, "etc", "modprobe.d", "mt7921.conf")
        self.assertTrue(os.path.isfile(conf_path))

    def test_modprobe_has_btusb_config(self):
        """mt7921.conf should configure btusb module."""
        conf_path = os.path.join(AIROOTFS, "etc", "modprobe.d", "mt7921.conf")
        with open(conf_path) as f:
            content = f.read()
        self.assertIn("btusb", content)

    def test_modprobe_has_mt7921e_config(self):
        """mt7921.conf should configure mt7921e module."""
        conf_path = os.path.join(AIROOTFS, "etc", "modprobe.d", "mt7921.conf")
        with open(conf_path) as f:
            content = f.read()
        self.assertIn("mt7921e", content)


if __name__ == "__main__":
    unittest.main()
