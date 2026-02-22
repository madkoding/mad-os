#!/usr/bin/env python3
"""
Test responsive layout changes in madOS applications.

This test suite validates that hardcoded fixed-width UI elements have been
replaced with responsive, proportional layouts that adapt to different screen sizes.
"""

import sys
import os
import types
import unittest
import re

# Repository paths
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")

# Mock gi/GTK modules (must be done before any GTK imports)
gi_mock = types.ModuleType("gi")
gi_mock.require_version = lambda *a, **kw: None
repo_mock = types.ModuleType("gi.repository")


class _StubMeta(type):
    def __getattr__(cls, name):
        return _StubWidget


class _StubWidget(metaclass=_StubMeta):
    def __init__(self, *a, **kw):
        pass

    def __init_subclass__(cls, **kw):
        pass

    def __getattr__(self, name):
        return _stub_func


def _stub_func(*a, **kw):
    return _StubWidget()


class _StubModule:
    def __getattr__(self, name):
        return _StubWidget


for name in ("Gtk", "GLib", "GdkPixbuf", "Gdk", "Pango"):
    setattr(repo_mock, name, _StubModule())

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock


class TestInstallerResponsiveLayout(unittest.TestCase):
    """Test that installer pages use responsive layouts instead of fixed widths."""

    def test_user_page_no_fixed_width(self):
        """User page should not use fixed-width set_size_request."""
        user_page_path = os.path.join(LIB_DIR, "mados_installer", "pages", "user.py")
        self.assertTrue(
            os.path.exists(user_page_path), f"User page not found at {user_page_path}"
        )

        with open(user_page_path, "r") as f:
            content = f.read()

        # Should NOT contain fixed width set_size_request patterns
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*380\s*,",
            "User page should not use set_size_request(380, ...)",
        )
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*\d{3,}\s*,",
            "User page should not use fixed-width set_size_request with 3+ digit widths",
        )

    def test_user_page_uses_hexpand(self):
        """User page should use set_hexpand(True) for responsive layout."""
        user_page_path = os.path.join(LIB_DIR, "mados_installer", "pages", "user.py")

        with open(user_page_path, "r") as f:
            content = f.read()

        # Should use set_hexpand(True)
        self.assertIn(
            "set_hexpand(True)", content, "User page should use set_hexpand(True)"
        )

    def test_user_page_uses_fill_alignment(self):
        """User page should use Gtk.Align.FILL instead of CENTER."""
        user_page_path = os.path.join(LIB_DIR, "mados_installer", "pages", "user.py")

        with open(user_page_path, "r") as f:
            content = f.read()

        # Should use FILL alignment
        self.assertIn(
            "Gtk.Align.FILL",
            content,
            "User page should use Gtk.Align.FILL for responsive layout",
        )

    def test_locale_page_no_fixed_width(self):
        """Locale page should not use fixed-width set_size_request."""
        locale_page_path = os.path.join(
            LIB_DIR, "mados_installer", "pages", "locale.py"
        )
        self.assertTrue(
            os.path.exists(locale_page_path),
            f"Locale page not found at {locale_page_path}",
        )

        with open(locale_page_path, "r") as f:
            content = f.read()

        # Should NOT contain fixed width set_size_request patterns
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*380\s*,",
            "Locale page should not use set_size_request(380, ...)",
        )
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*\d{3,}\s*,",
            "Locale page should not use fixed-width set_size_request with 3+ digit widths",
        )

    def test_locale_page_uses_hexpand(self):
        """Locale page should use set_hexpand(True) for responsive layout."""
        locale_page_path = os.path.join(
            LIB_DIR, "mados_installer", "pages", "locale.py"
        )

        with open(locale_page_path, "r") as f:
            content = f.read()

        # Should use set_hexpand(True)
        self.assertIn(
            "set_hexpand(True)", content, "Locale page should use set_hexpand(True)"
        )

    def test_completion_page_no_fixed_width(self):
        """Completion page should not use fixed-width set_size_request."""
        completion_page_path = os.path.join(
            LIB_DIR, "mados_installer", "pages", "completion.py"
        )
        self.assertTrue(
            os.path.exists(completion_page_path),
            f"Completion page not found at {completion_page_path}",
        )

        with open(completion_page_path, "r") as f:
            content = f.read()

        # Should NOT contain fixed width set_size_request patterns (420 or 380)
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*420\s*,",
            "Completion page should not use set_size_request(420, ...)",
        )
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*380\s*,",
            "Completion page should not use set_size_request(380, ...)",
        )
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*\d{3,}\s*,",
            "Completion page should not use fixed-width set_size_request with 3+ digit widths",
        )

    def test_completion_page_uses_hexpand(self):
        """Completion page should use set_hexpand(True) for responsive layout."""
        completion_page_path = os.path.join(
            LIB_DIR, "mados_installer", "pages", "completion.py"
        )

        with open(completion_page_path, "r") as f:
            content = f.read()

        # Should use set_hexpand(True)
        self.assertIn(
            "set_hexpand(True)", content, "Completion page should use set_hexpand(True)"
        )

    def test_welcome_page_uses_flowbox(self):
        """Welcome page should use FlowBox for features instead of horizontal Box."""
        welcome_page_path = os.path.join(
            LIB_DIR, "mados_installer", "pages", "welcome.py"
        )
        self.assertTrue(
            os.path.exists(welcome_page_path),
            f"Welcome page not found at {welcome_page_path}",
        )

        with open(welcome_page_path, "r") as f:
            content = f.read()

        # Should use FlowBox for responsive feature layout
        self.assertIn(
            "FlowBox",
            content,
            "Welcome page should use FlowBox for responsive feature layout",
        )


