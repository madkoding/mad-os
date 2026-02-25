#!/usr/bin/env python3
"""
Tests for madOS first-boot post-installation configuration.

Validates the first-boot script that runs after installation on the first reboot.
This script is responsible for service configuration and post-install setup
(audio, Chromium, fallback services for optional tools).

Phase 2 is 100% offline — all packages and tools are already present from
the ISO (copied via rsync during Phase 1).  Phase 2 only configures
services and creates fallback systemd services for optional tools.

These tests verify:
1. The first-boot service and script are properly created during installation
2. The script has valid bash syntax
3. The script contains all required configuration steps
4. Services are enabled appropriately
5. No internet downloads occur during Phase 2
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
        self.assertIn(
            "TimeoutStartSec", self.content,
            "Service must have TimeoutStartSec for configuration steps",
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
# Phase 2 is fully offline
# ═══════════════════════════════════════════════════════════════════════════
class TestPhase2FullyOffline(unittest.TestCase):
    """Verify Phase 2 does NOT download anything from the internet."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_no_redundant_system_update(self):
        """Script must NOT run 'pacman -Syu' (packages are already installed from ISO)."""
        self.assertNotIn(
            "pacman -Syu", self.content,
            "Must not run 'pacman -Syu' — all ISO packages are already installed via rsync",
        )

    def test_no_internet_check_in_first_boot(self):
        """Phase 2 must NOT check internet (it is 100% offline)."""
        # The _build_first_boot_script generates the bash script inline.
        # Extract just the generated script portion (inside the f-string).
        self.assertNotIn(
            "INTERNET_AVAILABLE", self.content,
            "Phase 2 must not use INTERNET_AVAILABLE — it is 100% offline",
        )

    def test_no_inline_git_clone(self):
        """Phase 2 must NOT clone repos (Nordic, Oh My Zsh are copied from ISO)."""
        # Check the first-boot script template (f-string) does not contain git clone
        self.assertNotIn(
            "git clone", self.content,
            "Phase 2 must not git clone anything — everything comes from the ISO",
        )

    def test_no_inline_opencode_install(self):
        """Phase 2 must NOT download OpenCode (binary is copied from ISO)."""
        # The setup script creation is fine (it's for manual retry),
        # but the direct curl install should not be there.
        # Look for the inline install pattern (curl | bash outside of heredoc)
        lines = self.content.splitlines()
        in_heredoc = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("cat >") and "<<" in stripped:
                in_heredoc = True
            if in_heredoc and stripped in ("EOFSETUP", "EOFSVC", "EOFAUDIO",
                                           "EOFCHROMIUM", "EOFPOLICY",
                                           "EOFUSRSVC"):
                in_heredoc = False
                continue
            if not in_heredoc and "opencode.ai/install" in stripped:
                self.fail(
                    "Phase 2 must not directly download OpenCode — "
                    "it should be copied from the ISO via rsync"
                )

    def test_no_inline_ollama_install(self):
        """Phase 2 must NOT download Ollama (binary is copied from ISO)."""
        lines = self.content.splitlines()
        in_heredoc = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("cat >") and "<<" in stripped:
                in_heredoc = True
            if in_heredoc and stripped in ("EOFSETUP", "EOFSVC", "EOFAUDIO",
                                           "EOFCHROMIUM", "EOFPOLICY",
                                           "EOFUSRSVC"):
                in_heredoc = False
                continue
            if not in_heredoc and "ollama.com/install.sh" in stripped:
                self.fail(
                    "Phase 2 must not directly download Ollama — "
                    "it should be copied from the ISO via rsync"
                )


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2 configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestPhase2Configuration(unittest.TestCase):
    """Verify Phase 2 configures services on first boot."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()


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
# Oh My Zsh fallback service
# ═══════════════════════════════════════════════════════════════════════════
class TestOhMyZshFallbackService(unittest.TestCase):
    """Verify the first-boot script creates Oh My Zsh fallback service."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_creates_fallback_service(self):
        """Must create setup-ohmyzsh.service as fallback."""
        self.assertIn(
            "setup-ohmyzsh.service", self.content,
            "Must create setup-ohmyzsh.service fallback",
        )


# ═══════════════════════════════════════════════════════════════════════════
# OpenCode fallback service
# ═══════════════════════════════════════════════════════════════════════════
class TestOpenCodeFallbackService(unittest.TestCase):
    """Verify the first-boot script creates OpenCode setup script and fallback service."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_creates_setup_script(self):
        """Must create setup-opencode.sh for manual retry."""
        self.assertIn(
            "setup-opencode.sh", self.content,
            "Must create setup-opencode.sh on the installed system",
        )

    def test_creates_fallback_service(self):
        """Must create setup-opencode.service for boot-time retry."""
        self.assertIn(
            "setup-opencode.service", self.content,
            "Must create setup-opencode.service on the installed system",
        )

    def test_enables_fallback_service(self):
        """Must enable setup-opencode.service on the installed system."""
        self.assertIn(
            "systemctl enable setup-opencode.service", self.content,
            "Must enable setup-opencode.service",
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

if __name__ == "__main__":
    unittest.main()
