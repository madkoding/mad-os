"""Unit tests for the madOS Launcher dock."""

import json
import os
import sys
import tempfile
import textwrap
import unittest

# ---- Determine REPO_DIR relative to this test file ----
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCHER_LIB = os.path.join(
    REPO_DIR, "airootfs", "usr", "local", "lib"
)

# ======================================================================
# GTK / GI Mock Setup — allows headless testing without GTK or Wayland
# ======================================================================
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import install_gtk_mocks

def _setup_gi_mocks():
    """Install mock gi modules so we can import mados_launcher headlessly."""
    gi_mock, repo_mock = install_gtk_mocks(extra_modules=("GtkLayerShell",))
    # Also add submodules that might be imported directly
    import sys as _sys
    for name in ("Gtk", "GLib", "GdkPixbuf", "Gdk", "Pango", "GtkLayerShell"):
        _sys.modules[f"gi.repository.{name}"] = getattr(repo_mock, name)


# Install mocks before importing mados_launcher
_setup_gi_mocks()

# Add the library path
if LAUNCHER_LIB not in sys.path:
    sys.path.insert(0, LAUNCHER_LIB)

from mados_launcher.config import (
    NORD,
    ICON_SIZE,
    TAB_WIDTH,
    DOCK_WIDTH,
    DEFAULT_MARGIN_TOP,
    DRAG_THRESHOLD,
    EXCLUDED_DESKTOP,
    ANIMATION_DURATION,
    STATE_FILE,
    CONFIG_DIR,
    ICON_ZOOM_SIZE,
    ICON_ZOOM_STEP,
    ICON_ZOOM_INTERVAL_MS,
    AVAHI_DESKTOP_FILES,
)
from mados_launcher.desktop_entries import (
    _clean_exec,
    _parse_desktop_file,
    scan_desktop_entries,
    DesktopEntry,
    EntryGroup,
    group_entries,
    _icon_group_key,
    _is_avahi_running,
)
from mados_launcher import __version__, __app_id__, __app_name__


# ======================================================================
# Test: Configuration Constants
# ======================================================================

class TestConfig(unittest.TestCase):
    """Validate configuration constants are sensible."""

    def test_nord_palette_has_all_colors(self):
        """Nord palette should have all 16 colors (nord0-nord15)."""
        for i in range(16):
            key = f"nord{i}"
            self.assertIn(key, NORD, f"Missing Nord color: {key}")
            self.assertTrue(NORD[key].startswith("#"), f"{key} should be hex")
            self.assertEqual(len(NORD[key]), 7, f"{key} should be 7-char hex")

    def test_icon_size_positive(self):
        self.assertGreater(ICON_SIZE, 0)

    def test_tab_width_positive(self):
        self.assertGreater(TAB_WIDTH, 0)

    def test_dock_width_larger_than_icon(self):
        self.assertGreater(DOCK_WIDTH, ICON_SIZE)

    def test_animation_duration_reasonable(self):
        self.assertGreaterEqual(ANIMATION_DURATION, 100)
        self.assertLessEqual(ANIMATION_DURATION, 1000)

    def test_default_margin_top_positive(self):
        self.assertGreaterEqual(DEFAULT_MARGIN_TOP, 0)

    def test_drag_threshold_positive(self):
        self.assertGreater(DRAG_THRESHOLD, 0)

    def test_excluded_desktop_contains_self(self):
        self.assertIn("mados-launcher.desktop", EXCLUDED_DESKTOP)

    def test_icon_zoom_size_larger_than_icon(self):
        self.assertGreater(ICON_ZOOM_SIZE, ICON_SIZE)

    def test_icon_zoom_step_positive(self):
        self.assertGreater(ICON_ZOOM_STEP, 0)

    def test_icon_zoom_interval_positive(self):
        self.assertGreater(ICON_ZOOM_INTERVAL_MS, 0)

    def test_avahi_desktop_files_is_set(self):
        self.assertIsInstance(AVAHI_DESKTOP_FILES, set)
        self.assertIn("avahi-discover.desktop", AVAHI_DESKTOP_FILES)
        self.assertIn("bvnc.desktop", AVAHI_DESKTOP_FILES)
        self.assertIn("bssh.desktop", AVAHI_DESKTOP_FILES)


