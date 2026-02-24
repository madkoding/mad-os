#!/usr/bin/env python3
"""
Tests for madOS first-boot post-installation configuration.

Validates the first-boot script that runs after installation on the first reboot.
This script is responsible for Phase 2 package installation, service configuration,
and post-install setup (Oh My Zsh, OpenCode, audio, etc.).

These tests verify:
1. The first-boot service and script are properly created during installation
2. The script has valid bash syntax
3. The script contains all required configuration steps
4. Phase 2 packages are correctly listed
5. Services are enabled appropriately
"""

import os
import re
import subprocess
import sys
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so installer modules can be imported headlessly.
# ---------------------------------------------------------------------------
# Import from test_helpers instead of duplicating
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import create_gtk_mocks

gi_mock, repo_mock = create_gtk_mocks()
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
# First-boot service setup
# ═══════════════════════════════════════════════════════════════════════════
class TestFirstBootServiceSetup(unittest.TestCase):
    """Verify the installer sets up the first-boot service correctly."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_creates_first_boot_script(self):
        """Installer must create /usr/local/bin/mados-first-boot.sh."""
        self.assertIn(
            "/usr/local/bin/mados-first-boot.sh", self.content,
            "Installer must create mados-first-boot.sh script",
        )

    def test_creates_first_boot_service(self):
        """Installer must create mados-first-boot.service."""
        self.assertIn(
            "mados-first-boot.service", self.content,
            "Installer must create mados-first-boot.service",
        )

    def test_enables_first_boot_service(self):
        """Installer must enable the first-boot service."""
        self.assertIn(
            "systemctl enable mados-first-boot.service", self.content,
            "Installer must enable mados-first-boot.service",
        )

    def test_service_runs_after_network(self):
        """First-boot service must wait for network connectivity."""
        self.assertIn(
            "After=network-online.target", self.content,
            "Service must run after network-online.target",
        )
        self.assertIn(
            "Wants=network-online.target", self.content,
            "Service must want network-online.target",
        )

    def test_service_is_oneshot(self):
        """First-boot service must be Type=oneshot."""
        self.assertIn(
            "Type=oneshot", self.content,
            "Service must be Type=oneshot (runs once)",
        )

    def test_service_has_timeout(self):
        """First-boot service must have a reasonable timeout."""
        # Phase 2 installs many packages, needs long timeout
        self.assertIn(
            "TimeoutStartSec", self.content,
            "Service must have TimeoutStartSec for long package installs",
        )


# ═══════════════════════════════════════════════════════════════════════════
# First-boot script generation
# ═══════════════════════════════════════════════════════════════════════════
class TestFirstBootScriptGeneration(unittest.TestCase):
    """Verify the first-boot script is generated correctly."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_has_build_first_boot_script_function(self):
        """Installer must have _build_first_boot_script function."""
        self.assertIn(
            "def _build_first_boot_script", self.content,
            "Must have _build_first_boot_script function",
        )

    def test_script_has_shebang(self):
        """Generated script must have bash shebang."""
        self.assertIn(
            "#!/bin/bash", self.content,
            "First-boot script must have bash shebang",
        )

    def test_script_uses_strict_mode(self):
        """Generated script must use bash strict mode."""
        # Look for set -euo pipefail or similar
        pattern = r"set -[euo]+[^\n]*pipefail"
        self.assertIsNotNone(
            re.search(pattern, self.content),
            "First-boot script must use 'set -euo pipefail' for safety",
        )

    def test_script_has_logging(self):
        """Generated script must have logging functionality."""
        self.assertIn(
            'LOG_TAG="mados-first-boot"', self.content,
            "Script must define LOG_TAG for journald logging",
        )
        self.assertIn(
            "log()", self.content,
            "Script must have log() function",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2 package installation
# ═══════════════════════════════════════════════════════════════════════════
class TestPhase2Packages(unittest.TestCase):
    """Verify Phase 2 packages are installed by first-boot script."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_installs_packages_with_pacman(self):
        """Script must install GPU compute packages using pacman."""
        self.assertIn(
            "pacman -S", self.content,
            "Must use 'pacman -S' to install GPU compute packages",
        )

    def test_uses_noconfirm_flag(self):
        """Script must use --noconfirm for unattended installation."""
        self.assertIn(
            "--noconfirm", self.content,
            "Must use --noconfirm for automated package installation",
        )

    def test_uses_needed_flag(self):
        """Script must use --needed to skip already-installed packages."""
        self.assertIn(
            "--needed", self.content,
            "Must use --needed to skip reinstalling existing packages",
        )

    def test_references_phase2_packages(self):
        """Script must reference PACKAGES_PHASE2."""
        # Import to verify it exists
        from mados_installer.config import PACKAGES_PHASE2
        self.assertIsInstance(PACKAGES_PHASE2, (list, tuple))
        self.assertGreater(len(PACKAGES_PHASE2), 0, "PACKAGES_PHASE2 must not be empty")

    def test_handles_cjk_fonts(self):
        """Script must conditionally install CJK fonts for Asian locales."""
        self.assertIn(
            "noto-fonts-cjk", self.content,
            "Must include noto-fonts-cjk for CJK locale support",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Service enablement
# ═══════════════════════════════════════════════════════════════════════════
class TestServiceEnablement(unittest.TestCase):
    """Verify the first-boot script enables required services."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_enables_bluetooth(self):
        """Script must enable bluetooth service."""
        self.assertIn(
            "systemctl enable bluetooth", self.content,
            "Must enable bluetooth service",
        )

    def test_enables_pipewire(self):
        """Script must enable PipeWire audio."""
        self.assertIn(
            "pipewire", self.content.lower(),
            "Must enable PipeWire audio system",
        )

    def test_enables_wireplumber(self):
        """Script must enable WirePlumber (PipeWire session manager)."""
        self.assertIn(
            "wireplumber", self.content.lower(),
            "Must enable WirePlumber service",
        )

    def test_enables_audio_init_service(self):
        """Script must create and enable mados-audio-init service."""
        self.assertIn(
            "mados-audio-init.service", self.content,
            "Must create mados-audio-init.service",
        )
        self.assertIn(
            "systemctl enable mados-audio-init", self.content,
            "Must enable mados-audio-init service",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Audio configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestAudioConfiguration(unittest.TestCase):
    """Verify the first-boot script configures audio correctly."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_creates_audio_init_script(self):
        """Script must create mados-audio-init.sh."""
        self.assertIn(
            "/usr/local/bin/mados-audio-init.sh", self.content,
            "Must create mados-audio-init.sh script",
        )

    def test_audio_script_uses_amixer(self):
        """Audio init script must use amixer to configure volumes."""
        self.assertIn(
            "amixer", self.content,
            "Audio init script must use amixer",
        )

    def test_audio_script_unmutes_controls(self):
        """Audio init script must unmute audio controls."""
        self.assertIn(
            "unmute", self.content,
            "Audio script must unmute audio controls",
        )

    def test_audio_script_saves_state(self):
        """Audio init script must save ALSA state."""
        self.assertIn(
            "alsactl store", self.content,
            "Audio script must save ALSA state with alsactl",
        )

    def test_audio_service_runs_after_sound_target(self):
        """Audio init service must run after sound.target."""
        self.assertIn(
            "After=", self.content,
            "Audio init service must have After= directive",
        )
        self.assertIn(
            "sound.target", self.content,
            "Audio init service must run after sound.target",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Chromium configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestChromiumConfiguration(unittest.TestCase):
    """Verify the first-boot script configures Chromium."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_creates_chromium_flags(self):
        """Script must create /etc/chromium-flags.conf."""
        self.assertIn(
            "/etc/chromium-flags.conf", self.content,
            "Must create /etc/chromium-flags.conf",
        )

    def test_chromium_uses_wayland(self):
        """Chromium must be configured for Wayland."""
        self.assertIn(
            "--ozone-platform", self.content,
            "Chromium must use Wayland via --ozone-platform",
        )

    def test_chromium_disables_vulkan(self):
        """Chromium must disable Vulkan (not supported on Intel Atom)."""
        self.assertIn(
            "--disable-vulkan", self.content,
            "Chromium must disable Vulkan for Intel Atom compatibility",
        )

    def test_chromium_disables_vaapi(self):
        """Chromium must disable VA-API (fails on Intel Atom)."""
        self.assertIn(
            "VaapiVideoDecoder", self.content,
            "Chromium must disable VA-API video decoder",
        )

    def test_chromium_limits_renderer_processes(self):
        """Chromium must limit renderer processes for low-RAM."""
        self.assertIn(
            "--renderer-process-limit", self.content,
            "Chromium must limit renderer processes for RAM optimization",
        )

    def test_chromium_sets_homepage(self):
        """Script must configure Chromium homepage policy."""
        self.assertIn(
            "/etc/chromium/policies/managed", self.content,
            "Must create Chromium managed policies directory",
        )
        self.assertIn(
            "HomepageLocation", self.content,
            "Must set Chromium homepage via policy",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Oh My Zsh installation
# ═══════════════════════════════════════════════════════════════════════════
class TestOhMyZshInstallation(unittest.TestCase):
    """Verify the first-boot script installs Oh My Zsh."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_installs_to_skel(self):
        """Oh My Zsh must be installed to /etc/skel."""
        self.assertIn(
            "/etc/skel/.oh-my-zsh", self.content,
            "Must install Oh My Zsh to /etc/skel",
        )

    def test_clones_from_github(self):
        """Must clone Oh My Zsh from GitHub."""
        self.assertIn(
            "github.com/ohmyzsh/ohmyzsh", self.content,
            "Must clone Oh My Zsh from official GitHub repo",
        )

    def test_copies_to_user_home(self):
        """Must copy Oh My Zsh to user's home directory."""
        self.assertIn(
            "cp", self.content,
            "Must copy Oh My Zsh to user home",
        )
        self.assertIn(
            "chown", self.content,
            "Must chown Oh My Zsh files to user",
        )

    def test_creates_fallback_service(self):
        """Must create setup-ohmyzsh.service as fallback."""
        self.assertIn(
            "setup-ohmyzsh.service", self.content,
            "Must create setup-ohmyzsh.service fallback",
        )

    def test_handles_no_internet(self):
        """Must handle case when internet is not available."""
        self.assertIn(
            "curl", self.content,
            "Must check for internet connectivity",
        )


# ═══════════════════════════════════════════════════════════════════════════
# OpenCode installation
# ═══════════════════════════════════════════════════════════════════════════
class TestOpenCodeInstallation(unittest.TestCase):
    """Verify the first-boot script installs OpenCode."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_uses_opencode_install_script(self):
        """Must use OpenCode official install script."""
        self.assertIn(
            "opencode.ai/install", self.content,
            "Must use OpenCode install script from opencode.ai",
        )

    def test_uses_curl_to_download(self):
        """Must use curl to download install script."""
        self.assertIn(
            "curl", self.content,
            "Must use curl to download OpenCode installer",
        )

    def test_pipes_to_bash(self):
        """Install script must be piped to bash."""
        self.assertIn(
            "bash", self.content,
            "Install script must be executed with bash",
        )

    def test_checks_opencode_command(self):
        """Must verify opencode command is available after install."""
        self.assertIn(
            "opencode", self.content,
            "Must verify opencode command exists",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Self-cleanup
# ═══════════════════════════════════════════════════════════════════════════
class TestFirstBootSelfCleanup(unittest.TestCase):
    """Verify the first-boot script disables itself after running."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_disables_service(self):
        """Script must disable mados-first-boot.service after running."""
        self.assertIn(
            "systemctl disable mados-first-boot", self.content,
            "Script must disable itself after completion",
        )

    def test_removes_script(self):
        """Script must remove itself after running."""
        self.assertIn(
            "rm", self.content,
            "Script must remove itself",
        )
        # Check it removes the script file
        pattern = r"rm[^\n]*mados-first-boot\.sh"
        self.assertIsNotNone(
            re.search(pattern, self.content),
            "Script must remove mados-first-boot.sh file",
        )


# ═══════════════════════════════════════════════════════════════════════════
# XDG user directories
# ═══════════════════════════════════════════════════════════════════════════
class TestXDGUserDirectories(unittest.TestCase):
    """Verify the installer creates standard XDG user directories."""

    XDG_DIRS = [
        "Documents", "Downloads", "Music", "Videos",
        "Desktop", "Templates", "Public",
    ]

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_creates_xdg_directories(self):
        """Installer must create standard XDG user directories."""
        for d in self.XDG_DIRS:
            with self.subTest(directory=d):
                self.assertIn(
                    d, self.content,
                    f"Installer must create ~/{d} directory",
                )

    def test_skel_has_xdg_directories(self):
        """Skel directory must contain XDG user directories."""
        skel_dir = os.path.join(AIROOTFS, "etc", "skel")
        for d in self.XDG_DIRS + ["Pictures"]:
            with self.subTest(directory=d):
                self.assertTrue(
                    os.path.isdir(os.path.join(skel_dir, d)),
                    f"/etc/skel/{d} must exist",
                )

    def test_xdg_user_dirs_defaults_exists(self):
        """XDG user-dirs.defaults config must exist."""
        defaults_file = os.path.join(AIROOTFS, "etc", "xdg", "user-dirs.defaults")
        self.assertTrue(
            os.path.isfile(defaults_file),
            "/etc/xdg/user-dirs.defaults must exist",
        )

    def test_xdg_user_dirs_defaults_content(self):
        """user-dirs.defaults must define all standard XDG directories."""
        defaults_file = os.path.join(AIROOTFS, "etc", "xdg", "user-dirs.defaults")
        if not os.path.isfile(defaults_file):
            self.skipTest("user-dirs.defaults not found")
        with open(defaults_file) as f:
            content = f.read()
        for key in ("DESKTOP", "DOWNLOAD", "TEMPLATES", "PUBLICSHARE",
                     "DOCUMENTS", "MUSIC", "PICTURES", "VIDEOS"):
            with self.subTest(key=key):
                self.assertIn(
                    key, content,
                    f"user-dirs.defaults must define {key}",
                )

    def test_xdg_user_dirs_package(self):
        """packages.x86_64 must include xdg-user-dirs."""
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            packages = f.read()
        self.assertIn(
            "xdg-user-dirs", packages,
            "xdg-user-dirs package must be in packages.x86_64",
        )


# ═══════════════════════════════════════════════════════════════════════════
# GPU detection in first-boot script
# ═══════════════════════════════════════════════════════════════════════════
class TestGpuDetection(unittest.TestCase):
    """Verify the first-boot script detects GPUs and installs compute drivers."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_uses_lspci_for_gpu_detection(self):
        """Script must use lspci to detect GPU hardware."""
        self.assertIn(
            "lspci", self.content,
            "Must use lspci to detect GPU hardware",
        )
        # Verify it filters for VGA/3D/Display controllers
        pattern = r'lspci[^\n]*grep[^\n]*-iE[^\n]*"VGA\|3D\|Display"'
        self.assertIsNotNone(
            re.search(pattern, self.content),
            "Must filter lspci output for VGA/3D/Display controllers",
        )

    def test_nvidia_detection(self):
        """Script must check for NVIDIA GPUs via case-insensitive grep."""
        pattern = r'grep\s+-qi\s+nvidia'
        self.assertIsNotNone(
            re.search(pattern, self.content),
            "Must detect NVIDIA GPUs with case-insensitive grep",
        )

    def test_amd_detection_checks_amd_ati_radeon(self):
        """Script must detect AMD GPUs by checking AMD, ATI, and Radeon strings."""
        for keyword in ("AMD", "ATI", "Radeon"):
            with self.subTest(keyword=keyword):
                self.assertIn(
                    keyword, self.content,
                    f"AMD detection must check for '{keyword}' string",
                )

    def test_legacy_amd_exclusion(self):
        """Script must skip pre-GCN legacy AMD GPUs for ROCm."""
        # Verify it checks legacy Radeon series (e.g., HD 2xxx-6xxx, Rage)
        self.assertIn(
            "Radeon HD", self.content,
            "Must check for Radeon HD legacy series",
        )
        self.assertIn(
            "Rage", self.content,
            "Must check for ATI Rage legacy GPUs",
        )
        self.assertIn(
            "Legacy AMD GPU detected", self.content,
            "Must log when a legacy AMD GPU is skipped",
        )

    def test_gpu_found_controls_common_packages(self):
        """GPU_FOUND variable must gate common package installation."""
        self.assertIn(
            'GPU_FOUND=false', self.content,
            "Must initialize GPU_FOUND to false",
        )
        self.assertIn(
            'GPU_FOUND=true', self.content,
            "Must set GPU_FOUND to true when a GPU is detected",
        )
        # Verify common packages are only installed when GPU_FOUND is true
        self.assertIn(
            '"$GPU_FOUND" = true',
            self.content,
            "Must check $GPU_FOUND before installing common packages",
        )

    def test_nvidia_packages_conditional(self):
        """NVIDIA packages must only be installed when NVIDIA GPU is detected."""
        # The NVIDIA install block should be inside the nvidia grep conditional
        # (grep and pacman may be separated by log lines)
        pattern = r'grep[^\n]*nvidia[^\n]*(?:\n[^\n]*){0,5}\n[^\n]*pacman -S[^\n]*--noconfirm[^\n]*--needed'
        self.assertIsNotNone(
            re.search(pattern, self.content, re.IGNORECASE | re.DOTALL),
            "NVIDIA packages must be installed conditionally after detection",
        )

    def test_amd_rocm_packages_conditional(self):
        """AMD ROCm packages must only be installed when AMD GPU is detected."""
        # Should reference ROCm packages conditionally
        self.assertIn(
            "rocm", self.content.lower(),
            "Must reference ROCm packages for AMD GPUs",
        )
        # ROCm install is gated by the legacy GPU check
        self.assertIn(
            "Legacy AMD GPU detected",
            self.content,
            "Must handle legacy AMD GPUs that don't support ROCm",
        )
        # Verify the script mentions ROCm support detection
        self.assertIn(
            "AMD GPU with ROCm support detected",
            self.content,
            "Must log ROCm-capable AMD GPU detection",
        )

    def test_gpu_compute_packages_from_config(self):
        """Script must use GPU_COMPUTE_PACKAGES config via f-string variables."""
        from mados_installer.config import GPU_COMPUTE_PACKAGES
        # The installation.py uses f-string variables like {nvidia_pkgs} and
        # {amd_pkgs} that expand at runtime.  Verify the variables are present.
        self.assertIn(
            "{nvidia_pkgs}", self.content,
            "Must reference {nvidia_pkgs} f-string variable for NVIDIA packages",
        )
        self.assertIn(
            "{amd_pkgs}", self.content,
            "Must reference {amd_pkgs} f-string variable for AMD packages",
        )
        self.assertIn(
            "{common_pkgs}", self.content,
            "Must reference {common_pkgs} f-string variable for common packages",
        )
        # Also verify the config dict has the expected packages
        self.assertGreater(len(GPU_COMPUTE_PACKAGES["nvidia"]), 0)
        self.assertGreater(len(GPU_COMPUTE_PACKAGES["amd"]), 0)
        self.assertGreater(len(GPU_COMPUTE_PACKAGES["common"]), 0)


if __name__ == "__main__":
    unittest.main()
