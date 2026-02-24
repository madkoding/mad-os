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
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so installer modules can be imported headlessly.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import install_gtk_mocks
install_gtk_mocks()

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

    def test_hyprland_included(self):
        """Live ISO must include hyprland compositor."""
        self.assertIn("hyprland", self._read_packages())

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

    def test_hyprland_config_exists(self):
        """Hyprland compositor config must exist in skel."""
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.SKEL, ".config", "hypr", "hyprland.conf")
            ),
            "Hyprland config missing from /etc/skel",
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

    def test_select_compositor_exists(self):
        """select-compositor script must exist."""
        path = os.path.join(BIN_DIR, "select-compositor")
        self.assertTrue(os.path.isfile(path), "select-compositor missing")

    def test_select_compositor_valid_syntax(self):
        """select-compositor must have valid bash syntax."""
        path = os.path.join(BIN_DIR, "select-compositor")
        result = subprocess.run(
            ["bash", "-n", path], capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )

    def test_hyprland_session_exists(self):
        """hyprland-session wrapper must exist."""
        path = os.path.join(BIN_DIR, "hyprland-session")
        self.assertTrue(os.path.isfile(path), "hyprland-session missing")

    def test_hyprland_session_valid_syntax(self):
        """hyprland-session must have valid bash syntax."""
        path = os.path.join(BIN_DIR, "hyprland-session")
        result = subprocess.run(
            ["bash", "-n", path], capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )

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
        "bluetooth",
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
# Initramfs / mkinitcpio preset restoration
# ═══════════════════════════════════════════════════════════════════════════
class TestInitramfsPresetRestoration(unittest.TestCase):
    """Verify the installer restores the standard linux.preset before mkinitcpio."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_restores_standard_linux_preset(self):
        """Installer must restore standard linux.preset with default/fallback presets."""
        self.assertIn(
            "PRESETS=('default' 'fallback')", self.content,
            "Installer must restore standard PRESETS=('default' 'fallback') in linux.preset",
        )

    def test_removes_archiso_mkinitcpio_conf(self):
        """Installer must remove archiso-specific mkinitcpio config."""
        self.assertIn(
            "rm -f /etc/mkinitcpio.conf.d/archiso.conf", self.content,
            "Installer must remove archiso.conf before mkinitcpio -P",
        )

    def test_preset_written_before_mkinitcpio(self):
        """linux.preset must be restored before mkinitcpio -P runs."""
        preset_pos = self.content.find("PRESETS=('default' 'fallback')")
        mkinitcpio_pos = self.content.find("mkinitcpio -P")
        self.assertNotEqual(preset_pos, -1, "Must contain preset restoration")
        self.assertNotEqual(mkinitcpio_pos, -1, "Must contain mkinitcpio -P")
        self.assertLess(
            preset_pos, mkinitcpio_pos,
            "linux.preset must be written before mkinitcpio -P is called",
        )

    def test_kernel_recovery_before_mkinitcpio(self):
        """Installer must recover kernel from modules dir if /boot/vmlinuz-linux is missing."""
        self.assertIn(
            "/usr/lib/modules/", self.content,
            "Installer must recover kernel from /usr/lib/modules/*/vmlinuz",
        )
        recovery_pos = self.content.find("/usr/lib/modules/")
        mkinitcpio_pos = self.content.find("mkinitcpio -P")
        self.assertLess(
            recovery_pos, mkinitcpio_pos,
            "Kernel recovery must happen before mkinitcpio -P is called",
        )

    def test_kernel_recovery_fallback_reinstall(self):
        """Installer must have fallback to reinstall linux package if kernel not found."""
        self.assertIn(
            "pacman -S --noconfirm linux", self.content,
            "Installer must fallback to reinstalling linux package if kernel still missing",
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


# ═══════════════════════════════════════════════════════════════════════════
# Compositor selection (Hyprland / Sway)
# ═══════════════════════════════════════════════════════════════════════════
class TestCompositorSelection(unittest.TestCase):
    """Verify dynamic compositor selection is properly configured."""

    def test_select_compositor_outputs_valid_compositor(self):
        """select-compositor should output either 'sway' or 'hyprland'."""
        path = os.path.join(BIN_DIR, "select-compositor")
        with open(path) as f:
            content = f.read()
        # Script must echo either "sway" or "hyprland"
        self.assertIn('echo "sway"', content)
        self.assertIn('echo "hyprland"', content)

    def test_bash_profile_uses_select_compositor(self):
        """bash_profile should use select-compositor for dynamic selection."""
        path = os.path.join(AIROOTFS, "etc", "skel", ".bash_profile")
        with open(path) as f:
            content = f.read()
        self.assertIn("select-compositor", content,
                       ".bash_profile must use select-compositor script")

    def test_bash_profile_supports_both_compositors(self):
        """bash_profile should handle both Sway and Hyprland."""
        path = os.path.join(AIROOTFS, "etc", "skel", ".bash_profile")
        with open(path) as f:
            content = f.read()
        self.assertIn("exec sway", content,
                       ".bash_profile must exec sway for software rendering")
        # Hyprland is launched via start-hyprland without exec so fallback to sway works if it fails
        self.assertIn("start-hyprland ||", content,
                       ".bash_profile must launch Hyprland via start-hyprland with fallback for hardware rendering")

    def test_zlogin_uses_select_compositor(self):
        """zlogin should use select-compositor for dynamic selection."""
        path = os.path.join(AIROOTFS, "home", "mados", ".zlogin")
        with open(path) as f:
            content = f.read()
        self.assertIn("select-compositor", content,
                       ".zlogin must use select-compositor script")

    def test_hyprland_in_installer_packages(self):
        """Installer PACKAGES must include hyprland."""
        from mados_installer.config import PACKAGES
        self.assertIn("hyprland", PACKAGES,
                       "hyprland must be in installer PACKAGES")

    def test_hyprland_session_script_execs_hyprland(self):
        """hyprland-session must exec start-hyprland."""
        path = os.path.join(BIN_DIR, "hyprland-session")
        with open(path) as f:
            content = f.read()
        self.assertIn("exec start-hyprland", content,
                       "hyprland-session must exec start-hyprland")

    def test_hyprland_session_sets_desktop(self):
        """hyprland-session must set XDG_CURRENT_DESKTOP."""
        path = os.path.join(BIN_DIR, "hyprland-session")
        with open(path) as f:
            content = f.read()
        self.assertIn("XDG_CURRENT_DESKTOP=Hyprland", content,
                       "hyprland-session must set XDG_CURRENT_DESKTOP")

    def test_profiledef_includes_new_scripts(self):
        """profiledef.sh must set permissions for compositor scripts."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        for script in ['hyprland-session', 'select-compositor']:
            with self.subTest(script=script):
                self.assertIn(script, content,
                               f"profiledef.sh must include {script}")

    def test_waybar_supports_both_compositors(self):
        """Waybar config must include modules for both Sway and Hyprland."""
        path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(path) as f:
            content = f.read()
        self.assertIn("sway/workspaces", content,
                       "Waybar must include sway/workspaces module")
        self.assertIn("hyprland/workspaces", content,
                       "Waybar must include hyprland/workspaces module")

    def test_installer_copies_compositor_scripts(self):
        """Installer must copy compositor selection scripts."""
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        with open(install_py) as f:
            content = f.read()
        for script in ['hyprland-session', 'start-hyprland', 'select-compositor']:
            with self.subTest(script=script):
                self.assertIn(script, content,
                               f"Installer must copy {script}")


