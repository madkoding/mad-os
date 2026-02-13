#!/usr/bin/env python3
"""
Tests for madOS Plymouth boot splash theme.

Validates that the Plymouth theme script has correct structure,
required callbacks, and the shader-inspired tunnel animation elements.
"""

import os
import re
import unittest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
THEME_DIR = os.path.join(AIROOTFS, "usr", "share", "plymouth", "themes", "mados")


class TestPlymouthThemeFiles(unittest.TestCase):
    """Verify Plymouth theme files exist and have correct structure."""

    def test_theme_directory_exists(self):
        """Plymouth theme directory must exist."""
        self.assertTrue(os.path.isdir(THEME_DIR))

    def test_plymouth_config_exists(self):
        """mados.plymouth config file must exist."""
        self.assertTrue(os.path.isfile(os.path.join(THEME_DIR, "mados.plymouth")))

    def test_script_file_exists(self):
        """mados.script must exist."""
        self.assertTrue(os.path.isfile(os.path.join(THEME_DIR, "mados.script")))

    def test_logo_image_exists(self):
        """logo.png must exist in theme directory."""
        self.assertTrue(os.path.isfile(os.path.join(THEME_DIR, "logo.png")))

    def test_dot_image_exists(self):
        """dot.png must exist in theme directory."""
        self.assertTrue(os.path.isfile(os.path.join(THEME_DIR, "dot.png")))


class TestPlymouthConfig(unittest.TestCase):
    """Verify mados.plymouth configuration is correct."""

    def setUp(self):
        with open(os.path.join(THEME_DIR, "mados.plymouth")) as f:
            self.content = f.read()

    def test_theme_name(self):
        """Theme name must be 'madOS'."""
        self.assertIn("Name=madOS", self.content)

    def test_module_is_script(self):
        """Theme must use the 'script' module."""
        self.assertIn("ModuleName=script", self.content)

    def test_image_dir_path(self):
        """ImageDir must point to correct path."""
        self.assertIn("ImageDir=/usr/share/plymouth/themes/mados", self.content)

    def test_script_file_path(self):
        """ScriptFile must point to correct path."""
        self.assertIn("ScriptFile=/usr/share/plymouth/themes/mados/mados.script", self.content)


class TestPlymouthScript(unittest.TestCase):
    """Verify Plymouth script has required structure and callbacks."""

    def setUp(self):
        with open(os.path.join(THEME_DIR, "mados.script")) as f:
            self.content = f.read()

    def test_has_background_colors(self):
        """Script must set background colors."""
        self.assertIn("SetBackgroundTopColor", self.content)
        self.assertIn("SetBackgroundBottomColor", self.content)

    def test_has_logo_setup(self):
        """Script must load and position logo image."""
        self.assertIn('Image("logo.png")', self.content)
        self.assertIn("logo.sprite", self.content)

    def test_has_dot_image(self):
        """Script must load dot.png for spinner and tunnel effects."""
        self.assertIn('Image("dot.png")', self.content)

    def test_has_refresh_callback(self):
        """Script must set a refresh callback for animation."""
        self.assertIn("Plymouth.SetRefreshFunction", self.content)
        self.assertIn("fun refresh_callback", self.content)

    def test_has_quit_callback(self):
        """Script must set a quit callback."""
        self.assertIn("Plymouth.SetQuitFunction", self.content)
        self.assertIn("fun quit_callback", self.content)

    def test_has_message_callbacks(self):
        """Script must set message display callbacks."""
        self.assertIn("Plymouth.SetDisplayNormalFunction", self.content)
        self.assertIn("Plymouth.SetMessageFunction", self.content)

    def test_has_password_callback(self):
        """Script must set password prompt callback for encrypted disks."""
        self.assertIn("Plymouth.SetDisplayPasswordFunction", self.content)
        self.assertIn("fun display_password_callback", self.content)

    def test_has_boot_progress_callback(self):
        """Script must set boot progress callback."""
        self.assertIn("Plymouth.SetBootProgressFunction", self.content)

    def test_has_spinner_animation(self):
        """Script must have spinner dot animation."""
        self.assertIn("NUM_DOTS", self.content)
        self.assertIn("SPINNER_RADIUS", self.content)
        self.assertIn("active_dot", self.content)

    def test_has_tunnel_rings(self):
        """Script must have tunnel ring elements (shader-inspired effect)."""
        self.assertIn("NUM_RINGS", self.content)
        self.assertIn("ring[r]", self.content)

    def test_has_depth_attenuation(self):
        """Script must implement depth-based opacity (shader depth effect)."""
        self.assertIn("depth_factor", self.content)

    def test_has_animation_frame_counter(self):
        """Script must have frame counter for animation timing."""
        self.assertIn("frame", self.content)
        self.assertIn("frame++", self.content)

    def test_braces_balanced(self):
        """Script braces must be balanced."""
        opens = self.content.count('{')
        closes = self.content.count('}')
        self.assertEqual(opens, closes,
                         f"Unbalanced braces: {opens} opens vs {closes} closes")

    def test_parentheses_balanced(self):
        """Script parentheses must be balanced."""
        opens = self.content.count('(')
        closes = self.content.count(')')
        self.assertEqual(opens, closes,
                         f"Unbalanced parentheses: {opens} opens vs {closes} closes")


class TestPlymouthInstallerSync(unittest.TestCase):
    """Verify the installer embeds a Plymouth script consistent with the theme."""

    def setUp(self):
        installer_path = os.path.join(
            AIROOTFS, "usr", "local", "lib", "mados_installer", "pages", "installation.py"
        )
        with open(installer_path) as f:
            self.installer_content = f.read()
        with open(os.path.join(THEME_DIR, "mados.script")) as f:
            self.theme_content = f.read()

    def test_installer_has_plymouth_setup(self):
        """Installer must set up Plymouth theme."""
        self.assertIn("plymouth-set-default-theme mados", self.installer_content)

    def test_installer_has_tunnel_rings(self):
        """Installer's embedded script must include tunnel ring animation."""
        self.assertIn("NUM_RINGS", self.installer_content)
        self.assertIn("ring[r]", self.installer_content)

    def test_installer_has_depth_effect(self):
        """Installer's embedded script must include depth attenuation."""
        self.assertIn("depth_factor", self.installer_content)

    def test_installer_copies_assets(self):
        """Installer must copy logo.png and dot.png to installed system."""
        self.assertIn("logo.png", self.installer_content)
        self.assertIn("dot.png", self.installer_content)

    def test_installer_theme_description_matches(self):
        """Installer and theme file must have matching description."""
        with open(os.path.join(THEME_DIR, "mados.plymouth")) as f:
            theme_config = f.read()
        # Extract description from theme config
        desc_match = re.search(r'Description=(.+)', theme_config)
        self.assertIsNotNone(desc_match)
        theme_desc = desc_match.group(1).strip()
        # Installer should have the same description
        self.assertIn(theme_desc, self.installer_content)


if __name__ == "__main__":
    unittest.main()
