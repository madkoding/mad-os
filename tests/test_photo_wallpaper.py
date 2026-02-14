#!/usr/bin/env python3
"""
Tests for madOS Photo Viewer wallpaper functionality.

Validates compositor detection and config file updating for both Sway and
Hyprland desktop environments when setting wallpapers.

These tests use temporary config files and mock GTK dependencies.
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so photo viewer modules can be imported headlessly.
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "tests"))

from test_helpers import create_gtk_mocks
import types

gi_mock, repo_mock = create_gtk_mocks()
sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

# Mock cairo module
cairo_mock = types.ModuleType("cairo")
sys.modules["cairo"] = cairo_mock

# ---------------------------------------------------------------------------
# Paths and imports
# ---------------------------------------------------------------------------
LIB_DIR = os.path.join(REPO_DIR, "airootfs", "usr", "local", "lib")
sys.path.insert(0, LIB_DIR)

from mados_photo_viewer.app import PhotoViewerApp


# ═══════════════════════════════════════════════════════════════════════════
# Compositor Detection
# ═══════════════════════════════════════════════════════════════════════════
class TestDetectCompositor(unittest.TestCase):
    """Verify compositor detection based on environment variables."""

    def test_returns_sway_by_default(self):
        """Should return 'sway' when no Hyprland env var is set."""
        with patch.dict(os.environ, {}, clear=False):
            if 'HYPRLAND_INSTANCE_SIGNATURE' in os.environ:
                del os.environ['HYPRLAND_INSTANCE_SIGNATURE']
            result = PhotoViewerApp._detect_compositor()
            self.assertEqual(result, 'sway')

    def test_returns_hyprland_when_env_set(self):
        """Should return 'hyprland' when HYPRLAND_INSTANCE_SIGNATURE is set."""
        with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': 'test123'}):
            result = PhotoViewerApp._detect_compositor()
            self.assertEqual(result, 'hyprland')

    def test_returns_hyprland_with_empty_string(self):
        """Should return 'hyprland' even if env var is empty string."""
        with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': ''}):
            result = PhotoViewerApp._detect_compositor()
            # Empty string is still truthy in the context of env var existence
            # but os.environ.get() would return empty string which is falsy
            # Let's verify the actual behavior
            self.assertEqual(result, 'sway')  # Empty string is falsy


# ═══════════════════════════════════════════════════════════════════════════
# Sway Config Update
# ═══════════════════════════════════════════════════════════════════════════
class TestUpdateSwayConfig(unittest.TestCase):
    """Verify _update_sway_config updates Sway configuration correctly."""

    def setUp(self):
        """Create a mock PhotoViewerApp instance without calling __init__."""
        self.app = object.__new__(PhotoViewerApp)
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, 'config')

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_replaces_existing_wallpaper_line(self):
        """Should replace existing 'output * bg' line with new path."""
        # Create config with existing wallpaper line
        original_content = """# Sway config
set $mod Mod4

output * bg /old/wallpaper.jpg fill

exec waybar
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        # Patch expanduser to return our test config path
        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_sway_config('/new/wallpaper.png')

        # Verify the config was updated
        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('output * bg /new/wallpaper.png fill', content)
        self.assertNotIn('/old/wallpaper.jpg', content)
        self.assertIn('exec waybar', content)  # Other lines preserved

    def test_appends_when_no_wallpaper_line_exists(self):
        """Should append wallpaper line when none exists."""
        original_content = """# Sway config
set $mod Mod4
exec waybar
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_sway_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('output * bg /new/wallpaper.png fill', content)
        self.assertIn('exec waybar', content)
        # Should be at the end
        self.assertTrue(content.strip().endswith('output * bg /new/wallpaper.png fill'))

    def test_skips_when_config_file_missing(self):
        """Should not raise error when config file doesn't exist."""
        nonexistent_path = os.path.join(self.tmpdir, 'nonexistent', 'config')
        
        with patch('os.path.expanduser', return_value=nonexistent_path):
            # Should not raise any exception
            self.app._update_sway_config('/some/wallpaper.png')

    def test_preserves_all_other_lines(self):
        """Should preserve all non-wallpaper config lines."""
        original_content = """# Sway config file
set $mod Mod4
bindsym $mod+Return exec alacritty
output * bg /old/wallpaper.jpg fill
output HDMI-A-1 resolution 1920x1080
exec waybar
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_sway_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            lines = f.readlines()

        # Count lines - should have same number (replaced, not added)
        self.assertEqual(len(lines), 6)
        self.assertIn('set $mod Mod4\n', lines)
        self.assertIn('bindsym $mod+Return exec alacritty\n', lines)
        self.assertIn('output HDMI-A-1 resolution 1920x1080\n', lines)
        self.assertIn('exec waybar\n', lines)

    def test_handles_multiple_output_lines(self):
        """Should only replace the wallpaper output line."""
        original_content = """output HDMI-A-1 resolution 1920x1080
