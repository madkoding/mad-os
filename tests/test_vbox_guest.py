#!/usr/bin/env python3
"""
Tests for VirtualBox Guest Additions integration in madOS.

Validates that the mados-vbox-guest script exists, has correct syntax,
and is properly integrated into both Sway and Hyprland compositor configs.
"""

import os
import subprocess
import unittest

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SWAY_CONFIG = os.path.join(AIROOTFS, "etc", "skel", ".config", "sway", "config")
HYPRLAND_CONFIG = os.path.join(AIROOTFS, "etc", "skel", ".config", "hypr", "hyprland.conf")
PROFILEDEF = os.path.join(REPO_DIR, "profiledef.sh")
PACKAGES = os.path.join(REPO_DIR, "packages.x86_64")
VBOX_SCRIPT = os.path.join(BIN_DIR, "mados-vbox-guest")


class TestVBoxGuestScript(unittest.TestCase):
    """Validate the mados-vbox-guest helper script."""

    def test_script_exists(self):
        self.assertTrue(os.path.isfile(VBOX_SCRIPT), "mados-vbox-guest script should exist")

    def test_script_has_shebang(self):
        with open(VBOX_SCRIPT) as f:
            first_line = f.readline()
        self.assertTrue(first_line.startswith("#!/"), "Script should start with a shebang line")

    def test_script_valid_bash_syntax(self):
        result = subprocess.run(["bash", "-n", VBOX_SCRIPT], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")

    def test_script_detects_virtualbox(self):
        with open(VBOX_SCRIPT) as f:
            content = f.read()
        self.assertIn("systemd-detect-virt", content)
        self.assertIn("oracle", content)

    def test_script_starts_vmsvga(self):
        with open(VBOX_SCRIPT) as f:
            content = f.read()
        self.assertIn("VBoxClient --vmsvga", content)

    def test_script_starts_clipboard(self):
        with open(VBOX_SCRIPT) as f:
            content = f.read()
        self.assertIn("VBoxClient --clipboard", content)

    def test_script_starts_draganddrop(self):
        with open(VBOX_SCRIPT) as f:
            content = f.read()
        self.assertIn("VBoxClient --draganddrop", content)

    def test_script_starts_seamless(self):
        with open(VBOX_SCRIPT) as f:
            content = f.read()
        self.assertIn("VBoxClient --seamless", content)

    def test_script_exits_early_if_not_vm(self):
        with open(VBOX_SCRIPT) as f:
            content = f.read()
        self.assertIn("exit 0", content)


class TestVBoxGuestIntegration(unittest.TestCase):
    """Validate VirtualBox guest additions integration in configs."""

    def test_sway_config_launches_vbox_guest(self):
        with open(SWAY_CONFIG) as f:
            content = f.read()
        self.assertIn("mados-vbox-guest", content)

    def test_hyprland_config_launches_vbox_guest(self):
        with open(HYPRLAND_CONFIG) as f:
            content = f.read()
        self.assertIn("mados-vbox-guest", content)

    def test_profiledef_has_permissions(self):
        with open(PROFILEDEF) as f:
            content = f.read()
        self.assertIn("mados-vbox-guest", content)

    def test_packages_include_virtualbox_guest_utils(self):
        with open(PACKAGES) as f:
            content = f.read()
        self.assertIn("virtualbox-guest-utils", content)

    def test_vboxservice_enabled(self):
        link_path = os.path.join(
            AIROOTFS, "etc", "systemd", "system",
            "multi-user.target.wants", "vboxservice.service",
        )
        self.assertTrue(os.path.islink(link_path) or os.path.exists(link_path))


if __name__ == "__main__":
    unittest.main()