class TestEqualizerResponsiveLayout(unittest.TestCase):
    """Test that equalizer app uses smaller minimum sizes."""

    def test_equalizer_gain_indicator_smaller_size(self):
        """Equalizer GainIndicator should use 20x80 instead of 30x120."""
        equalizer_app_path = os.path.join(LIB_DIR, "mados_equalizer", "app.py")
        self.assertTrue(
            os.path.exists(equalizer_app_path),
            f"Equalizer app not found at {equalizer_app_path}",
        )

        with open(equalizer_app_path, "r") as f:
            content = f.read()

        # Should NOT use old size 30x120
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*30\s*,\s*120\s*\)",
            "GainIndicator should not use set_size_request(30, 120)",
        )

        # Should use new size 20x80
        self.assertRegex(
            content,
            r"set_size_request\s*\(\s*20\s*,\s*80\s*\)",
            "GainIndicator should use set_size_request(20, 80)",
        )

    def test_equalizer_enable_button_smaller_size(self):
        """Equalizer enable button should use width 80 instead of 100."""
        equalizer_app_path = os.path.join(LIB_DIR, "mados_equalizer", "app.py")

        with open(equalizer_app_path, "r") as f:
            content = f.read()

        # Check for enable button with smaller size (should use 80, not 100)
        # Look for enable_button followed by set_size_request within reasonable proximity
        # Limit search to 200 characters to avoid false matches
        enable_btn_pattern = r"enable_button.{0,200}?set_size_request\s*\(\s*(\d+)\s*,"
        matches = re.findall(enable_btn_pattern, content, re.DOTALL)

        for width_str in matches:
            width = int(width_str)
            self.assertLessEqual(
                width, 80, f"Enable button should use width 80 or less, not {width}"
            )

    def test_equalizer_preset_combo_smaller_size(self):
        """Equalizer preset combo should use width 120 instead of 180."""
        equalizer_app_path = os.path.join(LIB_DIR, "mados_equalizer", "app.py")

        with open(equalizer_app_path, "r") as f:
            content = f.read()

        # Should NOT use old size 180
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*180\s*,",
            "Preset combo should not use set_size_request(180, ...)",
        )

    def test_equalizer_uses_hexpand(self):
        """Equalizer should use set_hexpand for responsive elements."""
        equalizer_app_path = os.path.join(LIB_DIR, "mados_equalizer", "app.py")

        with open(equalizer_app_path, "r") as f:
            content = f.read()

        # Should use set_hexpand(True) for flexible sizing
        self.assertIn(
            "set_hexpand(True)",
            content,
            "Equalizer should use set_hexpand(True) for responsive layout",
        )

    def test_equalizer_volume_box_smaller_size(self):
        """Equalizer volume box should use width 60 instead of 80."""
        equalizer_app_path = os.path.join(LIB_DIR, "mados_equalizer", "app.py")

        with open(equalizer_app_path, "r") as f:
            content = f.read()

        # Look for volume_box directly followed by set_size_request (within 300 chars)
        # This pattern matches "volume_box = Gtk.Box..." then "volume_box.set_size_request"
        # Limited search range to avoid performance issues and false matches
        volume_box_pattern = (
            r"volume_box\s*=.{0,300}?volume_box\.set_size_request\s*\(\s*(\d+)\s*,"
        )
        matches = re.findall(volume_box_pattern, content, re.DOTALL)

        # Should find at least one volume_box size request
        self.assertGreater(len(matches), 0, "Should find volume_box size request")

        for width_str in matches:
            width = int(width_str)
            self.assertLessEqual(
                width, 60, f"Volume box should use width 60 or less, not {width}"
            )