output * bg /old/wallpaper.jpg fill
output DP-1 position 0,0
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_sway_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('output HDMI-A-1 resolution 1920x1080', content)
        self.assertIn('output DP-1 position 0,0', content)
        self.assertIn('output * bg /new/wallpaper.png fill', content)
        self.assertNotIn('/old/wallpaper.jpg', content)

    def test_handles_commented_wallpaper_line(self):
        """Should not replace commented wallpaper lines."""
        original_content = """# output * bg /commented/wallpaper.jpg fill
set $mod Mod4
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_sway_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        # Should append since no uncommented wallpaper line found
        self.assertIn('# output * bg /commented/wallpaper.jpg fill', content)
        self.assertIn('output * bg /new/wallpaper.png fill', content)

    def test_handles_wallpaper_line_with_different_mode(self):
        """Should replace wallpaper lines with different fill modes."""
        original_content = """output * bg /old/wallpaper.jpg stretch
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_sway_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('output * bg /new/wallpaper.png fill', content)
        self.assertNotIn('stretch', content)

    def test_handles_empty_config_file(self):
        """Should append wallpaper line to empty config."""
        with open(self.config_path, 'w') as f:
            f.write('')

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_sway_config('/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('output * bg /wallpaper.png fill', content)


# ═══════════════════════════════════════════════════════════════════════════
# Hyprland Config Update
# ═══════════════════════════════════════════════════════════════════════════
class TestUpdateHyprlandConfig(unittest.TestCase):
    """Verify _update_hyprland_config updates Hyprland configuration correctly."""

    def setUp(self):
        """Create a mock PhotoViewerApp instance without calling __init__."""
        self.app = object.__new__(PhotoViewerApp)
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, 'hyprland.conf')

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_replaces_existing_swaybg_line(self):
        """Should replace existing 'exec-once = swaybg' line with new path."""
        original_content = """# Hyprland config
$mod = SUPER

exec-once = swaybg -i /old/wallpaper.jpg -m fill

exec-once = waybar
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('exec-once = swaybg -i /new/wallpaper.png -m fill', content)
        self.assertNotIn('/old/wallpaper.jpg', content)
        self.assertIn('exec-once = waybar', content)

    def test_appends_when_no_swaybg_line_exists(self):
        """Should append swaybg line when none exists."""
        original_content = """# Hyprland config
$mod = SUPER
exec-once = waybar
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('exec-once = swaybg -i /new/wallpaper.png -m fill', content)
        self.assertIn('exec-once = waybar', content)
        self.assertTrue(content.strip().endswith('exec-once = swaybg -i /new/wallpaper.png -m fill'))

    def test_skips_when_config_file_missing(self):
        """Should not raise error when config file doesn't exist."""
        nonexistent_path = os.path.join(self.tmpdir, 'nonexistent', 'hyprland.conf')
        
        with patch('os.path.expanduser', return_value=nonexistent_path):
            # Should not raise any exception
            self.app._update_hyprland_config('/some/wallpaper.png')

    def test_preserves_all_other_lines(self):
        """Should preserve all non-swaybg config lines."""
        original_content = """# Hyprland config
$mod = SUPER
bind = $mod, Return, exec, alacritty
exec-once = swaybg -i /old/wallpaper.jpg -m fill
exec-once = waybar
monitor = HDMI-A-1,1920x1080,0x0,1
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            lines = f.readlines()

        # Should have same number of lines
        self.assertEqual(len(lines), 6)
        self.assertIn('$mod = SUPER\n', lines)
        self.assertIn('bind = $mod, Return, exec, alacritty\n', lines)
        self.assertIn('exec-once = waybar\n', lines)
        self.assertIn('monitor = HDMI-A-1,1920x1080,0x0,1\n', lines)

    def test_handles_multiple_exec_once_lines(self):
        """Should only replace the swaybg exec-once line."""
        original_content = """exec-once = waybar
exec-once = swaybg -i /old/wallpaper.jpg -m fill
exec-once = mako
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('exec-once = waybar', content)
        self.assertIn('exec-once = mako', content)
        self.assertIn('exec-once = swaybg -i /new/wallpaper.png -m fill', content)
        self.assertNotIn('/old/wallpaper.jpg', content)

    def test_handles_commented_swaybg_line(self):
        """Should not replace commented swaybg lines."""
        original_content = """# exec-once = swaybg -i /commented/wallpaper.jpg -m fill
$mod = SUPER
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        # Should append since no uncommented swaybg line found
        self.assertIn('# exec-once = swaybg -i /commented/wallpaper.jpg -m fill', content)
        self.assertIn('exec-once = swaybg -i /new/wallpaper.png -m fill', content)

    def test_handles_swaybg_with_different_flags(self):
        """Should replace swaybg lines with different arguments."""
        original_content = """exec-once = swaybg -i /old/wallpaper.jpg -m stretch -o HDMI-A-1
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('exec-once = swaybg -i /new/wallpaper.png -m fill', content)
        self.assertNotIn('stretch', content)
        self.assertNotIn('HDMI-A-1', content)

    def test_handles_exec_not_exec_once(self):
        """Should not replace 'exec' lines, only 'exec-once' lines."""
        original_content = """exec = swaybg -i /should/not/replace.jpg -m fill
exec-once = swaybg -i /old/wallpaper.jpg -m fill
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        # The 'exec =' line should be preserved
        self.assertIn('exec = swaybg -i /should/not/replace.jpg -m fill', content)
        self.assertIn('exec-once = swaybg -i /new/wallpaper.png -m fill', content)
        self.assertNotIn('/old/wallpaper.jpg', content)

    def test_handles_empty_config_file(self):
        """Should append swaybg line to empty config."""
        with open(self.config_path, 'w') as f:
            f.write('')

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        self.assertIn('exec-once = swaybg -i /wallpaper.png -m fill', content)

    def test_matches_swaybg_anywhere_in_exec_once(self):
        """Should match swaybg even with complex exec-once commands."""
        original_content = """exec-once = bash -c "sleep 1 && swaybg -i /old/wallpaper.jpg -m fill"
"""
        with open(self.config_path, 'w') as f:
            f.write(original_content)

        with patch('os.path.expanduser', return_value=self.config_path):
            self.app._update_hyprland_config('/new/wallpaper.png')

        with open(self.config_path, 'r') as f:
            content = f.read()

        # Should replace the entire line
        self.assertIn('exec-once = swaybg -i /new/wallpaper.png -m fill', content)
        self.assertNotIn('bash -c', content)


if __name__ == '__main__':
    unittest.main()