# ======================================================================
# Test: Package Metadata
# ======================================================================

class TestMetadata(unittest.TestCase):
    """Validate package metadata."""

    def test_version_format(self):
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3, "Version should be semver X.Y.Z")
        for p in parts:
            self.assertTrue(p.isdigit(), f"Version part '{p}' should be numeric")

    def test_app_id(self):
        self.assertEqual(__app_id__, "mados-launcher")

    def test_app_name(self):
        self.assertEqual(__app_name__, "madOS Launcher")


# ======================================================================
# Test: Exec Field Cleaning
# ======================================================================

class TestCleanExec(unittest.TestCase):
    """Test cleaning of Exec field values from .desktop files."""

    def test_no_field_codes(self):
        self.assertEqual(_clean_exec("chromium"), "chromium")

    def test_strip_percent_u(self):
        self.assertEqual(_clean_exec("chromium %u"), "chromium")

    def test_strip_percent_U(self):
        self.assertEqual(_clean_exec("firefox %U"), "firefox")

    def test_strip_percent_f(self):
        self.assertEqual(_clean_exec("gedit %f"), "gedit")

    def test_strip_percent_F(self):
        self.assertEqual(_clean_exec("nautilus %F"), "nautilus")

    def test_strip_multiple_codes(self):
        self.assertEqual(_clean_exec("app %f %u %i"), "app")

    def test_preserve_flags(self):
        self.assertEqual(
            _clean_exec("chromium --no-sandbox %u"),
            "chromium --no-sandbox",
        )

    def test_strip_percent_k(self):
        self.assertEqual(_clean_exec("app %k"), "app")

    def test_empty_exec(self):
        self.assertEqual(_clean_exec(""), "")

    def test_only_field_code(self):
        self.assertEqual(_clean_exec("%u"), "")


# ======================================================================
# Test: Desktop File Parsing
# ======================================================================

class TestDesktopParsing(unittest.TestCase):
    """Test parsing of individual .desktop files."""

    def _write_desktop(self, content):
        """Write a temp .desktop file and return its path and filename."""
        fd, path = tempfile.mkstemp(suffix=".desktop")
        with os.fdopen(fd, "w") as f:
            f.write(textwrap.dedent(content))
        return path, os.path.basename(path)

    def test_valid_application(self):
        path, fname = self._write_desktop("""\
            [Desktop Entry]
            Type=Application
            Name=Test App
            Exec=test-app
            Icon=utilities-terminal
            Comment=A test application
            Categories=Utility;
        """)
        try:
            entry = _parse_desktop_file(path, fname)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.name, "Test App")
            self.assertEqual(entry.exec_cmd, "test-app")
            self.assertEqual(entry.icon_name, "utilities-terminal")
            self.assertEqual(entry.comment, "A test application")
            self.assertEqual(entry.categories, "Utility;")
        finally:
            os.unlink(path)

    def test_filters_non_application_type(self):
        path, fname = self._write_desktop("""\
            [Desktop Entry]
            Type=Link
            Name=Some Link
            URL=https://example.com
        """)
        try:
            entry = _parse_desktop_file(path, fname)
            self.assertIsNone(entry)
        finally:
            os.unlink(path)

    def test_filters_nodisplay(self):
        path, fname = self._write_desktop("""\
            [Desktop Entry]
            Type=Application
            Name=Hidden App
            Exec=hidden-app
            NoDisplay=true
        """)
        try:
            entry = _parse_desktop_file(path, fname)
            self.assertIsNone(entry)
        finally:
            os.unlink(path)

    def test_filters_hidden(self):
        path, fname = self._write_desktop("""\
            [Desktop Entry]
            Type=Application
            Name=Hidden App 2
            Exec=hidden-app-2
            Hidden=true
        """)
        try:
            entry = _parse_desktop_file(path, fname)
            self.assertIsNone(entry)
        finally:
            os.unlink(path)

    def test_filters_no_exec(self):
        path, fname = self._write_desktop("""\
            [Desktop Entry]
            Type=Application
            Name=No Exec App
        """)
        try:
            entry = _parse_desktop_file(path, fname)
            self.assertIsNone(entry)
        finally:
            os.unlink(path)

    def test_invalid_ini(self):
        fd, path = tempfile.mkstemp(suffix=".desktop")
        with os.fdopen(fd, "w") as f:
            f.write("this is not valid ini content\n{{{garbage")
        try:
            entry = _parse_desktop_file(path, os.path.basename(path))
            self.assertIsNone(entry)
        finally:
            os.unlink(path)

    def test_exec_field_codes_cleaned(self):
        path, fname = self._write_desktop("""\
            [Desktop Entry]
            Type=Application
            Name=Browser
            Exec=chromium --new-window %U
        """)
        try:
            entry = _parse_desktop_file(path, fname)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.exec_cmd, "chromium --new-window")
        finally:
            os.unlink(path)