class TestPhotoViewerResponsiveLayout(unittest.TestCase):
    """Test that photo viewer app uses smaller minimum sizes."""

    def test_photo_viewer_size_scale_smaller(self):
        """Photo viewer size scale should use width 80 instead of 120."""
        photo_viewer_path = os.path.join(LIB_DIR, "mados_photo_viewer", "app.py")
        self.assertTrue(
            os.path.exists(photo_viewer_path),
            f"Photo viewer app not found at {photo_viewer_path}",
        )

        with open(photo_viewer_path, "r") as f:
            content = f.read()

        # Look for size-related size requests (unified size slider)
        size_matches = re.findall(
            r"size_scale.*?set_size_request\s*\(\s*(\d+)", content, re.DOTALL | re.IGNORECASE
        )

        for match in size_matches:
            width = int(match)
            self.assertLessEqual(
                width, 80, f"Size scale width should be 80 or less, not {width}"
            )

    def test_photo_viewer_uses_icon_toolbar(self):
        """Photo viewer should use a single Gtk.Toolbar with icon style."""
        photo_viewer_path = os.path.join(LIB_DIR, "mados_photo_viewer", "app.py")

        with open(photo_viewer_path, "r") as f:
            content = f.read()

        # Should use Gtk.Toolbar (icon-based like PDF viewer)
        self.assertIn(
            "Gtk.Toolbar()",
            content,
            "Photo viewer should use Gtk.Toolbar() for icon-based toolbar",
        )
        self.assertIn(
            "ToolbarStyle.ICONS",
            content,
            "Photo viewer toolbar should use ICONS style",
        )

    def test_photo_viewer_uses_hexpand(self):
        """Photo viewer should use set_hexpand for responsive elements."""
        photo_viewer_path = os.path.join(LIB_DIR, "mados_photo_viewer", "app.py")

        with open(photo_viewer_path, "r") as f:
            content = f.read()

        # Should use set_hexpand(True) for flexible sizing
        self.assertIn(
            "set_hexpand(True)",
            content,
            "Photo viewer should use set_hexpand(True) for responsive layout",
        )

    def test_video_player_smaller_minimum_size(self):
        """Video player should use smaller minimum size 320x180 instead of 640x360."""
        video_player_path = os.path.join(
            LIB_DIR, "mados_photo_viewer", "video_player.py"
        )
        self.assertTrue(
            os.path.exists(video_player_path),
            f"Video player not found at {video_player_path}",
        )

        with open(video_player_path, "r") as f:
            content = f.read()

        # Should NOT use old size 640x360
        self.assertNotRegex(
            content,
            r"set_size_request\s*\(\s*640\s*,\s*360\s*\)",
            "Video player should not use set_size_request(640, 360)",
        )

        # Should use new size 320x180
        self.assertRegex(
            content,
            r"set_size_request\s*\(\s*320\s*,\s*180\s*\)",
            "Video player should use set_size_request(320, 180)",
        )

    def test_video_player_volume_smaller(self):
        """Video player volume should use width 80 instead of 100."""
        video_player_path = os.path.join(
            LIB_DIR, "mados_photo_viewer", "video_player.py"
        )

        with open(video_player_path, "r") as f:
            content = f.read()

        # Look for volume scale size request (should be on same line or next line)
        volume_pattern = r"_volume_scale[^\n]*\n[^\n]*set_size_request\s*\(\s*(\d+)"
        volume_matches = re.findall(volume_pattern, content)

        # Should have at least one volume scale size request
        self.assertGreater(
            len(volume_matches),
            0,
            "Video player should have volume scale size request",
        )

        for match in volume_matches:
            width = int(match)
            self.assertLessEqual(
                width, 80, f"Volume control width should be 80 or less, not {width}"
            )


class TestResponsiveLayoutIntegration(unittest.TestCase):
    """Integration tests for overall responsive layout patterns."""

    def test_no_large_fixed_widths_in_installer(self):
        """Installer pages should not contain large fixed widths (300+)."""
        installer_pages_dir = os.path.join(LIB_DIR, "mados_installer", "pages")
        self.assertTrue(
            os.path.exists(installer_pages_dir),
            f"Installer pages directory not found at {installer_pages_dir}",
        )

        for filename in os.listdir(installer_pages_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                filepath = os.path.join(installer_pages_dir, filename)
                with open(filepath, "r") as f:
                    content = f.read()

                # Check for large fixed widths (300+) in set_size_request
                matches = re.findall(r"set_size_request\s*\(\s*(\d+)\s*,", content)

                for width_str in matches:
                    width = int(width_str)
                    self.assertLess(
                        width,
                        300,
                        f"{filename} should not use large fixed width {width} in set_size_request",
                    )

    def test_apps_use_responsive_patterns(self):
        """All GUI apps should use responsive patterns like hexpand or proportional sizing."""
        app_dirs = [
            "mados_equalizer",
            "mados_photo_viewer",
        ]

        for app_dir in app_dirs:
            app_path = os.path.join(LIB_DIR, app_dir, "app.py")
            if os.path.exists(app_path):
                with open(app_path, "r") as f:
                    content = f.read()

                # Should use at least one responsive pattern
                has_responsive_pattern = (
                    "set_hexpand(True)" in content
                    or "set_vexpand(True)" in content
                    or "_on_paned_allocate" in content
                    or "FlowBox" in content
                )

                self.assertTrue(
                    has_responsive_pattern,
                    f"{app_dir}/app.py should use responsive layout patterns",
                )


if __name__ == "__main__":
    unittest.main()
