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
import unittest
from unittest.mock import patch, MagicMock, call

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so installer modules can be imported headlessly.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import install_gtk_mocks
install_gtk_mocks()

# ---------------------------------------------------------------------------
# Add installer lib to path and import
# ---------------------------------------------------------------------------
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "airootfs", "usr", "local", "lib")
)

from mados_installer.pages.installation import _rsync_rootfs_with_progress
from mados_installer.config import RSYNC_EXCLUDES

# ---------------------------------------------------------------------------
# Shared test helpers — extracted to reduce code duplication.
# ---------------------------------------------------------------------------
_MOD = "mados_installer.pages.installation"


class MockApp:
    """Minimal mock of the GTK application object used by the installer."""

    def __init__(self):
        self.progress_bar = MagicMock()
        self.status_label = MagicMock()
        self.log_buffer = MagicMock()
        self.log_scrolled = MagicMock()


def _make_mock_proc(returncode=0, stdout_lines=None):
    """Create a mock subprocess with preconfigured stdout and return code."""
    proc = MagicMock()
    if stdout_lines is not None:
        it = iter(stdout_lines)
        proc.stdout.readline.side_effect = lambda: next(it)
    else:
        proc.stdout.readline.return_value = ""
    proc.returncode = returncode
    proc.wait.return_value = None
    return proc


def _make_popen_dispatcher(mock_first, mock_rest):
    """Return a Popen side_effect: first call → *mock_first*, rest → *mock_rest*."""
    call_idx = [0]

    def dispatcher(cmd, **kwargs):
        idx = call_idx[0]
        call_idx[0] += 1
        return mock_first if idx == 0 else mock_rest

    return dispatcher


def _patched_rsync_run(app, *, popen_kw, run_kw,
                       set_progress_kw=None, os_remove_kw=None,
                       open_kw=None):
    """Execute ``_rsync_rootfs_with_progress`` with standard patches applied.

    The six mandatory patch targets are always installed; only the keyword
    arguments forwarded to each ``patch()`` call vary between tests.
    """
    open_patch = (patch("builtins.open", **open_kw) if open_kw is not None
                  else patch("builtins.open", MagicMock()))
    with (
        patch(f"{_MOD}.subprocess.Popen", **popen_kw),
        patch(f"{_MOD}.subprocess.run", **run_kw),
        patch(f"{_MOD}.set_progress", **(set_progress_kw or {})),
        patch(f"{_MOD}.log_message"),
        patch(f"{_MOD}.os.remove", **(os_remove_kw or {})),
        open_patch,
    ):
        _rsync_rootfs_with_progress(app)


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

        popen_idx = [0]

        def make_popen(cmd, **kwargs):
            popen_calls.append(cmd)
            idx = popen_idx[0]
            popen_idx[0] += 1
            rc = rsync_returncode if idx == 0 else extras_returncode
            return _make_mock_proc(returncode=rc)

        def mock_run(cmd, **kwargs):
            run_calls.append(cmd)
            return MagicMock(returncode=0)

        _patched_rsync_run(
            app,
            popen_kw={"side_effect": make_popen},
            run_kw={"side_effect": mock_run},
        )
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

    def _capture_progress(self, *, rsync_stdout_lines=None):
        """Run the rsync flow and return the list of recorded progress fractions."""
        progress_values = []

        def on_progress(app_arg, fraction, text):
            progress_values.append(fraction)

        mock_rsync = _make_mock_proc(stdout_lines=rsync_stdout_lines)
        dispatcher = _make_popen_dispatcher(mock_rsync, _make_mock_proc())

        app = MockApp()
        _patched_rsync_run(
            app,
            popen_kw={"side_effect": dispatcher},
            run_kw={"return_value": MagicMock(returncode=0)},
            set_progress_kw={"side_effect": on_progress},
        )
        return progress_values

    def test_progress_range_0_21_to_0_48(self):
        """Progress must stay within the 0.21 → 0.48 range."""
        lines = [
            "          5,000  0%    0.00kB/s    0:00:00\n",
            "    100,000,000 25%  100.00MB/s    0:00:03\n",
            "    200,000,000 50%  100.00MB/s    0:00:02\n",
            "    300,000,000 75%  100.00MB/s    0:00:01\n",
            "    400,000,000 100% 100.00MB/s    0:00:00\n",
            "",  # EOF
        ]
        progress_values = self._capture_progress(rsync_stdout_lines=lines)

        self.assertGreater(
            len(progress_values), 0, "Should have recorded progress values"
        )
        for p in progress_values:
            self.assertGreaterEqual(p, 0.21, f"Progress {p} below start 0.21")
            self.assertLessEqual(p, 0.48, f"Progress {p} above end 0.48")

    def test_final_progress_is_0_48(self):
        """The last progress update must be exactly 0.48 (system ready)."""
        progress_values = self._capture_progress()
        self.assertAlmostEqual(
            progress_values[-1],
            0.48,
            places=5,
            msg="Final progress should be 0.48",
        )

    def test_initial_progress_is_0_21(self):
        """The first progress update must be 0.21 (start of rsync)."""
        progress_values = self._capture_progress()
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
        run_calls = []

        def capture_run(cmd, **kwargs):
            run_calls.append(cmd)
            return MagicMock(returncode=0)

        app = MockApp()
        _patched_rsync_run(
            app,
            popen_kw={"return_value": _make_mock_proc()},
            run_kw={"side_effect": capture_run},
        )

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
        os_remove_calls = []
        open_calls = []

        def mock_os_remove(path):
            os_remove_calls.append(path)

        def mock_open(path, *args, **kwargs):
            open_calls.append(path)
            return MagicMock(__enter__=MagicMock(return_value=MagicMock()),
                             __exit__=MagicMock(return_value=False))

        app = MockApp()
        _patched_rsync_run(
            app,
            popen_kw={"return_value": _make_mock_proc()},
            run_kw={"return_value": MagicMock(returncode=0)},
            os_remove_kw={"side_effect": mock_os_remove},
            open_kw={"side_effect": mock_open},
        )

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
        dispatcher = _make_popen_dispatcher(
            _make_mock_proc(returncode), _make_mock_proc()
        )
        app = MockApp()
        _patched_rsync_run(
            app,
            popen_kw={"side_effect": dispatcher},
            run_kw={"return_value": MagicMock(returncode=0)},
        )

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