# ======================================================================
# Test: Desktop Entry Scanning
# ======================================================================

class TestDesktopScanning(unittest.TestCase):
    """Test scanning directories for .desktop files."""

    def test_scan_with_temp_directory(self):
        """Scan a temp directory with known .desktop files."""
        import mados_launcher.desktop_entries as de_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid .desktop file
            with open(os.path.join(tmpdir, "app1.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Bravo App
                    Exec=bravo
                    Icon=utilities-terminal
                """))

            with open(os.path.join(tmpdir, "app2.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Alpha App
                    Exec=alpha
                """))

            # Create a NoDisplay entry that should be filtered
            with open(os.path.join(tmpdir, "hidden.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Hidden
                    Exec=hidden
                    NoDisplay=true
                """))

            # Create self-exclusion entry
            with open(os.path.join(tmpdir, "mados-launcher.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=madOS Launcher
                    Exec=mados-launcher
                    NoDisplay=true
                """))

            # Temporarily override DESKTOP_DIRS on the config module
            orig_dirs = de_mod._config.DESKTOP_DIRS
            de_mod._config.DESKTOP_DIRS = [tmpdir]
            try:
                entries = scan_desktop_entries()
                names = [e.name for e in entries]
                self.assertEqual(names, ["Alpha App", "Bravo App"])
            finally:
                de_mod._config.DESKTOP_DIRS = orig_dirs

    def test_scan_empty_directory(self):
        """Scanning an empty directory should return empty list."""
        import mados_launcher.desktop_entries as de_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dirs = de_mod._config.DESKTOP_DIRS
            de_mod._config.DESKTOP_DIRS = [tmpdir]
            try:
                entries = scan_desktop_entries()
                self.assertEqual(len(entries), 0)
            finally:
                de_mod._config.DESKTOP_DIRS = orig_dirs

    def test_scan_nonexistent_directory(self):
        """Scanning a non-existent directory should not crash."""
        import mados_launcher.desktop_entries as de_mod

        orig_dirs = de_mod._config.DESKTOP_DIRS
        de_mod._config.DESKTOP_DIRS = ["/nonexistent/path/that/does/not/exist"]
        try:
            entries = scan_desktop_entries()
            self.assertEqual(len(entries), 0)
        finally:
            de_mod._config.DESKTOP_DIRS = orig_dirs


# ======================================================================
# Test: State Persistence
# ======================================================================

class TestStatePersistence(unittest.TestCase):
    """Test state save/load functionality."""

    def test_state_file_format(self):
        """State should be stored as JSON with margin_top and expanded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            state = {"margin_top": 150, "expanded": True}
            with open(state_file, "w") as f:
                json.dump(state, f)

            with open(state_file, "r") as f:
                loaded = json.load(f)

            self.assertEqual(loaded["margin_top"], 150)
            self.assertTrue(loaded["expanded"])

    def test_invalid_state_does_not_crash(self):
        """Loading invalid JSON should not raise an exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            with open(state_file, "w") as f:
                f.write("{invalid json")

            # Simulate what _load_state does
            try:
                with open(state_file, "r") as f:
                    json.load(f)
                loaded = True
            except json.JSONDecodeError:
                loaded = False
            self.assertFalse(loaded)


