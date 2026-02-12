#!/usr/bin/env python3
"""
Tests for OpenCode availability in both the live USB and post-installation.

Validates that the opencode command will be discoverable and functional by
verifying:
  - Live USB: systemd service is enabled (symlinked), script is correct,
    PATH includes /usr/local/bin, and install methods are present.
  - Post-installation: the installer generates a setup script, enables the
    fallback service, configures sudoers, and installs OpenCode via
    curl + npm fallback.
"""

import os
import re
import sys
import types
import unittest

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

sys.modules.setdefault("gi", gi_mock)
sys.modules.setdefault("gi.repository", repo_mock)

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
# Live USB – OpenCode service enablement
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOpenCodeServiceEnabled(unittest.TestCase):
    """Verify setup-opencode.service is enabled (symlinked) for the live USB."""

    def test_symlink_exists_in_multi_user_wants(self):
        """setup-opencode.service must be symlinked in multi-user.target.wants/."""
        symlink_path = os.path.join(MULTI_USER_WANTS, "setup-opencode.service")
        self.assertTrue(
            os.path.lexists(symlink_path),
            "setup-opencode.service symlink missing from multi-user.target.wants/ "
            "– the service will never run at boot and opencode won't be installed",
        )

    def test_symlink_points_to_correct_service(self):
        """The symlink must point to /etc/systemd/system/setup-opencode.service."""
        symlink_path = os.path.join(MULTI_USER_WANTS, "setup-opencode.service")
        if not os.path.lexists(symlink_path):
            self.skipTest("symlink does not exist")
        target = os.readlink(symlink_path)
        self.assertEqual(
            target,
            "/etc/systemd/system/setup-opencode.service",
            f"Symlink points to '{target}' instead of "
            "'/etc/systemd/system/setup-opencode.service'",
        )

    def test_no_broken_claude_code_symlink(self):
        """Ensure no stale setup-claude-code.service symlink exists."""
        stale = os.path.join(MULTI_USER_WANTS, "setup-claude-code.service")
        self.assertFalse(
            os.path.lexists(stale),
            "Stale setup-claude-code.service symlink found in "
            "multi-user.target.wants/ – this should have been replaced "
            "by setup-opencode.service",
        )

    def test_service_file_exists(self):
        """The actual setup-opencode.service unit file must exist."""
        self.assertTrue(
            os.path.isfile(os.path.join(SYSTEMD_DIR, "setup-opencode.service")),
            "setup-opencode.service unit file is missing from systemd/system/",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – setup-opencode.sh script correctness
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOpenCodeScript(unittest.TestCase):
    """Verify setup-opencode.sh will install opencode correctly."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-opencode.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_installs_to_usr_local_bin(self):
        """OpenCode should be installed to /usr/local/bin (in PATH)."""
        self.assertIn(
            "/usr/local/bin", self.content,
            "setup-opencode.sh must install to /usr/local/bin so the "
            "binary is in PATH",
        )

    def test_curl_method_before_npm_fallback(self):
        """Curl install method must appear before npm fallback."""
        curl_pos = self.content.find("opencode.ai/install")
        npm_pos = self.content.find("npm install")
        self.assertNotEqual(curl_pos, -1, "Must have curl install method")
        self.assertNotEqual(npm_pos, -1, "Must have npm fallback method")
        self.assertLess(
            curl_pos, npm_pos,
            "Curl install must be tried before npm fallback",
        )

    def test_verifies_opencode_after_install(self):
        """Script should verify opencode is available after each install method."""
        # The script uses $OPENCODE_CMD variable (set to "opencode") with command -v
        checks = re.findall(r'command -v.*(?:opencode|\$OPENCODE_CMD)', self.content)
        self.assertGreaterEqual(
            len(checks), 2,
            "Script must verify opencode availability after both "
            "curl and npm install methods",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – systemd service PATH configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOpenCodeServiceConfig(unittest.TestCase):
    """Verify the systemd service has the right PATH so opencode is found."""

    def setUp(self):
        service_path = os.path.join(SYSTEMD_DIR, "setup-opencode.service")
        with open(service_path) as f:
            self.content = f.read()

    def test_path_includes_usr_local_bin(self):
        """Service PATH must include /usr/local/bin where opencode is installed."""
        path_match = re.search(r'Environment=PATH=(.*)', self.content)
        self.assertIsNotNone(path_match, "Service must set PATH environment")
        self.assertIn(
            "/usr/local/bin", path_match.group(1),
            "Service PATH must include /usr/local/bin",
        )

    def test_runs_after_network(self):
        """Service must run after network is available (needs internet to install)."""
        self.assertIn(
            "network-online.target", self.content,
            "Service must start after network-online.target",
        )

    def test_runs_after_pacman_init(self):
        """Service must run after pacman-init to ensure keyrings are ready."""
        self.assertIn(
            "pacman-init.service", self.content,
            "Service must start after pacman-init.service",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Post-installation – OpenCode setup in first-boot script
# ═══════════════════════════════════════════════════════════════════════════
class TestPostInstallOpenCode(unittest.TestCase):
    """Verify the installer configures OpenCode for the installed system."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_installer_installs_opencode_via_curl(self):
        """Installer must attempt to install OpenCode via curl (primary)."""
        self.assertIn(
            "opencode.ai/install", self.content,
            "Installer must try curl install from opencode.ai",
        )

    def test_installer_installs_opencode_via_npm_fallback(self):
        """Installer must fall back to npm if curl fails."""
        self.assertIn(
            "npm install -g", self.content,
            "Installer must fall back to npm install -g",
        )
        self.assertIn(
            "opencode-ai", self.content,
            "Installer must install opencode-ai npm package",
        )

    def test_installer_creates_setup_script(self):
        """Installer must create setup-opencode.sh for manual retry."""
        self.assertIn(
            "setup-opencode.sh", self.content,
            "Installer must create setup-opencode.sh on the installed system",
        )

    def test_installer_creates_fallback_service(self):
        """Installer must create setup-opencode.service for boot-time retry."""
        self.assertIn(
            "setup-opencode.service", self.content,
            "Installer must create setup-opencode.service on the installed system",
        )

    def test_installer_enables_fallback_service(self):
        """Installer must enable setup-opencode.service on the installed system."""
        self.assertIn(
            "systemctl enable setup-opencode.service", self.content,
            "Installer must enable setup-opencode.service",
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

    def test_installer_verifies_opencode_after_install(self):
        """Installer should check if opencode is available after install."""
        self.assertIn(
            "command -v opencode", self.content,
            "Installer must verify opencode is available after install",
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

    def test_npm_included(self):
        """Live ISO must include npm (needed for npm fallback install)."""
        packages = self._read_packages()
        has_npm = "npm" in packages or "nodejs" in packages
        self.assertTrue(
            has_npm,
            "Live ISO must include npm or nodejs for OpenCode npm fallback",
        )


if __name__ == "__main__":
    unittest.main()
