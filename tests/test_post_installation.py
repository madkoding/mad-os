#!/usr/bin/env python3
"""
Tests for madOS post-installation configuration.

Validates that the installed system will be correctly configured by verifying
the installer configuration files, system config templates, and package lists
that are applied during and after installation.

These tests run in CI without requiring an actual installation – they verify
the source files in the repository are consistent and correct.
"""

import os
import re
import subprocess
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

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")

# Add lib dir to path for imports
sys.path.insert(0, LIB_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# Installer Python modules syntax validation
# ═══════════════════════════════════════════════════════════════════════════
class TestInstallerModuleSyntax(unittest.TestCase):
    """Verify all installer Python modules have valid syntax."""

    def test_all_installer_modules_compile(self):
        """Every .py file in mados_installer/ should compile without errors."""
        installer_dir = os.path.join(LIB_DIR, "mados_installer")
        if not os.path.isdir(installer_dir):
            self.skipTest("mados_installer directory not found")

        for root, _, files in os.walk(installer_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, LIB_DIR)
                with self.subTest(module=rel):
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", fpath],
                        capture_output=True, text=True,
                    )
                    self.assertEqual(
                        result.returncode, 0,
                        f"Syntax error in {rel}: {result.stderr}",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Installer package list
# ═══════════════════════════════════════════════════════════════════════════
class TestInstallerPackages(unittest.TestCase):
    """Verify the installer's package list includes essential packages."""

    ESSENTIAL_PACKAGES = [
        "base",
        "linux",
        "grub",
        "zsh",
        "sudo",
        "networkmanager",
        "earlyoom",
    ]

    def test_config_packages_importable(self):
        """Installer config module should be importable."""
        from mados_installer.config import PACKAGES
        self.assertIsInstance(PACKAGES, (list, tuple))
        self.assertGreater(len(PACKAGES), 0, "PACKAGES must not be empty")

    def test_essential_packages_present(self):
        """PACKAGES must include all essential system packages."""
        from mados_installer.config import PACKAGES
        for pkg in self.ESSENTIAL_PACKAGES:
            with self.subTest(package=pkg):
                self.assertIn(
                    pkg, PACKAGES,
                    f"Essential package '{pkg}' missing from installer PACKAGES",
                )

    def test_zram_generator_included(self):
        """PACKAGES should include zram-generator for RAM optimization."""
        from mados_installer.config import PACKAGES
        self.assertIn(
            "zram-generator", PACKAGES,
            "zram-generator must be in PACKAGES for low-RAM optimization",
        )

    def test_phase1_packages_exist(self):
        """PACKAGES_PHASE1 must exist and contain essential boot packages."""
        from mados_installer.config import PACKAGES_PHASE1
        self.assertIsInstance(PACKAGES_PHASE1, (list, tuple))
        self.assertGreater(len(PACKAGES_PHASE1), 0, "PACKAGES_PHASE1 must not be empty")
        for pkg in self.ESSENTIAL_PACKAGES:
            with self.subTest(package=pkg):
                self.assertIn(
                    pkg, PACKAGES_PHASE1,
                    f"Essential package '{pkg}' must be in PACKAGES_PHASE1 for Phase 1 install",
                )

    def test_phase2_packages_exist(self):
        """PACKAGES_PHASE2 must exist and contain desktop/app packages."""
        from mados_installer.config import PACKAGES_PHASE2
        self.assertIsInstance(PACKAGES_PHASE2, (list, tuple))
        self.assertGreater(len(PACKAGES_PHASE2), 0, "PACKAGES_PHASE2 must not be empty")

    def test_combined_packages_equal_phases(self):
        """PACKAGES must be the combination of PACKAGES_PHASE1 + PACKAGES_PHASE2."""
        from mados_installer.config import PACKAGES, PACKAGES_PHASE1, PACKAGES_PHASE2
        self.assertEqual(
            PACKAGES, PACKAGES_PHASE1 + PACKAGES_PHASE2,
            "PACKAGES must equal PACKAGES_PHASE1 + PACKAGES_PHASE2",
        )

    def test_first_boot_script_in_installation(self):
        """installation.py must contain first-boot service setup."""
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        with open(install_py) as f:
            content = f.read()
        self.assertIn(
            "mados-first-boot", content,
            "installation.py must set up the mados-first-boot service",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Live ISO package list (packages.x86_64)
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveISOPackages(unittest.TestCase):
    """Verify packages.x86_64 includes essential packages for the live ISO."""

    def _read_packages(self):
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            return [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

    def test_zsh_included(self):
        """Live ISO must include zsh (default shell for mados user)."""
        self.assertIn("zsh", self._read_packages())

    def test_git_included(self):
        """Live ISO must include git (needed by setup-ohmyzsh.sh)."""
        self.assertIn("git", self._read_packages())

    def test_nodejs_or_npm_included(self):
        """Live ISO must include nodejs (needed by setup-opencode.sh)."""
        packages = self._read_packages()
        has_node = "nodejs" in packages or "npm" in packages
        self.assertTrue(
            has_node,
            "Live ISO must include nodejs or npm for OpenCode setup",
        )

    def test_sway_included(self):
        """Live ISO must include sway compositor."""
        self.assertIn("sway", self._read_packages())

    def test_earlyoom_included(self):
        """Live ISO must include earlyoom for low-RAM protection."""
        self.assertIn("earlyoom", self._read_packages())


# ═══════════════════════════════════════════════════════════════════════════
# System configuration files (templates applied post-install)
# ═══════════════════════════════════════════════════════════════════════════
class TestSystemConfigFiles(unittest.TestCase):
    """Verify system configuration files exist and are properly formatted."""

    def test_zram_config_exists(self):
        """ZRAM generator config must exist."""
        path = os.path.join(AIROOTFS, "etc", "systemd", "zram-generator.conf")
        self.assertTrue(os.path.isfile(path), "zram-generator.conf missing")

    def test_zram_config_has_swap(self):
        """ZRAM config must define a swap device."""
        path = os.path.join(AIROOTFS, "etc", "systemd", "zram-generator.conf")
        with open(path) as f:
            content = f.read()
        self.assertIn("[zram0]", content, "Must define [zram0] section")
        self.assertIn(
            "zram-size", content.lower(),
            "Must configure zram-size",
        )

    def test_sysctl_tuning_exists(self):
        """Kernel parameter tuning config must exist."""
        path = os.path.join(
            AIROOTFS, "etc", "sysctl.d", "99-extreme-low-ram.conf"
        )
        self.assertTrue(os.path.isfile(path), "sysctl tuning config missing")

    def test_sysctl_has_swappiness(self):
        """Sysctl config must set vm.swappiness."""
        path = os.path.join(
            AIROOTFS, "etc", "sysctl.d", "99-extreme-low-ram.conf"
        )
        with open(path) as f:
            content = f.read()
        self.assertIn(
            "vm.swappiness", content,
            "Must configure vm.swappiness for RAM optimization",
        )

    def test_os_release_branding(self):
        """os-release must have madOS branding."""
        path = os.path.join(AIROOTFS, "etc", "os-release")
        if not os.path.isfile(path):
            self.skipTest("os-release not in airootfs")
        with open(path) as f:
            content = f.read()
        self.assertIn("mados", content.lower(), "os-release must reference madOS")


# ═══════════════════════════════════════════════════════════════════════════
# User environment defaults (skel)
# ═══════════════════════════════════════════════════════════════════════════
class TestSkelConfig(unittest.TestCase):
    """Verify default user configuration files in /etc/skel."""

    SKEL = os.path.join(AIROOTFS, "etc", "skel")

    def test_zshrc_exists(self):
        """.zshrc must exist in skel for new users."""
        self.assertTrue(
            os.path.isfile(os.path.join(self.SKEL, ".zshrc")),
            ".zshrc missing from /etc/skel",
        )

    def test_sway_config_exists(self):
        """Sway compositor config must exist in skel."""
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.SKEL, ".config", "sway", "config")
            ),
            "Sway config missing from /etc/skel",
        )

    def test_waybar_config_exists(self):
        """Waybar status bar config must exist in skel."""
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.SKEL, ".config", "waybar", "config")
            ),
            "Waybar config missing from /etc/skel",
        )

    def test_waybar_style_exists(self):
        """Waybar style CSS must exist in skel."""
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.SKEL, ".config", "waybar", "style.css")
            ),
            "Waybar style.css missing from /etc/skel",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Installer script files