# ======================================================================
# Test: File Structure Validation
# ======================================================================

class TestFileStructure(unittest.TestCase):
    """Validate all expected launcher files exist in the repo."""

    def test_launcher_module_files(self):
        """All required Python module files should exist."""
        expected_files = [
            "__init__.py",
            "__main__.py",
            "app.py",
            "config.py",
            "desktop_entries.py",
            "theme.py",
            "window_tracker.py",
        ]
        lib_dir = os.path.join(
            REPO_DIR, "airootfs", "usr", "local", "lib", "mados_launcher"
        )
        for fname in expected_files:
            fpath = os.path.join(lib_dir, fname)
            self.assertTrue(
                os.path.isfile(fpath),
                f"Missing launcher module file: {fname}",
            )

    def test_bash_launcher_exists(self):
        launcher = os.path.join(
            REPO_DIR, "airootfs", "usr", "local", "bin", "mados-launcher"
        )
        self.assertTrue(os.path.isfile(launcher), "Bash launcher script missing")

    def test_desktop_file_exists(self):
        desktop = os.path.join(
            REPO_DIR, "airootfs", "usr", "share", "applications", "mados-launcher.desktop"
        )
        self.assertTrue(os.path.isfile(desktop), ".desktop file missing")

    def test_desktop_file_nodisplay(self):
        """The launcher .desktop must have NoDisplay=true to avoid self-inclusion."""
        desktop = os.path.join(
            REPO_DIR, "airootfs", "usr", "share", "applications", "mados-launcher.desktop"
        )
        with open(desktop, "r") as f:
            content = f.read()
        self.assertIn("NoDisplay=true", content)


# ======================================================================
# Test: Integration with project configuration
# ======================================================================

class TestProjectIntegration(unittest.TestCase):
    """Verify the launcher is properly integrated into the project configs."""

    def test_gtk_layer_shell_in_packages(self):
        """gtk-layer-shell must be in packages.x86_64."""
        packages_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(packages_file, "r") as f:
            packages = f.read().splitlines()
        self.assertIn("gtk-layer-shell", packages)

    def test_profiledef_has_launcher_bin(self):
        """profiledef.sh should include mados-launcher in file_permissions."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef, "r") as f:
            content = f.read()
        self.assertIn("/usr/local/bin/mados-launcher", content)

    def test_profiledef_has_launcher_lib(self):
        """profiledef.sh should include mados_launcher/ lib in file_permissions."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef, "r") as f:
            content = f.read()
        self.assertIn("/usr/local/lib/mados_launcher/", content)

    def test_sway_autostart_configured(self):
        """Sway config should autostart mados-launcher."""
        sway_config = os.path.join(
            REPO_DIR, "airootfs", "etc", "skel", ".config", "sway", "config"
        )
        with open(sway_config, "r") as f:
            content = f.read()
        self.assertIn("mados-launcher", content)

    def test_hyprland_autostart_configured(self):
        """Hyprland config should autostart mados-launcher."""
        hypr_config = os.path.join(
            REPO_DIR, "airootfs", "etc", "skel", ".config", "hypr", "hyprland.conf"
        )
        with open(hypr_config, "r") as f:
            content = f.read()
        self.assertIn("mados-launcher", content)


# ======================================================================
# Test: Entry Grouping by Category
# ======================================================================

