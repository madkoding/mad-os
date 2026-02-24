#!/usr/bin/env python3
"""
Tests for ONLYOFFICE Desktop Editors availability in both the live USB and
post-installation.

Validates that the ONLYOFFICE AppImage will be discoverable and functional by
verifying:
  - Live USB: systemd service is enabled (symlinked), script is correct,
    PATH includes /usr/local/bin, and install method is present.
  - Post-installation: the installer generates a setup script, enables the
    fallback service, and installs ONLYOFFICE via GitHub download.
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
# Live USB – ONLYOFFICE service enablement
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOnlyofficeServiceEnabled(unittest.TestCase):
    """Verify setup-onlyoffice.service is enabled (symlinked) for the live USB."""

    def test_symlink_exists_in_multi_user_wants(self):
        """setup-onlyoffice.service must be symlinked in multi-user.target.wants/."""
        symlink_path = os.path.join(MULTI_USER_WANTS, "setup-onlyoffice.service")
        self.assertTrue(
            os.path.lexists(symlink_path),
            "setup-onlyoffice.service symlink missing from multi-user.target.wants/ "
            "– the service will never run at boot and ONLYOFFICE won't be installed",
        )

    def test_symlink_points_to_correct_service(self):
        """The symlink must point to /etc/systemd/system/setup-onlyoffice.service."""
        symlink_path = os.path.join(MULTI_USER_WANTS, "setup-onlyoffice.service")
        if not os.path.lexists(symlink_path):
            self.skipTest("symlink does not exist")
        target = os.readlink(symlink_path)
        self.assertEqual(
            target,
            "/etc/systemd/system/setup-onlyoffice.service",
            f"Symlink points to '{target}' instead of "
            "'/etc/systemd/system/setup-onlyoffice.service'",
        )

    def test_service_file_exists(self):
        """The actual setup-onlyoffice.service unit file must exist."""
        self.assertTrue(
            os.path.isfile(os.path.join(SYSTEMD_DIR, "setup-onlyoffice.service")),
            "setup-onlyoffice.service unit file is missing from systemd/system/",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – setup-onlyoffice.sh script correctness
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOnlyofficeScript(unittest.TestCase):
    """Verify setup-onlyoffice.sh will install ONLYOFFICE correctly."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-onlyoffice.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_script_exists(self):
        """setup-onlyoffice.sh must exist."""
        self.assertTrue(os.path.isfile(self.script_path))

    def test_uses_github_download_url(self):
        """Script must use GitHub download URL for ONLYOFFICE DesktopEditors."""
        self.assertIn(
            "ONLYOFFICE/DesktopEditors",
            self.content,
            "setup-onlyoffice.sh must use GitHub URL containing "
            "ONLYOFFICE/DesktopEditors",
        )

    def test_checks_connectivity(self):
        """Script should check internet before attempting download."""
        self.assertIn("curl", self.content)

    def test_graceful_exit_on_no_network(self):
        """Script should exit 0 (not fail) when network is unavailable."""
        self.assertIn("exit 0", self.content)

    def test_has_shebang(self):
        """setup-onlyoffice.sh must start with a bash shebang."""
        with open(self.script_path) as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith("#!"))
        self.assertIn("bash", first_line)


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – systemd service configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOnlyofficeServiceConfig(unittest.TestCase):
    """Verify the systemd service has the right PATH so ONLYOFFICE is found."""

    def setUp(self):
        service_path = os.path.join(SYSTEMD_DIR, "setup-onlyoffice.service")
        with open(service_path) as f:
            self.content = f.read()

    def test_path_includes_usr_local_bin(self):
        """Service PATH must include /usr/local/bin where the wrapper is installed."""
        path_match = re.search(r"Environment=PATH=(.*)", self.content)
        self.assertIsNotNone(path_match, "Service must set PATH environment")
        self.assertIn(
            "/usr/local/bin",
            path_match.group(1),
            "Service PATH must include /usr/local/bin",
        )

    def test_runs_after_network(self):
        """Service must run after network is available (needs internet to download)."""
        self.assertIn(
            "network-online.target",
            self.content,
            "Service must start after network-online.target",
        )

    def test_has_timeout(self):
        """Service must have a timeout to prevent hangs."""
        self.assertIn(
            "TimeoutStartSec=",
            self.content,
            "Service must have a TimeoutStartSec",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Post-installation – ONLYOFFICE setup in installer
# ═══════════════════════════════════════════════════════════════════════════
class TestPostInstallOnlyoffice(unittest.TestCase):
    """Verify the installer configures ONLYOFFICE for the installed system."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_installer_downloads_onlyoffice_appimage(self):
        """Installer must reference ONLYOFFICE AppImage download URL."""
        self.assertIn(
            "ONLYOFFICE/DesktopEditors",
            self.content,
            "Installer must reference GitHub ONLYOFFICE/DesktopEditors download URL",
        )

    def test_installer_creates_setup_script(self):
        """Installer must create setup-onlyoffice.sh for manual retry."""
        self.assertIn(
            "setup-onlyoffice.sh",
            self.content,
            "Installer must create setup-onlyoffice.sh on the installed system",
        )

    def test_installer_creates_fallback_service(self):
        """Installer must create setup-onlyoffice.service for boot-time retry."""
        self.assertIn(
            "setup-onlyoffice.service",
            self.content,
            "Installer must create setup-onlyoffice.service on the installed system",
        )

    def test_installer_enables_fallback_service(self):
        """Installer must enable setup-onlyoffice.service on the installed system."""
        self.assertIn(
            "systemctl enable setup-onlyoffice.service",
            self.content,
            "Installer must enable setup-onlyoffice.service",
        )

    def test_installer_creates_desktop_entry(self):
        """Installer must create .desktop entry for ONLYOFFICE."""
        self.assertIn(
            "onlyoffice-desktopeditors.desktop",
            self.content,
            "Installer must create onlyoffice-desktopeditors.desktop",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Live USB – packages.x86_64 has fuse2 (needed for AppImage)
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveUSBOnlyofficeDependencies(unittest.TestCase):
    """Verify the live ISO includes packages needed to run ONLYOFFICE AppImage."""

    def _read_packages(self):
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

    def test_fuse2_included(self):
        """Live ISO must include fuse2 (needed for AppImage execution)."""
        self.assertIn("fuse2", self._read_packages())


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh – ONLYOFFICE script permissions
# ═══════════════════════════════════════════════════════════════════════════
class TestProfiledefOnlyofficePermissions(unittest.TestCase):
    """Verify profiledef.sh grants correct permissions to setup-onlyoffice.sh."""

    def setUp(self):
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            self.content = f.read()

    def test_setup_onlyoffice_has_permissions(self):
        """profiledef.sh should set permissions for setup-onlyoffice.sh."""
        self.assertIn(
            "setup-onlyoffice.sh",
            self.content,
            "profiledef.sh must include permissions for setup-onlyoffice.sh",
        )

    def test_setup_onlyoffice_executable(self):
        """setup-onlyoffice.sh should have executable permissions (0:0:755)."""
        pattern = re.compile(r'\["/usr/local/bin/setup-onlyoffice\.sh"\]="0:0:755"')
        self.assertRegex(
            self.content,
            pattern,
            "setup-onlyoffice.sh must have 0:0:755 permissions in profiledef.sh",
        )


if __name__ == "__main__":
    unittest.main()