# ═══════════════════════════════════════════════════════════════════════════
class TestInstallerScripts(unittest.TestCase):
    """Verify installer launch scripts exist and are valid."""

    def test_install_mados_exists(self):
        """install-mados launcher must exist."""
        path = os.path.join(BIN_DIR, "install-mados")
        self.assertTrue(os.path.isfile(path), "install-mados missing")

    def test_install_mados_valid_syntax(self):
        """install-mados launcher must have valid bash syntax."""
        path = os.path.join(BIN_DIR, "install-mados")
        result = subprocess.run(
            ["bash", "-n", path], capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )

    def test_gtk_installer_exists(self):
        """GTK installer Python script must exist."""
        path = os.path.join(BIN_DIR, "install-mados-gtk.py")
        self.assertTrue(os.path.isfile(path), "install-mados-gtk.py missing")

    def test_gtk_installer_valid_syntax(self):
        """GTK installer must have valid Python syntax."""
        path = os.path.join(BIN_DIR, "install-mados-gtk.py")
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Syntax error in GTK installer: {result.stderr}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Post-install service enablement
# ═══════════════════════════════════════════════════════════════════════════
class TestPostInstallServices(unittest.TestCase):
    """Verify the installer enables required services after installation."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    REQUIRED_SERVICES = [
        "earlyoom",
        "NetworkManager",
        "iwd",
    ]

    def test_required_services_enabled(self):
        """Installer must enable essential system services."""
        for svc in self.REQUIRED_SERVICES:
            with self.subTest(service=svc):
                self.assertIn(
                    svc, self.content,
                    f"Installer must enable {svc} service",
                )

    def test_enables_greetd(self):
        """Installer should enable greetd for graphical login."""
        self.assertIn(
            "greetd", self.content,
            "Installer must enable greetd for graphical login",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Autologin for live environment
# ═══════════════════════════════════════════════════════════════════════════
class TestLiveAutologin(unittest.TestCase):
    """Verify live ISO autologin is configured correctly."""

    def test_autologin_conf_exists(self):
        """getty@tty1 autologin drop-in must exist."""
        path = os.path.join(
            AIROOTFS, "etc", "systemd", "system",
            "getty@tty1.service.d", "autologin.conf",
        )
        self.assertTrue(os.path.isfile(path), "autologin.conf missing")

    def test_autologin_for_mados_user(self):
        """Autologin must be configured for the mados user."""
        path = os.path.join(
            AIROOTFS, "etc", "systemd", "system",
            "getty@tty1.service.d", "autologin.conf",
        )
        with open(path) as f:
            content = f.read()
        self.assertIn(
            "--autologin mados", content,
            "Autologin must be configured for the mados user",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Sudoers configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestSudoersConfig(unittest.TestCase):
    """Verify sudoers configuration for live environment."""

    def test_claude_nopasswd_exists(self):
        """OpenCode NOPASSWD sudoers file must exist."""
        path = os.path.join(
            AIROOTFS, "etc", "sudoers.d", "99-opencode-nopasswd"
        )
        self.assertTrue(os.path.isfile(path), "99-opencode-nopasswd missing")

    def test_mados_has_nopasswd(self):
        """mados user should have NOPASSWD sudo access."""
        path = os.path.join(
            AIROOTFS, "etc", "sudoers.d", "99-opencode-nopasswd"
        )
        with open(path) as f:
            content = f.read()
        self.assertIn(
            "NOPASSWD", content,
            "mados user must have NOPASSWD sudo access",
        )


if __name__ == "__main__":
    unittest.main()
