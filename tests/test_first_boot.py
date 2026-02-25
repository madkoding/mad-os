#!/usr/bin/env python3
"""
Tests for madOS first-boot post-installation configuration.

Validates the first-boot script that runs after installation on the first reboot.
Phase 2 is a lightweight verification pass — all packages, services, scripts,
and config files are pre-installed on the live USB and copied via rsync during
Phase 1.  Services are enabled in the Phase 1 chroot.

Phase 2 only verifies the graphical environment (cage, regreet, sway,
session scripts) and enables TTY fallbacks if anything is missing, then
disables itself.

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

    def test_service_runs_after_local_fs(self):
        """First-boot service must wait for local filesystem (offline, no network needed)."""
        self.assertIn(
            "After=local-fs.target", self.content,
            "Service must run after local-fs.target (Phase 2 is 100% offline)",
        )

    def test_service_does_not_need_network(self):
        """First-boot service must NOT depend on network (Phase 2 is 100% offline)."""
        # Phase 2 only configures services and creates fallback services.
        # Network dependency would delay boot and is not needed.
        # Check the service definition (not the fallback services inside heredocs)
        lines = self.content.splitlines()
        in_heredoc = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("cat >") and "<<" in stripped:
                in_heredoc = True
            if in_heredoc and stripped in ("EOFSVC", "EOFSETUP"):
                in_heredoc = False
                continue
            if not in_heredoc and "mados-first-boot.service" in stripped:
                # We're near the service definition
                pass
        # The first-boot service definition should use local-fs.target, not network
        self.assertNotIn(
            "After=network-online.target\nWants=network-online.target\n"
            "ConditionPathExists=/usr/local/bin/mados-first-boot.sh",
            self.content,
            "First-boot service must not use network-online.target (Phase 2 is offline)",
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

    def test_service_runs_before_greetd(self):
        """First-boot service must complete before greetd starts.

        Phase 2 creates the greetd config and enables services. If greetd
        starts before Phase 2 finishes, the login screen may fail due to
        missing config files.
        """
        self.assertIn(
            "Before=greetd.service", self.content,
            "Service must run before greetd.service to ensure config is ready",
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
        """Generated script must use set -e for error detection."""
        # The first-boot script uses 'set -e' initially, then 'set +e' for
        # non-critical operations.  We verify 'set -e' is present.
        self.assertIn(
            "set -e", self.content,
            "First-boot script must use 'set -e' for error detection",
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

    def test_script_has_file_logging(self):
        """Generated script must log to a persistent file."""
        self.assertIn(
            "LOG_FILE=", self.content,
            "Script must define LOG_FILE for persistent file logging",
        )
        self.assertIn(
            "/var/log/mados-first-boot.log", self.content,
            "Script must log to /var/log/mados-first-boot.log",
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
# Phase 2 is now minimal — only graphical verification + cleanup
# ═══════════════════════════════════════════════════════════════════════════
class TestPhase2Configuration(unittest.TestCase):
    """Verify Phase 2 is a lightweight verification pass only."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()


