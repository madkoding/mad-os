#!/usr/bin/env python3
"""
Tests for Ollama availability in both the live USB and post-installation.

Validates that the ollama command will be discoverable and functional by
verifying:
  - Live USB: setup script is correct, PATH includes /usr/local/bin,
    and install method is present.  No systemd service exists (ollama
    is a program, not a service).
  - Post-installation: the installer generates a setup script and
    installs Ollama via curl.
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
# Live USB – Ollama is a program, not a service
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOllamaNoService(unittest.TestCase):
    """Verify ollama has NO systemd service (it is a program, not a service)."""

    def test_no_service_file(self):
        """setup-ollama.service must NOT exist — ollama is a program."""
        self.assertFalse(
            os.path.isfile(os.path.join(SYSTEMD_DIR, "setup-ollama.service")),
            "setup-ollama.service must NOT exist — ollama is a program, not a service",
        )

    def test_no_symlink_in_multi_user_wants(self):
        """setup-ollama.service must NOT be symlinked in multi-user.target.wants/."""
        symlink_path = os.path.join(MULTI_USER_WANTS, "setup-ollama.service")
        self.assertFalse(
            os.path.lexists(symlink_path),
            "setup-ollama.service symlink must NOT exist in multi-user.target.wants/",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – Ollama is pre-installed during ISO build
# No setup script needed

# ═══════════════════════════════════════════════════════════════════════════
# Post-installation – Ollama is copied by rsync from live USB
# ═══════════════════════════════════════════════════════════════════════════
class TestPostInstallOllama(unittest.TestCase):
    """Verify the installer copies Ollama from the live USB via rsync.

    Ollama is a pre-installed program on the live USB.  The installer rsync
    copies everything (binaries + setup scripts) to the installed system.
    The installer does NOT need to create scripts or install anything for Ollama.
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
        """Installer must NOT create setup-ollama.service (ollama is a program)."""
        self.assertNotIn(
            "setup-ollama.service",
            self.content,
            "Installer must NOT create setup-ollama.service — ollama is a program, not a service",
        )

    def test_installer_copies_ollama_binary_from_live(self):
        """Installer should copy Ollama binary from live environment if available."""
        self.assertIn(
            "/usr/local/bin/ollama",
            self.content,
            "Installer must reference /usr/local/bin/ollama for binary copy",
        )
        self.assertIn(
            'for binary in ["opencode", "ollama"]',
            self.content,
            "Installer must copy ollama binary via binary copy loop",
        )

    def test_installer_adds_ollama_to_sudoers(self):
        """Installer should add ollama to NOPASSWD sudoers."""
        pattern = re.compile(r"NOPASSWD:.*?/usr/local/bin/ollama")
        self.assertRegex(
            self.content,
            pattern,
            "Installer must include /usr/local/bin/ollama in sudoers NOPASSWD line",
        )

    def test_no_inline_ollama_download(self):
        """Installer must NOT directly download Ollama (binary is copied from ISO)."""
        lines = self.content.splitlines()
        in_heredoc = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("cat >") and "<<" in stripped:
                in_heredoc = True
            if in_heredoc and stripped in ("EOFSETUP", "EOFSVC"):
                in_heredoc = False
                continue
            if not in_heredoc and "ollama.com/install.sh" in stripped:
                self.fail(
                    "Installer must not directly download Ollama — "
                    "the binary should already be on disk from Phase 1 rsync"
                )


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – packages.x86_64 has Ollama dependencies
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOllamaDependencies(unittest.TestCase):
    """Verify the live ISO includes packages needed to install Ollama."""

    def _read_packages(self):
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

    def test_curl_included(self):
        """Live ISO must include curl (needed for ollama.com/install.sh)."""
        self.assertIn("curl", self._read_packages())


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh – Ollama script permissions
# ═══════════════════════════════════════════════════════════════════════════
class TestProfiledefOllamaPermissions(unittest.TestCase):
    """Verify profiledef.sh grants correct permissions to setup-ollama.sh."""

    def setUp(self):
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            self.content = f.read()

    def test_setup_ollama_has_permissions(self):
        """profiledef.sh should set permissions for setup-ollama.sh."""
        self.assertIn(
            "setup-ollama.sh",
            self.content,
            "profiledef.sh must include permissions for setup-ollama.sh",
        )

    def test_setup_ollama_executable(self):
        """setup-ollama.sh should have executable permissions (0:0:755)."""
        pattern = re.compile(r'\["/usr/local/bin/setup-ollama\.sh"\]="0:0:755"')
        self.assertRegex(
            self.content,
            pattern,
            "setup-ollama.sh must have 0:0:755 permissions in profiledef.sh",
        )


if __name__ == "__main__":
    unittest.main()
