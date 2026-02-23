#!/usr/bin/env python3
"""
Tests for madOS installer autostart functionality.

Validates that the installer autostart script, Sway config, and Hyprland config
are properly configured to launch the GTK installer in live USB environments.

The autostart helper script checks for archiso environment and Ventoy boot
conditions before launching the installer.
"""

import os
import re
import subprocess
import unittest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SWAY_CONFIG_DIR = os.path.join(AIROOTFS, "etc", "sway", "config.d")
HYPRLAND_CONFIG = os.path.join(AIROOTFS, "etc", "skel", ".config", "hypr", "hyprland.conf")


# ═══════════════════════════════════════════════════════════════════════════
# mados-installer-autostart script tests
# ═══════════════════════════════════════════════════════════════════════════
class TestInstallerAutostartScript(unittest.TestCase):
    """Verify mados-installer-autostart script is properly configured."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "mados-installer-autostart")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_script_exists(self):
        """mados-installer-autostart must exist."""
        self.assertTrue(os.path.isfile(self.script_path))

    def test_valid_bash_syntax(self):
        """Script must have valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error in mados-installer-autostart: {result.stderr}",
        )

    def test_has_bash_shebang(self):
        """Script must start with a bash shebang."""
        with open(self.script_path) as f:
            first_line = f.readline().strip()
        self.assertTrue(
            first_line.startswith("#!"),
            "mados-installer-autostart must start with #!",
        )
        self.assertIn(
            "bash", first_line,
            "mados-installer-autostart must use bash shebang",
        )

    def test_contains_is_ventoy_boot_function(self):
        """Script must contain is_ventoy_boot function."""
        self.assertIn(
            "is_ventoy_boot()", self.content,
            "Script must define is_ventoy_boot() function",
        )
        # Verify the function checks /proc/cmdline for ventoy
        self.assertIn(
            "/proc/cmdline", self.content,
            "is_ventoy_boot must check /proc/cmdline",
        )
        self.assertIn(
            "ventoy", self.content,
            "is_ventoy_boot must search for ventoy string",
        )

    def test_uses_preserve_env_with_sudo(self):
        """Script must use --preserve-env with sudo, NOT inline VAR=value syntax."""
        # Must have --preserve-env
        self.assertIn(
            "--preserve-env", self.content,
            "Script must use sudo --preserve-env to pass environment variables",
        )
        
        # Should NOT use inline environment variable syntax before sudo
        # Bad: sudo VAR=value command
        # Good: sudo --preserve-env=VAR command
        sudo_lines = [line for line in self.content.splitlines() if "sudo" in line]
        for line in sudo_lines:
            # Skip comment lines
            if line.strip().startswith("#"):
                continue
            # Check that we don't have VAR=value immediately after sudo (before --preserve-env)
            # Pattern: sudo followed by WORD= (but not if --preserve-env comes first)
            if re.search(r'\bsudo\s+(?!--preserve-env)\w+=', line):
                self.fail(
                    f"Script must NOT use inline environment variables with sudo.\n"
                    f"Bad line: {line.strip()}\n"
                    f"Use --preserve-env instead."
                )

    def test_exports_gdk_backend_wayland(self):
        """Script must export GDK_BACKEND=wayland."""
        self.assertIn(
            "export GDK_BACKEND=wayland", self.content,
            "Script must export GDK_BACKEND=wayland for GTK Wayland support",
        )

    def test_checks_run_archiso_directory(self):
        """Script must check for /run/archiso directory."""
        self.assertIn(
            "/run/archiso", self.content,
            "Script must check for /run/archiso to detect live environment",
        )
        # Verify it's used in a conditional check
        self.assertRegex(
            self.content,
            r'if\s+\[\s+.*\s*/run/archiso',
            "Script must use /run/archiso in a conditional check",
        )

    def test_checks_install_mados_exists(self):
        """Script must check /usr/local/bin/install-mados exists before running."""
        self.assertIn(
            "/usr/local/bin/install-mados", self.content,
            "Script must reference /usr/local/bin/install-mados",
        )
        # Verify it checks executability with -x
        self.assertRegex(
            self.content,
            r'\[\s+-x\s+/usr/local/bin/install-mados\s+\]',
            "Script must check if /usr/local/bin/install-mados is executable",
        )

    def test_has_permissions_in_profiledef(self):
        """Script must have 0:0:755 permissions in profiledef.sh."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        
        self.assertIn(
            "mados-installer-autostart", content,
            "profiledef.sh must include mados-installer-autostart",
        )
        
        pattern = re.compile(
            r'\["/usr/local/bin/mados-installer-autostart"\]="0:0:755"'
        )
        self.assertRegex(
            content, pattern,
            "mados-installer-autostart must have 0:0:755 permissions in profiledef.sh",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Sway config tests
# ═══════════════════════════════════════════════════════════════════════════
class TestSwayInstallerAutostart(unittest.TestCase):
    """Verify Sway config for installer autostart is properly configured."""

    def setUp(self):
        self.config_path = os.path.join(SWAY_CONFIG_DIR, "50-installer-autostart.conf")
        with open(self.config_path) as f:
            self.content = f.read()

    def test_config_file_exists(self):
        """50-installer-autostart.conf must exist in Sway config.d."""
        self.assertTrue(os.path.isfile(self.config_path))

    def test_references_mados_installer_autostart(self):
        """Config must exec mados-installer-autostart."""
        self.assertIn(
            "mados-installer-autostart", self.content,
            "Sway config must exec mados-installer-autostart",
        )
        self.assertRegex(
            self.content,
            r'exec\s+/usr/local/bin/mados-installer-autostart',
            "Sway config must exec /usr/local/bin/mados-installer-autostart",
        )

    def test_has_window_rules_for_title(self):
        """Config must have window rules matching 'madOS Installer' title."""
        self.assertIn(
            'title="madOS Installer"', self.content,
            "Sway config must match installer by title",
        )

    def test_has_floating_enable_rule(self):
        """Config must have floating enable rule for installer."""
        # Look for a line with both title="madOS Installer" and floating enable
        lines = self.content.splitlines()
        has_floating_rule = any(
            'title="madOS Installer"' in line and "floating enable" in line
            for line in lines
        )
        self.assertTrue(
            has_floating_rule,
            "Sway config must have 'floating enable' rule for madOS Installer",
        )

    def test_has_resize_set_rule(self):
        """Config must have resize set rule for installer."""
        lines = self.content.splitlines()
        has_resize_rule = any(
            'title="madOS Installer"' in line and "resize set" in line
            for line in lines
        )
        self.assertTrue(
            has_resize_rule,
            "Sway config must have 'resize set' rule for madOS Installer",
        )

    def test_has_move_position_center_rule(self):
        """Config must have move position center rule for installer."""
        lines = self.content.splitlines()
        has_center_rule = any(
            'title="madOS Installer"' in line and "move position center" in line
            for line in lines
        )
        self.assertTrue(
            has_center_rule,
            "Sway config must have 'move position center' rule for madOS Installer",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Hyprland config tests
# ═══════════════════════════════════════════════════════════════════════════
class TestHyprlandInstallerAutostart(unittest.TestCase):
    """Verify Hyprland config for installer autostart is properly configured."""

    def setUp(self):
        with open(HYPRLAND_CONFIG) as f:
            self.content = f.read()

    def test_config_file_exists(self):
        """Hyprland config must exist."""
        self.assertTrue(os.path.isfile(HYPRLAND_CONFIG))

    def test_references_mados_installer_autostart_in_exec_once(self):
        """Config must exec-once mados-installer-autostart."""
        self.assertIn(
            "mados-installer-autostart", self.content,
            "Hyprland config must reference mados-installer-autostart",
        )
        self.assertRegex(
            self.content,
            r'exec-once\s*=\s*/usr/local/bin/mados-installer-autostart',
            "Hyprland config must exec-once /usr/local/bin/mados-installer-autostart",
        )

    def test_has_window_rules_matching_title(self):
        """Config must have window rules matching 'madOS Installer' title."""
        self.assertIn(
            "madOS Installer", self.content,
            "Hyprland config must reference madOS Installer window",
        )
        
        # Check for window rules with title matching (comma separates rule from matcher)
        self.assertRegex(
            self.content,
            r'windowrule\s*=.*,\s*match:title\s*\^\(madOS Installer\)',
            "Hyprland config must have windowrule matching madOS Installer title",
        )

    def test_has_floating_window_rule(self):
        """Config must have floating window rule for installer."""
        # Look for windowrule with float and madOS Installer
        lines = self.content.splitlines()
        has_float_rule = any(
            "windowrule" in line and "float" in line and "madOS Installer" in line
            for line in lines
        )
        self.assertTrue(
            has_float_rule,
            "Hyprland config must have floating window rule for madOS Installer",
        )

    def test_has_size_window_rule(self):
        """Config must have size window rule for installer."""
        lines = self.content.splitlines()
        has_size_rule = any(
            "windowrule" in line and "size" in line and "madOS Installer" in line
            for line in lines
        )
        self.assertTrue(
            has_size_rule,
            "Hyprland config must have size window rule for madOS Installer",
        )

    def test_has_center_window_rule(self):
        """Config must have center window rule for installer."""
        lines = self.content.splitlines()
        has_center_rule = any(
            "windowrule" in line and "center" in line and "madOS Installer" in line
            for line in lines
        )
        self.assertTrue(
            has_center_rule,
            "Hyprland config must have center window rule for madOS Installer",
        )


if __name__ == "__main__":
    unittest.main()