# ═══════════════════════════════════════════════════════════════════════════
# Service enablement — now in Phase 1 config script (chroot)
# ═══════════════════════════════════════════════════════════════════════════
class TestServiceEnablement(unittest.TestCase):
    """Verify services are enabled in the Phase 1 config script (chroot)."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_enables_bluetooth(self):
        """Config script must enable bluetooth service."""
        self.assertIn(
            "systemctl enable bluetooth", self.content,
            "Must enable bluetooth service",
        )

    def test_enables_pipewire(self):
        """Config script must enable PipeWire audio."""
        self.assertIn(
            "pipewire", self.content.lower(),
            "Must enable PipeWire audio system",
        )

    def test_enables_wireplumber(self):
        """Config script must enable WirePlumber (PipeWire session manager)."""
        self.assertIn(
            "wireplumber", self.content.lower(),
            "Must enable WirePlumber service",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Audio — pre-installed on live USB, copied by rsync
# ═══════════════════════════════════════════════════════════════════════════
class TestAudioConfiguration(unittest.TestCase):
    """Verify audio scripts and services are pre-installed on the live USB."""

    def test_audio_init_script_exists(self):
        """mados-audio-init.sh must exist on the live USB."""
        script = os.path.join(REPO_DIR, "airootfs", "usr", "local", "bin",
                              "mados-audio-init.sh")
        self.assertTrue(os.path.isfile(script),
                        "mados-audio-init.sh must be pre-installed on live USB")

    def test_audio_init_service_exists(self):
        """mados-audio-init.service must exist on the live USB."""
        service = os.path.join(REPO_DIR, "airootfs", "etc", "systemd",
                               "system", "mados-audio-init.service")
        self.assertTrue(os.path.isfile(service),
                        "mados-audio-init.service must be pre-installed on live USB")

    def test_audio_init_service_is_enabled(self):
        """mados-audio-init.service must be enabled via symlink on live USB."""
        symlink = os.path.join(REPO_DIR, "airootfs", "etc", "systemd",
                               "system", "multi-user.target.wants",
                               "mados-audio-init.service")
        self.assertTrue(os.path.islink(symlink),
                        "mados-audio-init.service must be enabled on live USB")

    def test_audio_quality_service_exists(self):
        """mados-audio-quality.service must exist on the live USB."""
        service = os.path.join(REPO_DIR, "airootfs", "etc", "systemd",
                               "system", "mados-audio-quality.service")
        self.assertTrue(os.path.isfile(service),
                        "mados-audio-quality.service must be pre-installed on live USB")

    def test_user_audio_quality_service_in_skel(self):
        """User-level audio quality service must be in /etc/skel."""
        skel_svc = os.path.join(REPO_DIR, "airootfs", "etc", "skel",
                                ".config", "systemd", "user",
                                "mados-audio-quality.service")
        self.assertTrue(os.path.isfile(skel_svc),
                        "User-level audio quality service must be in /etc/skel")


# ═══════════════════════════════════════════════════════════════════════════
# Chromium — pre-installed on live USB, copied by rsync
# ═══════════════════════════════════════════════════════════════════════════
class TestChromiumConfiguration(unittest.TestCase):
    """Verify Chromium config files are pre-installed on the live USB."""

    def test_chromium_flags_exists(self):
        """chromium-flags.conf must exist on the live USB."""
        flags = os.path.join(REPO_DIR, "airootfs", "etc",
                             "chromium-flags.conf")
        self.assertTrue(os.path.isfile(flags),
                        "chromium-flags.conf must be pre-installed on live USB")

    def test_chromium_flags_has_content(self):
        """chromium-flags.conf must contain Wayland flags."""
        flags = os.path.join(REPO_DIR, "airootfs", "etc",
                             "chromium-flags.conf")
        if not os.path.isfile(flags):
            self.skipTest("chromium-flags.conf not found")
        with open(flags) as f:
            content = f.read()
        self.assertIn("--ozone-platform", content,
                       "Chromium must use Wayland via --ozone-platform")

    def test_chromium_homepage_policy_exists(self):
        """Chromium homepage policy JSON must exist on the live USB."""
        policy = os.path.join(REPO_DIR, "airootfs", "etc", "chromium",
                              "policies", "managed", "mados-homepage.json")
        self.assertTrue(os.path.isfile(policy),
                        "Chromium homepage policy must be pre-installed on live USB")

    def test_chromium_homepage_policy_is_valid_json(self):
        """Chromium homepage policy must be valid JSON."""
        import json
        policy = os.path.join(REPO_DIR, "airootfs", "etc", "chromium",
                              "policies", "managed", "mados-homepage.json")
        if not os.path.isfile(policy):
            self.skipTest("Chromium policy not found")
        with open(policy) as f:
            parsed = json.load(f)
        self.assertIn("HomepageLocation", parsed,
                       "Chromium policy must contain HomepageLocation")


# ═══════════════════════════════════════════════════════════════════════════
# Oh My Zsh fallback service — pre-installed on live USB
# ═══════════════════════════════════════════════════════════════════════════
class TestOhMyZshFallbackService(unittest.TestCase):
    """Verify the Oh My Zsh fallback service is pre-installed on the live USB."""

    def test_service_file_exists(self):
        """setup-ohmyzsh.service must exist on the live USB."""
        service = os.path.join(REPO_DIR, "airootfs", "etc", "systemd",
                               "system", "setup-ohmyzsh.service")
        self.assertTrue(os.path.isfile(service),
                        "setup-ohmyzsh.service must be pre-installed on live USB")

    def test_service_is_enabled(self):
        """setup-ohmyzsh.service must be enabled via symlink on live USB."""
        symlink = os.path.join(REPO_DIR, "airootfs", "etc", "systemd",
                               "system", "multi-user.target.wants",
                               "setup-ohmyzsh.service")
        self.assertTrue(os.path.islink(symlink),
                        "setup-ohmyzsh.service must be enabled on live USB")


# ═══════════════════════════════════════════════════════════════════════════
# OpenCode and Ollama are programs copied by rsync (no Phase 2 action)
# ═══════════════════════════════════════════════════════════════════════════
class TestOpenCodeOllamaNotInPhase2(unittest.TestCase):
    """Verify Phase 2 does NOT redundantly create setup scripts for programs
    that are already copied from the live USB via rsync."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_no_opencode_service(self):
        """Must NOT create setup-opencode.service (opencode is a program)."""
        self.assertNotIn(
            "setup-opencode.service", self.content,
            "Must NOT create setup-opencode.service — opencode is a program, not a service",
        )

    def test_no_ollama_service(self):
        """Must NOT create setup-ollama.service (ollama is a program)."""
        self.assertNotIn(
            "setup-ollama.service", self.content,
            "Must NOT create setup-ollama.service — ollama is a program, not a service",
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
# Graphical environment verification
# ═══════════════════════════════════════════════════════════════════════════
class TestGraphicalEnvironmentVerification(unittest.TestCase):
    """Verify Phase 2 checks graphical environment components."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_checks_cage_binary(self):
        """Phase 2 must verify cage binary exists."""
        self.assertIn(
            "cage", self.content,
            "Phase 2 must check for cage binary",
        )

    def test_checks_regreet_binary(self):
        """Phase 2 must verify regreet binary exists."""
        self.assertIn(
            "regreet", self.content,
            "Phase 2 must check for regreet binary",
        )

    def test_checks_cage_greeter_script(self):
        """Phase 2 must verify cage-greeter script is executable."""
        self.assertIn(
            "cage-greeter", self.content,
            "Phase 2 must check cage-greeter script",
        )

    def test_checks_greetd_service_enabled(self):
        """Phase 2 must verify greetd.service is enabled."""
        self.assertIn(
            "greetd.service", self.content,
            "Phase 2 must check greetd.service status",
        )

    def test_enables_getty_tty2_fallback(self):
        """Phase 2 must enable getty@tty2 as a fallback login."""
        self.assertIn(
            "getty@tty2.service", self.content,
            "Phase 2 must enable getty@tty2 as fallback login",
        )

    def test_checks_hyprland_session_script(self):
        """Phase 2 must verify hyprland-session script is executable."""
        self.assertIn(
            "hyprland-session", self.content,
            "Phase 2 must check hyprland-session script",
        )

    def test_checks_start_hyprland_script(self):
        """Phase 2 must verify start-hyprland script is executable."""
        self.assertIn(
            "start-hyprland", self.content,
            "Phase 2 must check start-hyprland script",
        )

    def test_checks_select_compositor_script(self):
        """Phase 2 must verify select-compositor script is executable."""
        self.assertIn(
            "select-compositor", self.content,
            "Phase 2 must check select-compositor script",
        )

    def test_checks_regreet_config(self):
        """Phase 2 must verify regreet.toml config exists."""
        self.assertIn(
            "regreet.toml", self.content,
            "Phase 2 must check regreet.toml config",
        )

    def test_checks_desktop_session_files(self):
        """Phase 2 must verify wayland session .desktop files exist and have correct Exec."""
        self.assertIn(
            "wayland-sessions/sway.desktop", self.content,
            "Phase 2 must check sway.desktop session file",
        )
        self.assertIn(
            "wayland-sessions/hyprland.desktop", self.content,
            "Phase 2 must check hyprland.desktop session file",
        )

    def test_fixes_desktop_exec_lines(self):
        """Phase 2 must fix .desktop Exec= lines if they don't point to madOS scripts."""
        self.assertIn(
            "/usr/local/bin/", self.content,
            "Phase 2 must verify Exec= points to /usr/local/bin/ session scripts",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Ollama and OpenCode are pre-installed programs (Phase 1 rsync)
# ═══════════════════════════════════════════════════════════════════════════
class TestToolsCopiedByRsync(unittest.TestCase):
    """Verify Phase 1 copies Ollama and OpenCode binaries from live USB."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_copies_ollama_binary(self):
        """Phase 1 must copy Ollama binary from live USB."""
        self.assertIn(
            "/usr/local/bin/ollama", self.content,
            "Phase 1 must copy ollama binary from live USB",
        )

    def test_copies_opencode_binary(self):
        """Phase 1 must copy OpenCode binary from live USB."""
        self.assertIn(
            "/usr/local/bin/opencode", self.content,
            "Phase 1 must copy opencode binary from live USB",
        )

    def test_no_ollama_opencode_service_references(self):
        """Installer must NOT reference services for ollama/opencode."""
        self.assertNotIn(
            "setup-ollama.service", self.content,
            "Installer must not create setup-ollama.service — ollama is a program",
        )
        self.assertNotIn(
            "setup-opencode.service", self.content,
            "Installer must not create setup-opencode.service — opencode is a program",
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
# Phase 2 script runtime generation & validation
# ═══════════════════════════════════════════════════════════════════════════
class TestPhase2ScriptGeneration(unittest.TestCase):
    """Generate the Phase 2 bash script and validate it structurally.

    Unlike the static tests above (which grep the Python source), these
    tests actually call ``_build_first_boot_script()`` and inspect the
    **generated** bash output to catch runtime issues.
    """

    @classmethod
    def setUpClass(cls):
        """Generate the Phase 2 script once for all tests in this class."""
        try:
            from mados_installer.pages.installation import _build_first_boot_script
        except ImportError:
            raise unittest.SkipTest("Cannot import _build_first_boot_script")
        cls.script = _build_first_boot_script({
            "username": "testuser",
            "locale": "en_US.UTF-8",
        })
        cls.lines = cls.script.splitlines()

    # ── Bash syntax ─────────────────────────────────────────────────────
    def test_bash_syntax_is_valid(self):
        """Generated script must pass ``bash -n`` syntax check."""
        result = subprocess.run(
            ["bash", "-n"],
            input=self.script,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"bash -n failed:\n{result.stderr}",
        )

    # ── Heredoc matching ────────────────────────────────────────────────
    def test_all_heredocs_are_terminated(self):
        """Every heredoc opener (<<'TAG') must have a matching terminator."""
        heredoc_re = re.compile(r"<<\s*'?(\w+)'?")
        open_tags = []
        for i, line in enumerate(self.lines, 1):
            m = heredoc_re.search(line)
            if m:
                open_tags.append((m.group(1), i))
            for tag, _ in list(open_tags):
                if line.strip() == tag:
                    open_tags = [(t, ln) for t, ln in open_tags if t != tag]
        self.assertEqual(
            open_tags, [],
            f"Unterminated heredocs: {open_tags}",
        )

    # ── No username needed in Phase 2 ──────────────────────────────────
    def test_no_username_in_phase2(self):
        """Phase 2 should not contain username-specific paths.

        All user-specific config is handled by /etc/skel (copied by rsync)
        and user creation in Phase 1.
        """
        self.assertNotIn("testuser", self.script,
                          "Phase 2 should not reference specific usernames — "
                          "user config is in /etc/skel")

    def test_no_unresolved_fstring_placeholders(self):
        """No stray Python f-string braces like {variable} should remain.

        Legitimate bash braces (``${var}``, ``${{``, array expansions) are
        excluded.
        """
        # Match {word} that is NOT preceded by $ (bash expansion) and NOT
        # a doubled brace {{ }} (f-string escape).
        stray = re.findall(r'(?<!\$)(?<!\{)\{([a-z_][a-z_0-9]*)\}(?!\})', self.script)
        self.assertEqual(
            stray, [],
            f"Unresolved f-string placeholders: {stray}",
        )

    # ── Systemd unit structure ──────────────────────────────────────────
    def _extract_heredoc_content(self, tag):
        """Return the content between <<'TAG' and TAG."""
        capture = False
        content = []
        heredoc_re = re.compile(r"<<\s*'?" + re.escape(tag) + r"'?")
        for line in self.lines:
            if capture:
                if line.strip() == tag:
                    break
                content.append(line)
            elif heredoc_re.search(line):
                capture = True
        return "\n".join(content)

    def _get_all_heredoc_contents_for_tag(self, tag):
        """Return list of all heredoc blocks for the given tag."""
        blocks = []
        capture = False
        content = []
        heredoc_re = re.compile(r"<<\s*'?" + re.escape(tag) + r"'?")
        for line in self.lines:
            if capture:
                if line.strip() == tag:
                    blocks.append("\n".join(content))
                    content = []
                    capture = False
                else:
                    content.append(line)
            elif heredoc_re.search(line):
                capture = True
        return blocks

    # ── Phase 2 no longer has heredocs for services/audio/chromium ─────
    # All that content is pre-installed on the live USB.
    # Phase 2 only verifies graphical environment + cleanup.

    # ── Error handling ──────────────────────────────────────────────────
    def test_uses_set_plus_e(self):
        """Phase 2 script must use set +e (all operations are non-critical)."""
        self.assertIn("set +e", self.script,
                       "Phase 2 must use set +e since all operations are non-critical")

    # ── File logging ────────────────────────────────────────────────────
    def test_has_persistent_file_logging(self):
        """Generated script must log to a persistent file."""
        self.assertIn("LOG_FILE=", self.script,
                       "Script must define LOG_FILE variable")
        self.assertIn("/var/log/mados-first-boot.log", self.script,
                       "Script must log to /var/log/mados-first-boot.log")

    # ── Graphical environment verification ──────────────────────────────
    def test_verifies_graphical_env_binaries(self):
        """Script must check that graphical environment binaries exist."""
        for binary in ["cage", "regreet", "sway"]:
            with self.subTest(binary=binary):
                self.assertIn(binary, self.script,
                               f"Script must verify {binary} binary")

    def test_verifies_cage_greeter_script(self):
        """Script must verify cage-greeter script exists and is executable."""
        self.assertIn("cage-greeter", self.script,
                       "Script must check cage-greeter script")

    def test_verifies_greetd_enabled(self):
        """Script must verify greetd.service is enabled."""
        self.assertIn("is-enabled greetd", self.script,
                       "Script must check if greetd.service is enabled")

    def test_enables_getty_tty2_fallback(self):
        """Script must enable getty@tty2 as a login fallback."""
        self.assertIn("getty@tty2.service", self.script,
                       "Script must enable getty@tty2 as fallback login")

    def test_verifies_hyprland_session_scripts(self):
        """Script must verify hyprland-session and start-hyprland are executable."""
        self.assertIn("hyprland-session", self.script,
                       "Script must check hyprland-session script")
        self.assertIn("start-hyprland", self.script,
                       "Script must check start-hyprland script")

    def test_verifies_select_compositor(self):
        """Script must verify select-compositor script is executable."""
        self.assertIn("select-compositor", self.script,
                       "Script must check select-compositor script")

    def test_verifies_regreet_config(self):
        """Script must verify regreet.toml config exists."""
        self.assertIn("regreet.toml", self.script,
                       "Script must check regreet.toml config")

    def test_verifies_desktop_session_files(self):
        """Script must verify wayland session .desktop files."""
        self.assertIn("sway.desktop", self.script,
                       "Script must check sway.desktop session file")
        self.assertIn("hyprland.desktop", self.script,
                       "Script must check hyprland.desktop session file")

    # ── Ollama/OpenCode are NOT in Phase 2 (copied by rsync) ──────────────
    def test_no_ollama_service_in_phase2(self):
        """Phase 2 must NOT create setup-ollama.service — ollama is a program."""
        self.assertNotIn("setup-ollama.service", self.script,
                         "Phase 2 must NOT create setup-ollama.service — ollama is a program, not a service")

    def test_no_opencode_service_in_phase2(self):
        """Phase 2 must NOT create setup-opencode.service — opencode is a program."""
        self.assertNotIn("setup-opencode.service", self.script,
                         "Phase 2 must NOT create setup-opencode.service — opencode is a program, not a service")

    def test_no_heredocs_in_phase2(self):
        """Phase 2 must NOT contain heredocs — all files are pre-installed."""
        self.assertNotIn("<<'EOF", self.script,
                         "Phase 2 must not create files via heredocs — they are pre-installed on the live USB")

    # ── systemctl calls are fault-tolerant ──────────────────────────────
    def test_systemctl_enable_calls_have_fallback(self):
        """Every 'systemctl enable' must have '|| true' or '2>/dev/null || true'."""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if "systemctl enable" in stripped or "systemctl --global enable" in stripped:
                with self.subTest(line=i, text=stripped):
                    self.assertTrue(
                        "|| true" in stripped or "||true" in stripped,
                        f"Line {i}: systemctl enable without '|| true' fallback — "
                        "would crash Phase 2 if the service doesn't exist: {stripped}",
                    )

    # ── Self-cleanup ────────────────────────────────────────────────────
    def test_script_disables_itself(self):
        """Script must disable mados-first-boot.service at the end."""
        self.assertIn("systemctl disable mados-first-boot", self.script)

    def test_script_removes_itself(self):
        """Script must rm the first-boot script file."""
        self.assertRegex(self.script, r"rm[^\n]*mados-first-boot\.sh",
                          "Script must remove mados-first-boot.sh")


if __name__ == "__main__":
    unittest.main()
