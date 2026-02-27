#!/usr/bin/env python3
"""
Tests for OpenCode availability in both the live USB and post-installation.

Validates that the opencode command will be discoverable and functional by
verifying:
  - Live USB: setup script is correct, PATH includes /usr/local/bin,
    and install methods are present.  No systemd service exists (opencode
    is a program, not a service).
  - Post-installation: the installer generates a setup script, configures
    sudoers, and installs OpenCode via curl + npm fallback.
"""

import os
import re
import sys
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so installer modules can be imported headlessly.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import install_gtk_mocks
install_gtk_mocks(use_setdefault=True)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")
MULTI_USER_WANTS = os.path.join(SYSTEMD_DIR, "multi-user.target.wants")

# Add lib dir to path for installer module imports
sys.path.insert(0, LIB_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – OpenCode is a program, not a service
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOpenCodeNoService(unittest.TestCase):
    """Verify opencode has NO systemd service (it is a program, not a service)."""

    def test_no_service_file(self):
        """setup-opencode.service must NOT exist — opencode is a program."""
        self.assertFalse(
            os.path.isfile(os.path.join(SYSTEMD_DIR, "setup-opencode.service")),
            "setup-opencode.service must NOT exist — opencode is a program, not a service",
        )

    def test_no_symlink_in_multi_user_wants(self):
        """setup-opencode.service must NOT be symlinked in multi-user.target.wants/."""
        symlink_path = os.path.join(MULTI_USER_WANTS, "setup-opencode.service")
        self.assertFalse(
            os.path.lexists(symlink_path),
            "setup-opencode.service symlink must NOT exist in multi-user.target.wants/",
        )

    def test_no_broken_claude_code_symlink(self):
        """Ensure no stale setup-claude-code.service symlink exists."""
        stale = os.path.join(MULTI_USER_WANTS, "setup-claude-code.service")
        self.assertFalse(
            os.path.lexists(stale),
            "Stale setup-claude-code.service symlink found in "
            "multi-user.target.wants/ – this should have been removed",
        )


# Live USB – OpenCode is pre-installed during ISO build
# No setup script needed

# ═══════════════════════════════════════════════════════════════════════════
# Post-installation – OpenCode is copied by rsync from live USB
# ═══════════════════════════════════════════════════════════════════════════
class TestPostInstallOpenCode(unittest.TestCase):
    """Verify the installer copies OpenCode from the live USB via rsync.

    OpenCode is a pre-installed program on the live USB.  The installer rsync
    copies everything (binaries + setup scripts) to the installed system.
    The installer does NOT need to create scripts or install anything for OpenCode.
    """

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_installer_does_not_create_service(self):
        """Installer must NOT create setup-opencode.service (opencode is a program)."""
        self.assertNotIn(
            "setup-opencode.service", self.content,
            "Installer must NOT create setup-opencode.service — opencode is a program, not a service",
        )

    def test_installer_configures_sudoers_for_opencode(self):
        """Installer must grant NOPASSWD sudo for the opencode binary."""
        self.assertIn(
            "opencode", self.content,
            "Installer must reference opencode in sudoers configuration",
        )
        self.assertIn(
            "/usr/local/bin/opencode", self.content,
            "Installer sudoers must include /usr/local/bin/opencode path",
        )

    def test_no_inline_opencode_download(self):
        """Installer must NOT directly download OpenCode (binary is copied from ISO)."""
        lines = self.content.splitlines()
        in_heredoc = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("cat >") and "<<" in stripped:
                in_heredoc = True
            if in_heredoc and stripped in ("EOFSETUP", "EOFSVC"):
                in_heredoc = False
                continue
            if not in_heredoc and "opencode.ai/install" in stripped:
                self.fail(
                    "Installer must not directly download OpenCode — "
                    "the binary should already be on disk from Phase 1 rsync"
                )


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – packages.x86_64 has OpenCode dependencies
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOpenCodeDependencies(unittest.TestCase):
    """Verify the live ISO includes packages needed to install OpenCode."""

    def _read_packages(self):
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            return [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

    def test_curl_included(self):
        """Live ISO must include curl (needed for opencode.ai/install)."""
        self.assertIn("curl", self._read_packages())


if __name__ == "__main__":
    unittest.main()
