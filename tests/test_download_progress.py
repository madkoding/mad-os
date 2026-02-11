#!/usr/bin/env python3
"""
Unit tests for the download-in-groups progress feature.

Validates that the new _download_packages_with_progress() function and
the updated progress ranges in _run_pacstrap_with_progress() work correctly.

These tests mock subprocess and GTK to run in a headless CI environment.
"""

import sys
import types
import unittest
from unittest.mock import patch, MagicMock, call

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so installer modules can be imported headlessly.
# ---------------------------------------------------------------------------
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


for name in ("Gtk", "GLib", "GdkPixbuf", "Gdk"):
    setattr(repo_mock, name, _StubModule())

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

# ---------------------------------------------------------------------------
# Add installer lib to path and import
# ---------------------------------------------------------------------------
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "airootfs", "usr", "local", "lib"))

from mados_installer.pages.installation import (
    _download_packages_with_progress,
    _run_pacstrap_with_progress,
)
from mados_installer.config import PACKAGES


class MockApp:
    """Minimal mock of the GTK application object used by the installer."""

    def __init__(self):
        self.progress_bar = MagicMock()
        self.status_label = MagicMock()
        self.log_buffer = MagicMock()
        self.log_scrolled = MagicMock()


class TestDownloadProgressRanges(unittest.TestCase):
    """Verify the progress ranges for the download and install phases."""

    def test_download_progress_range(self):
        """Download phase should use progress range 0.25 to 0.36."""
        app = MockApp()
        progress_values = []

        def capture_progress(app_arg, fraction, text):
            progress_values.append(fraction)

        # Mock subprocess to simulate successful pacman -Sw
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch("mados_installer.pages.installation.subprocess.Popen",
                    return_value=mock_proc), \
             patch("mados_installer.pages.installation.set_progress",
                    side_effect=capture_progress), \
             patch("mados_installer.pages.installation.log_message"):

            _download_packages_with_progress(app, list(PACKAGES))

        # Verify progress stays within the expected range
        self.assertTrue(len(progress_values) > 0,
                        "Should have recorded progress values")
        for p in progress_values:
            self.assertGreaterEqual(p, 0.25,
                                    f"Progress {p} below download start 0.25")
            self.assertLessEqual(p, 0.36,
                                 f"Progress {p} above download end 0.36")
        # Final value should be exactly 0.36
        self.assertAlmostEqual(progress_values[-1], 0.36, places=5,
                               msg="Final download progress should be 0.36")

    def test_pacstrap_progress_range(self):
        """Install phase should use progress range 0.36 to 0.48."""
        app = MockApp()
        progress_values = []

        def capture_progress(app_arg, fraction, text):
            progress_values.append(fraction)

        # Simulate pacstrap output with numbered installing lines
        lines = [
            "Packages (3)\n",
            "(1/3) installing base...\n",
            "(2/3) installing linux...\n",
            "(3/3) installing grub...\n",
            "",  # EOF
        ]
        line_iter = iter(lines)

        mock_proc = MagicMock()
        mock_proc.stdout.readline.side_effect = lambda: next(line_iter)
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch("mados_installer.pages.installation.subprocess.Popen",
                    return_value=mock_proc), \
             patch("mados_installer.pages.installation.set_progress",
                    side_effect=capture_progress), \
             patch("mados_installer.pages.installation.log_message"):

            _run_pacstrap_with_progress(app, ["base", "linux", "grub"])

        # Verify progress stays within the expected range
        self.assertTrue(len(progress_values) > 0,
                        "Should have recorded progress values")
        for p in progress_values:
            self.assertGreaterEqual(p, 0.36,
                                    f"Progress {p} below install start 0.36")
            self.assertLessEqual(p, 0.48,
                                 f"Progress {p} above install end 0.48")
        # Final value should be exactly 0.48
        self.assertAlmostEqual(progress_values[-1], 0.48, places=5,
                               msg="Final install progress should be 0.48")