# ═══════════════════════════════════════════════════════════════════════════
# Audio quality configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestAudioQualityPostInstall(unittest.TestCase):
    """Verify audio quality auto-detection is configured for installed system."""

    def test_audio_quality_script_exists(self):
        """Audio quality script must exist."""
        path = os.path.join(BIN_DIR, "mados-audio-quality.sh")
        self.assertTrue(
            os.path.isfile(path),
            "mados-audio-quality.sh script missing"
        )

    def test_audio_quality_service_exists(self):
        """Audio quality systemd service must exist."""
        path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-audio-quality.service"
        )
        self.assertTrue(
            os.path.isfile(path),
            "mados-audio-quality.service missing"
        )

    def test_audio_quality_service_enabled(self):
        """Audio quality service must be enabled."""
        wants = os.path.join(
            AIROOTFS, "etc", "systemd", "system",
            "multi-user.target.wants", "mados-audio-quality.service"
        )
        self.assertTrue(
            os.path.islink(wants),
            "mados-audio-quality.service not enabled"
        )

    def test_audio_quality_user_service_in_skel(self):
        """User audio quality service must be in skel."""
        path = os.path.join(
            AIROOTFS, "etc", "skel", ".config",
            "systemd", "user", "mados-audio-quality.service"
        )
        self.assertTrue(
            os.path.isfile(path),
            "User audio quality service missing from skel"
        )

    def test_audio_quality_runs_after_audio_init(self):
        """Audio quality service must run after basic audio init."""
        path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-audio-quality.service"
        )
        with open(path) as f:
            content = f.read()
        self.assertIn(
            "mados-audio-init.service", content,
            "Must run after mados-audio-init.service"
        )

    def test_script_has_pipewire_config(self):
        """Script must generate PipeWire configuration."""
        path = os.path.join(BIN_DIR, "mados-audio-quality.sh")
        with open(path) as f:
            content = f.read()
        self.assertIn("pipewire.conf.d", content)
        self.assertIn("default.clock.rate", content)

    def test_script_has_wireplumber_config(self):
        """Script must generate WirePlumber configuration."""
        path = os.path.join(BIN_DIR, "mados-audio-quality.sh")
        with open(path) as f:
            content = f.read()
        self.assertIn("wireplumber.conf.d", content)
        self.assertIn("monitor.alsa.rules", content)


if __name__ == "__main__":
    unittest.main()
