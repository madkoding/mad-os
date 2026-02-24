#!/usr/bin/env python3
"""
Unit tests for the rsync-based installation flow.

Validates that ``_rsync_rootfs_with_progress()`` correctly invokes rsync to
copy the live rootfs to /mnt, cleans up archiso artifacts, installs extra
packages, and reports progress through the expected range (0.21 → 0.48).

These tests mock subprocess and GTK to run in a headless CI environment.
"""

import os
import re
import subprocess
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


for name in ("Gtk", "GLib", "GdkPixbuf", "Gdk", "Pango"):
    setattr(repo_mock, name, _StubModule())

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

# ---------------------------------------------------------------------------
# Add installer lib to path and import
# ---------------------------------------------------------------------------
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "airootfs", "usr", "local", "lib")
)

from mados_installer.pages.installation import _rsync_rootfs_with_progress
from mados_installer.config import RSYNC_EXCLUDES


class MockApp:
    """Minimal mock of the GTK application object used by the installer."""

    def __init__(self):
        self.progress_bar = MagicMock()
        self.status_label = MagicMock()
        self.log_buffer = MagicMock()
        self.log_scrolled = MagicMock()


# ═══════════════════════════════════════════════════════════════════════════
# Rsync command construction
# ═══════════════════════════════════════════════════════════════════════════
class TestRsyncCommand(unittest.TestCase):
    """Verify rsync is invoked with the correct arguments."""

    def _run_rsync(self, rsync_returncode=0, extras_returncode=0):
        """Run _rsync_rootfs_with_progress with mocked subprocess.

        Returns (popen_calls, run_calls) — lists of command lists passed to
        subprocess.Popen and subprocess.run respectively.
        """
        app = MockApp()
        popen_calls = []
        run_calls = []

        # First Popen call → rsync; subsequent → extra-packages install
        popen_idx = [0]

        def make_popen(cmd, **kwargs):
            popen_calls.append(cmd)
            mock_proc = MagicMock()
            mock_proc.stdout.readline.return_value = ""
            mock_proc.wait.return_value = None
            idx = popen_idx[0]
            popen_idx[0] += 1
            if idx == 0:
                mock_proc.returncode = rsync_returncode
            else:
                mock_proc.returncode = extras_returncode
            return mock_proc

        def mock_run(cmd, **kwargs):
            run_calls.append(cmd)
            return MagicMock(returncode=0)

        with (
            patch(
                "mados_installer.pages.installation.subprocess.Popen",
                side_effect=make_popen,
            ),
            patch(
                "mados_installer.pages.installation.subprocess.run",
                side_effect=mock_run,
            ),
            patch("mados_installer.pages.installation.set_progress"),
            patch("mados_installer.pages.installation.log_message"),
            patch("mados_installer.pages.installation.os.remove"),
            patch("builtins.open", MagicMock()),
        ):
            _rsync_rootfs_with_progress(app)

        return popen_calls, run_calls

    def test_rsync_invoked_with_correct_flags(self):
        """rsync must be called with -aAXH --info=progress2 --no-inc-recursive."""
        popen_calls, _ = self._run_rsync()
        rsync_cmd = popen_calls[0]
        self.assertEqual(rsync_cmd[0], "rsync")
        self.assertIn("-aAXH", rsync_cmd)
        self.assertIn("--info=progress2", rsync_cmd)
        self.assertIn("--no-inc-recursive", rsync_cmd)

    def test_rsync_copies_root_to_mnt(self):
        """rsync must copy from '/' to '/mnt/'."""
        popen_calls, _ = self._run_rsync()
        rsync_cmd = popen_calls[0]
        self.assertEqual(rsync_cmd[-2], "/")
        self.assertEqual(rsync_cmd[-1], "/mnt/")

    def test_all_excludes_are_passed(self):
        """Every RSYNC_EXCLUDES entry must be passed as --exclude."""
        popen_calls, _ = self._run_rsync()
        rsync_cmd = popen_calls[0]
        # Build the list of --exclude values from the command
        exclude_values = []
        for i, arg in enumerate(rsync_cmd):
            if arg == "--exclude" and i + 1 < len(rsync_cmd):
                exclude_values.append(rsync_cmd[i + 1])
        for exc in RSYNC_EXCLUDES:
            with self.subTest(exclude=exc):
                self.assertIn(
                    exc,
                    exclude_values,
                    f"RSYNC_EXCLUDES entry '{exc}' not found in rsync command",
                )

    def test_exclude_count_matches_config(self):
        """Number of --exclude flags must equal len(RSYNC_EXCLUDES)."""
        popen_calls, _ = self._run_rsync()
        rsync_cmd = popen_calls[0]
        exclude_count = rsync_cmd.count("--exclude")
        self.assertEqual(
            exclude_count,
            len(RSYNC_EXCLUDES),
            f"Expected {len(RSYNC_EXCLUDES)} --exclude flags, got {exclude_count}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Progress tracking
# ═══════════════════════════════════════════════════════════════════════════
class TestRsyncProgress(unittest.TestCase):
    """Verify progress updates during the rsync installation phase."""

    def test_progress_range_0_21_to_0_48(self):
        """Progress must stay within the 0.21 → 0.48 range."""
        app = MockApp()
        progress_values = []

        def capture_progress(app_arg, fraction, text):
            progress_values.append(fraction)

        # Simulate rsync output with percentage lines
        lines = [
            "          5,000  0%    0.00kB/s    0:00:00\n",
            "    100,000,000 25%  100.00MB/s    0:00:03\n",
            "    200,000,000 50%  100.00MB/s    0:00:02\n",
            "    300,000,000 75%  100.00MB/s    0:00:01\n",
            "    400,000,000 100% 100.00MB/s    0:00:00\n",
            "",  # EOF
        ]
        line_iter = iter(lines)

        mock_rsync = MagicMock()
        mock_rsync.stdout.readline.side_effect = lambda: next(line_iter)
        mock_rsync.returncode = 0
        mock_rsync.wait.return_value = None

        # Extra-packages Popen
        mock_extras = MagicMock()
        mock_extras.stdout.readline.return_value = ""
        mock_extras.returncode = 0
        mock_extras.wait.return_value = None

        call_idx = [0]

        def make_popen(cmd, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            return mock_rsync if idx == 0 else mock_extras

        with (
            patch(
                "mados_installer.pages.installation.subprocess.Popen",
                side_effect=make_popen,
            ),
            patch(
                "mados_installer.pages.installation.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
            patch(
                "mados_installer.pages.installation.set_progress",
                side_effect=capture_progress,
            ),
            patch("mados_installer.pages.installation.log_message"),
            patch("mados_installer.pages.installation.os.remove"),
            patch("builtins.open", MagicMock()),
        ):
            _rsync_rootfs_with_progress(app)

        self.assertGreater(
            len(progress_values), 0, "Should have recorded progress values"
        )
        for p in progress_values:
            self.assertGreaterEqual(p, 0.21, f"Progress {p} below start 0.21")
            self.assertLessEqual(p, 0.48, f"Progress {p} above end 0.48")

    def test_final_progress_is_0_48(self):
        """The last progress update must be exactly 0.48 (system ready)."""
        app = MockApp()
        progress_values = []

        def capture_progress(app_arg, fraction, text):
            progress_values.append(fraction)

        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with (
            patch(
                "mados_installer.pages.installation.subprocess.Popen",
                return_value=mock_proc,
            ),
            patch(
                "mados_installer.pages.installation.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
            patch(
                "mados_installer.pages.installation.set_progress",
                side_effect=capture_progress,
            ),
            patch("mados_installer.pages.installation.log_message"),
            patch("mados_installer.pages.installation.os.remove"),
            patch("builtins.open", MagicMock()),
        ):
            _rsync_rootfs_with_progress(app)

        self.assertAlmostEqual(
            progress_values[-1],
            0.48,
            places=5,
            msg="Final progress should be 0.48",
        )

    def test_initial_progress_is_0_21(self):
        """The first progress update must be 0.21 (start of rsync)."""
        app = MockApp()
        progress_values = []

        def capture_progress(app_arg, fraction, text):
            progress_values.append(fraction)

        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with (
            patch(
                "mados_installer.pages.installation.subprocess.Popen",
                return_value=mock_proc,
            ),
            patch(
                "mados_installer.pages.installation.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
            patch(
                "mados_installer.pages.installation.set_progress",
                side_effect=capture_progress,
            ),
            patch("mados_installer.pages.installation.log_message"),
            patch("mados_installer.pages.installation.os.remove"),
            patch("builtins.open", MagicMock()),
        ):
            _rsync_rootfs_with_progress(app)

        self.assertAlmostEqual(
            progress_values[0],
            0.21,
            places=5,
            msg="First progress should be 0.21",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Archiso cleanup
# ═══════════════════════════════════════════════════════════════════════════
class TestArchisoCleanup(unittest.TestCase):
    """Verify archiso-specific packages are removed after rsync."""

    def test_removes_mkinitcpio_archiso(self):
        """arch-chroot pacman -Rdd mkinitcpio-archiso must run after rsync."""
        app = MockApp()
        run_calls = []

        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        def capture_run(cmd, **kwargs):
            run_calls.append(cmd)
            return MagicMock(returncode=0)

        with (
            patch(
                "mados_installer.pages.installation.subprocess.Popen",
                return_value=mock_proc,
            ),
            patch(
                "mados_installer.pages.installation.subprocess.run",
                side_effect=capture_run,
            ),
            patch("mados_installer.pages.installation.set_progress"),
            patch("mados_installer.pages.installation.log_message"),
            patch("mados_installer.pages.installation.os.remove"),
            patch("builtins.open", MagicMock()),
        ):
            _rsync_rootfs_with_progress(app)

        # Find the arch-chroot pacman -Rdd call
        archiso_calls = [
            c for c in run_calls
            if "arch-chroot" in c and "mkinitcpio-archiso" in c
        ]
        self.assertEqual(
            len(archiso_calls), 1,
            "Must call arch-chroot to remove mkinitcpio-archiso exactly once",
        )
        cmd = archiso_calls[0]
        self.assertIn("-Rdd", cmd)
        self.assertIn("--noconfirm", cmd)

    def test_empties_machine_id(self):
        """machine-id must be emptied so systemd regenerates it on first boot."""
        app = MockApp()

        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        os_remove_calls = []
        open_calls = []

        def mock_os_remove(path):
            os_remove_calls.append(path)

        def mock_open(path, *args, **kwargs):
            open_calls.append(path)
            return MagicMock(__enter__=MagicMock(return_value=MagicMock()),
                             __exit__=MagicMock(return_value=False))

        with (
            patch(
                "mados_installer.pages.installation.subprocess.Popen",
                return_value=mock_proc,
            ),
            patch(
                "mados_installer.pages.installation.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
            patch("mados_installer.pages.installation.set_progress"),
            patch("mados_installer.pages.installation.log_message"),
            patch(
                "mados_installer.pages.installation.os.remove",
                side_effect=mock_os_remove,
            ),
            patch("builtins.open", side_effect=mock_open),
        ):
            _rsync_rootfs_with_progress(app)

        # Verify os.remove was called for machine-id
        machine_id_removes = [p for p in os_remove_calls if "machine-id" in p]
        self.assertGreater(
            len(machine_id_removes), 0,
            "Must call os.remove on /mnt/etc/machine-id",
        )

        # Verify open() was called to create an empty machine-id file
        machine_id_opens = [p for p in open_calls if "machine-id" in str(p)]
        self.assertGreater(
            len(machine_id_opens), 0,
            "Must create an empty /mnt/etc/machine-id file",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Rsync exit code handling
# ═══════════════════════════════════════════════════════════════════════════
class TestRsyncExitCodes(unittest.TestCase):
    """Verify rsync exit codes are handled correctly."""

    def _run_with_returncode(self, returncode):
        """Run _rsync_rootfs_with_progress with a specific rsync return code."""
        app = MockApp()

        mock_rsync = MagicMock()
        mock_rsync.stdout.readline.return_value = ""
        mock_rsync.returncode = returncode
        mock_rsync.wait.return_value = None

        mock_extras = MagicMock()
        mock_extras.stdout.readline.return_value = ""
        mock_extras.returncode = 0
        mock_extras.wait.return_value = None

        call_idx = [0]

        def make_popen(cmd, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            return mock_rsync if idx == 0 else mock_extras

        with (
            patch(
                "mados_installer.pages.installation.subprocess.Popen",
                side_effect=make_popen,
            ),
            patch(
                "mados_installer.pages.installation.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
            patch("mados_installer.pages.installation.set_progress"),
            patch("mados_installer.pages.installation.log_message"),
            patch("mados_installer.pages.installation.os.remove"),
            patch("builtins.open", MagicMock()),
        ):
            _rsync_rootfs_with_progress(app)

    def test_exit_code_0_succeeds(self):
        """rsync exit code 0 (success) should not raise."""
        self._run_with_returncode(0)  # Should not raise

    def test_exit_code_24_treated_as_success(self):
        """rsync exit code 24 (vanished source files) should not raise."""
        self._run_with_returncode(24)  # Should not raise

    def test_exit_code_1_raises(self):
        """rsync exit code 1 (generic error) must raise CalledProcessError."""
        with self.assertRaises(subprocess.CalledProcessError) as ctx:
            self._run_with_returncode(1)
        self.assertEqual(ctx.exception.returncode, 1)

    def test_exit_code_23_raises(self):
        """rsync exit code 23 (partial transfer) must raise CalledProcessError."""
        with self.assertRaises(subprocess.CalledProcessError) as ctx:
            self._run_with_returncode(23)
        self.assertEqual(ctx.exception.returncode, 23)

    def test_exit_code_12_raises(self):
        """rsync exit code 12 (protocol error) must raise CalledProcessError."""
        with self.assertRaises(subprocess.CalledProcessError) as ctx:
            self._run_with_returncode(12)
        self.assertEqual(ctx.exception.returncode, 12)

    def test_exit_code_130_raises(self):
        """rsync exit code 130 (interrupted) must raise CalledProcessError."""
        with self.assertRaises(subprocess.CalledProcessError) as ctx:
            self._run_with_returncode(130)
        self.assertEqual(ctx.exception.returncode, 130)


if __name__ == "__main__":
    unittest.main()