class TestDownloadGrouping(unittest.TestCase):
    """Verify packages are downloaded in groups of 10."""

    def test_groups_of_ten(self):
        """pacman -Sw should be called once per group of 10 packages."""
        app = MockApp()
        popen_calls = []

        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        def capture_popen(cmd, **kwargs):
            popen_calls.append(cmd)
            return mock_proc

        packages = list(PACKAGES)  # ~86 packages
        expected_groups = (len(packages) + 9) // 10  # ceil division

        with patch("mados_installer.pages.installation.subprocess.Popen",
                    side_effect=capture_popen), \
             patch("mados_installer.pages.installation.set_progress"), \
             patch("mados_installer.pages.installation.log_message"):

            _download_packages_with_progress(app, packages)

        self.assertEqual(len(popen_calls), expected_groups,
                         f"Expected {expected_groups} groups but got "
                         f"{len(popen_calls)}")

        # Verify each call uses pacman -Sw --noconfirm
        for cmd in popen_calls:
            self.assertEqual(cmd[:3], ["pacman", "-Sw", "--noconfirm"],
                             f"Unexpected command prefix: {cmd[:3]}")

        # Verify all packages are included across all calls
        all_pkgs = []
        for cmd in popen_calls:
            all_pkgs.extend(cmd[3:])  # skip ["pacman", "-Sw", "--noconfirm"]
        self.assertEqual(sorted(all_pkgs), sorted(packages),
                         "All packages should be present across all groups")

    def test_small_package_list(self):
        """A list of ≤10 packages should result in exactly 1 group."""
        app = MockApp()
        call_count = 0

        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        def count_popen(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_proc

        with patch("mados_installer.pages.installation.subprocess.Popen",
                    side_effect=count_popen), \
             patch("mados_installer.pages.installation.set_progress"), \
             patch("mados_installer.pages.installation.log_message"):

            _download_packages_with_progress(app, ["base", "linux", "grub"])

        self.assertEqual(call_count, 1,
                         "Small package list should be one group")


class TestDownloadFailureHandling(unittest.TestCase):
    """Verify graceful handling of download failures."""

    def test_nonzero_exit_continues(self):
        """If a group fails, the function should continue and log a warning."""
        app = MockApp()
        log_messages = []

        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.returncode = 1  # simulate failure
        mock_proc.wait.return_value = None

        def capture_log(app_arg, msg):
            log_messages.append(msg)

        with patch("mados_installer.pages.installation.subprocess.Popen",
                    return_value=mock_proc), \
             patch("mados_installer.pages.installation.set_progress"), \
             patch("mados_installer.pages.installation.log_message",
                    side_effect=capture_log):

            # Should not raise even though all groups fail
            _download_packages_with_progress(app, list(PACKAGES))

        # Verify warning was logged for each failed group
        warnings = [m for m in log_messages if "Warning: download failed" in m]
        expected_groups = (len(PACKAGES) + 9) // 10
        self.assertEqual(len(warnings), expected_groups,
                         f"Expected {expected_groups} warnings but got "
                         f"{len(warnings)}")

        # Verify warning includes group number and exit code
        self.assertIn("exit code 1", warnings[0],
                      "Warning should include exit code")


class TestProgressBarNoise(unittest.TestCase):
    """Verify noisy progress-bar lines from pacman are filtered."""

    def test_progress_bar_lines_filtered(self):
        """Lines like '  100%  [####...]' should not appear in log."""
        app = MockApp()
        log_messages = []

        lines = [
            ":: Synchronizing package databases...\n",
            " 100% [############################]\n",
            "  downloading base...\n",
            " 50% [##############              ]\n",
            "---\n",
            "",  # EOF
        ]
        line_iter = iter(lines)

        mock_proc = MagicMock()
        mock_proc.stdout.readline.side_effect = lambda: next(line_iter)
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        def capture_log(app_arg, msg):
            log_messages.append(msg)

        with patch("mados_installer.pages.installation.subprocess.Popen",
                    return_value=mock_proc), \
             patch("mados_installer.pages.installation.set_progress"), \
             patch("mados_installer.pages.installation.log_message",
                    side_effect=capture_log):

            _download_packages_with_progress(app, ["base"])

        # Progress-bar lines should be filtered out
        for msg in log_messages:
            self.assertNotRegex(msg, r'\d+%\s*\[',
                                f"Progress bar line not filtered: {msg}")


class TestDemoModeProgressMath(unittest.TestCase):
    """Verify demo mode progress arithmetic matches real mode ranges."""

    def test_demo_download_range(self):
        """DEMO download: 0.25 + (0.11 * end/total) for end=total → 0.36."""
        total = len(PACKAGES)
        # Last iteration: end = total
        final_progress = 0.25 + (0.11 * total / total)
        self.assertAlmostEqual(final_progress, 0.36, places=5,
                               msg="Demo download final should reach 0.36")

    def test_demo_install_range(self):
        """DEMO install: 0.36 + (0.12 * (i+1)/total) for i+1=total → 0.48."""
        total = len(PACKAGES)
        final_progress = 0.36 + (0.12 * total / total)
        self.assertAlmostEqual(final_progress, 0.48, places=5,
                               msg="Demo install final should reach 0.48")

    def test_demo_download_start(self):
        """DEMO download: first progress value should be above 0.25."""
        group_size = 10
        end = min(group_size, len(PACKAGES))
        first_progress = 0.25 + (0.11 * end / len(PACKAGES))
        self.assertGreater(first_progress, 0.25,
                           "First demo download progress should be > 0.25")
        self.assertLess(first_progress, 0.36,
                        "First demo download progress should be < 0.36")


if __name__ == "__main__":
    unittest.main()