class TestEntryGrouping(unittest.TestCase):
    """Test grouping of desktop entries by shared icon."""

    def _make_entry(self, name, icon_name="", exec_cmd="app", filename="app.desktop"):
        return DesktopEntry(
            name=name, icon_name=icon_name, exec_cmd=exec_cmd,
            comment="", categories="", filename=filename,
        )

    def test_icon_group_key_normal(self):
        entry = self._make_entry("App", icon_name="audio-x-generic")
        self.assertEqual(_icon_group_key(entry), "audio-x-generic")

    def test_icon_group_key_with_path(self):
        entry = self._make_entry("App", icon_name="/usr/share/icons/my-icon.png")
        self.assertEqual(_icon_group_key(entry), "my-icon")

    def test_icon_group_key_empty(self):
        entry = self._make_entry("App", icon_name="")
        self.assertIsNone(_icon_group_key(entry))

    def test_icon_group_key_generic_fallback(self):
        """Generic icons should not be grouped."""
        entry = self._make_entry("App", icon_name="application-x-executable")
        self.assertIsNone(_icon_group_key(entry))

    def test_group_entries_same_icon(self):
        """Two entries with the same icon should form an EntryGroup."""
        entries = [
            self._make_entry("Audio", icon_name="audio-x-generic", filename="audio.desktop"),
            self._make_entry("Player", icon_name="audio-x-generic", filename="player.desktop"),
        ]
        grouped = group_entries(entries)
        self.assertEqual(len(grouped), 1)
        self.assertIsInstance(grouped[0], EntryGroup)
        self.assertEqual(len(grouped[0].entries), 2)

    def test_group_entries_different_icons_not_grouped(self):
        """Entries with different icons should remain separate."""
        entries = [
            self._make_entry("Audio", icon_name="audio-x-generic", filename="audio.desktop"),
            self._make_entry("Viewer", icon_name="image-x-generic", filename="viewer.desktop"),
        ]
        grouped = group_entries(entries)
        self.assertEqual(len(grouped), 2)
        for item in grouped:
            self.assertIsInstance(item, DesktopEntry)

    def test_group_entries_mixed(self):
        """Mix of grouped and ungrouped entries."""
        entries = [
            self._make_entry("Player A", icon_name="audio-x-generic", filename="a.desktop"),
            self._make_entry("Player B", icon_name="audio-x-generic", filename="b.desktop"),
            self._make_entry("Solo App", icon_name="solo-icon", filename="solo.desktop"),
        ]
        grouped = group_entries(entries)
        groups = [g for g in grouped if isinstance(g, EntryGroup)]
        singles = [g for g in grouped if isinstance(g, DesktopEntry)]
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].entries), 2)
        self.assertEqual(len(singles), 1)
        self.assertEqual(singles[0].name, "Solo App")

    def test_group_entries_no_icon_not_grouped(self):
        """Entries with no icon stay ungrouped even if multiple have no icon."""
        entries = [
            self._make_entry("App A", icon_name="", filename="a.desktop"),
            self._make_entry("App B", icon_name="", filename="b.desktop"),
        ]
        grouped = group_entries(entries)
        self.assertEqual(len(grouped), 2)
        for item in grouped:
            self.assertIsInstance(item, DesktopEntry)

    def test_group_entries_sorted(self):
        """Results should be sorted alphabetically."""
        entries = [
            self._make_entry("Z App", icon_name="z-icon", filename="z.desktop"),
            self._make_entry("Audio A", icon_name="audio-x-generic", filename="aa.desktop"),
            self._make_entry("Audio B", icon_name="audio-x-generic", filename="ab.desktop"),
            self._make_entry("A App", icon_name="a-icon", filename="a.desktop"),
        ]
        grouped = group_entries(entries)
        names = []
        for item in grouped:
            if isinstance(item, EntryGroup):
                names.append(item.representative.name)
            else:
                names.append(item.name)
        self.assertEqual(names, sorted(names, key=str.lower))

    def test_entry_group_representative(self):
        """EntryGroup representative should be the first entry."""
        entries = [
            self._make_entry("First", icon_name="shared-icon", filename="first.desktop"),
            self._make_entry("Second", icon_name="shared-icon", filename="second.desktop"),
        ]
        grouped = group_entries(entries)
        group = [g for g in grouped if isinstance(g, EntryGroup)][0]
        self.assertEqual(group.representative.name, "First")


# ======================================================================
# Test: Window Tracker
# ======================================================================

from mados_launcher.window_tracker import _exec_to_match_key, WindowTracker


class TestExecToMatchKey(unittest.TestCase):
    """Test extracting match keys from Exec commands."""

    def test_simple_binary(self):
        self.assertEqual(_exec_to_match_key("chromium"), "chromium")

    def test_full_path_binary(self):
        self.assertEqual(_exec_to_match_key("/usr/bin/chromium"), "chromium")

    def test_binary_with_args(self):
        self.assertEqual(
            _exec_to_match_key("chromium --no-sandbox --new-window"),
            "chromium",
        )

    def test_env_prefix(self):
        self.assertEqual(
            _exec_to_match_key("env VAR=val firefox"),
            "firefox",
        )

    def test_multiple_env_vars(self):
        self.assertEqual(
            _exec_to_match_key("env GTK_THEME=Nordic GDK_BACKEND=wayland firefox"),
            "firefox",
        )

    def test_python_module(self):
        self.assertEqual(
            _exec_to_match_key("python3 -m mados_equalizer"),
            "mados-equalizer",
        )

    def test_python_module_with_path(self):
        self.assertEqual(
            _exec_to_match_key("/usr/bin/python3 -m mados_photo_viewer"),
            "mados-photo-viewer",
        )

    def test_empty_exec(self):
        self.assertEqual(_exec_to_match_key(""), "")

    def test_none_exec(self):
        self.assertEqual(_exec_to_match_key(None), "")

    def test_only_env(self):
        self.assertEqual(_exec_to_match_key("env"), "")


class TestWindowTracker(unittest.TestCase):
    """Test WindowTracker matching logic."""

    def test_tracker_init(self):
        tracker = WindowTracker()
        self.assertIsInstance(tracker._running, set)
        self.assertIsInstance(tracker._urgent, set)
        self.assertIsInstance(tracker._focused, set)

    def test_is_running_no_windows(self):
        tracker = WindowTracker()
        self.assertFalse(tracker.is_running("chromium"))

    def test_is_running_with_match(self):
        tracker = WindowTracker()
        tracker._running = {"chromium", "foot"}
        self.assertTrue(tracker.is_running("chromium"))
        self.assertTrue(tracker.is_running("/usr/bin/foot"))
        self.assertFalse(tracker.is_running("firefox"))

    def test_is_running_by_desktop_filename(self):
        tracker = WindowTracker()
        tracker._running = {"org.mozilla.firefox"}
        # Direct exec won't match, but desktop filename fallback might
        self.assertFalse(tracker.is_running("firefox"))
        # If app_id matches the desktop filename base
        tracker._running = {"firefox"}
        self.assertTrue(
            tracker.is_running("something-else", "firefox.desktop")
        )

    def test_is_urgent(self):
        tracker = WindowTracker()
        tracker._running = {"foot"}
        tracker._urgent = {"foot"}
        self.assertTrue(tracker.is_urgent("/usr/bin/foot"))
        self.assertFalse(tracker.is_urgent("chromium"))

    def test_is_focused(self):
        tracker = WindowTracker()
        tracker._running = {"chromium"}
        tracker._focused = {"chromium"}
        self.assertTrue(tracker.is_focused("chromium"))
        self.assertFalse(tracker.is_focused("foot"))

    def test_python_module_match(self):
        tracker = WindowTracker()
        tracker._running = {"mados-equalizer"}
        self.assertTrue(
            tracker.is_running("python3 -m mados_equalizer")
        )


# ======================================================================
# Test: Avahi Filtering
# ======================================================================

class TestAvahiFiltering(unittest.TestCase):
    """Test filtering of Avahi-related desktop entries."""

    def test_is_avahi_running_returns_bool(self):
        """_is_avahi_running() should return a boolean."""
        result = _is_avahi_running()
        self.assertIsInstance(result, bool)

    def test_avahi_entries_filtered_when_inactive(self):
        """Avahi desktop entries should be filtered when avahi-daemon is not running."""
        import mados_launcher.desktop_entries as de_mod
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create avahi desktop files
            with open(os.path.join(tmpdir, "avahi-discover.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Avahi Discover
                    Exec=avahi-discover
                    Icon=network-wired
                """))

            with open(os.path.join(tmpdir, "bvnc.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Avahi VNC Browser
                    Exec=bvnc
                    Icon=network-wired
                """))

            # Create a normal desktop file
            with open(os.path.join(tmpdir, "normal-app.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Normal App
                    Exec=normal-app
                    Icon=utilities-terminal
                """))

            # Mock avahi as not running
            orig_dirs = de_mod._config.DESKTOP_DIRS
            de_mod._config.DESKTOP_DIRS = [tmpdir]
            try:
                with patch.object(de_mod, '_is_avahi_running', return_value=False):
                    entries = scan_desktop_entries()
                    names = [e.name for e in entries]
                    self.assertEqual(names, ["Normal App"])
                    self.assertNotIn("Avahi Discover", names)
                    self.assertNotIn("Avahi VNC Browser", names)
            finally:
                de_mod._config.DESKTOP_DIRS = orig_dirs

    def test_avahi_entries_included_when_active(self):
        """Avahi desktop entries should be included when avahi-daemon is running."""
        import mados_launcher.desktop_entries as de_mod
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create avahi desktop files
            with open(os.path.join(tmpdir, "avahi-discover.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Avahi Discover
                    Exec=avahi-discover
                    Icon=network-wired
                """))

            with open(os.path.join(tmpdir, "bssh.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Avahi SSH Browser
                    Exec=bssh
                    Icon=network-wired
                """))

            # Create a normal desktop file
            with open(os.path.join(tmpdir, "normal-app.desktop"), "w") as f:
                f.write(textwrap.dedent("""\
                    [Desktop Entry]
                    Type=Application
                    Name=Normal App
                    Exec=normal-app
                    Icon=utilities-terminal
                """))

            # Mock avahi as running
            orig_dirs = de_mod._config.DESKTOP_DIRS
            de_mod._config.DESKTOP_DIRS = [tmpdir]
            try:
                with patch.object(de_mod, '_is_avahi_running', return_value=True):
                    entries = scan_desktop_entries()
                    names = [e.name for e in entries]
                    self.assertIn("Avahi Discover", names)
                    self.assertIn("Avahi SSH Browser", names)
                    self.assertIn("Normal App", names)
            finally:
                de_mod._config.DESKTOP_DIRS = orig_dirs


# ======================================================================
# Test: Icon Zoom Configuration
# ======================================================================

class TestIconZoomConfig(unittest.TestCase):
    """Validate icon zoom animation configuration."""

    def test_zoom_size_reachable_in_steps(self):
        """ICON_ZOOM_SIZE should be reachable within reasonable steps from ICON_SIZE."""
        zoom_delta = ICON_ZOOM_SIZE - ICON_SIZE
        self.assertGreater(zoom_delta, 0, "ICON_ZOOM_SIZE must be larger than ICON_SIZE")
        
        # Verify the delta is reachable with the step size
        # (it doesn't have to be perfectly divisible, just reasonable)
        max_steps = zoom_delta / ICON_ZOOM_STEP
        # 50 steps at ICON_ZOOM_INTERVAL_MS each would be 1250ms — well beyond usable
        self.assertLessEqual(max_steps, 50, "Zoom should complete in a reasonable number of steps")

    def test_zoom_animation_total_time_reasonable(self):
        """Total zoom animation time should be between 50ms and 500ms."""
        zoom_delta = ICON_ZOOM_SIZE - ICON_SIZE
        steps = zoom_delta / ICON_ZOOM_STEP
        total_time_ms = steps * ICON_ZOOM_INTERVAL_MS
        
        self.assertGreaterEqual(
            total_time_ms, 50,
            f"Animation too fast: {total_time_ms}ms (should be >= 50ms)"
        )
        self.assertLessEqual(
            total_time_ms, 500,
            f"Animation too slow: {total_time_ms}ms (should be <= 500ms)"
        )


if __name__ == "__main__":
    unittest.main()
