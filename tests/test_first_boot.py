#!/usr/bin/env python3
"""
Tests for madOS post-installation configuration.

Validates the installer's chroot configuration script that runs during
installation.  All packages, services, scripts, and config files are
pre-installed on the live USB and copied via rsync.  The chroot script
enables services and verifies the graphical environment.

There is no Phase 2 / first-boot service — everything is done in a single
installation pass.

These tests verify:
1. The config script has valid structure
2. Services are enabled correctly
3. Pre-installed files exist (audio, Chromium, Oh My Zsh)
4. Graphical environment verification is present
5. No internet downloads occur during installation
6. No redundant setup services for pre-installed programs
"""

import os
import re
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
# No Phase 2 / first-boot service should exist
# ═══════════════════════════════════════════════════════════════════════════
class TestNoFirstBootService(unittest.TestCase):
    """Verify there is no Phase 2 / first-boot service in the installer."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_no_first_boot_service(self):
        """Installer must NOT create mados-first-boot.service."""
        self.assertNotIn(
            "mados-first-boot.service", self.content,
            "No first-boot service should exist — all config is done in chroot",
        )

    def test_no_first_boot_script(self):
        """Installer must NOT create mados-first-boot.sh."""
        self.assertNotIn(
            "mados-first-boot.sh", self.content,
            "No first-boot script should exist — all config is done in chroot",
        )

    def test_no_build_first_boot_function(self):
        """Installer must NOT have _build_first_boot_script function."""
        self.assertNotIn(
            "def _build_first_boot_script", self.content,
            "No _build_first_boot_script function should exist",
        )

    def test_no_phase2_references(self):
        """Installer must NOT reference 'Phase 2'."""
        self.assertNotIn(
            "Phase 2", self.content,
            "No Phase 2 references should exist in the installer",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Service enablement — in chroot config script
# ═══════════════════════════════════════════════════════════════════════════
class TestServiceEnablement(unittest.TestCase):
    """Verify services are enabled in the chroot config script."""

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


# No redundant setup scripts for pre-installed programs
# ═══════════════════════════════════════════════════════════════════════════
class TestNoRedundantSetupScripts(unittest.TestCase):
    """Verify installer does NOT create setup scripts for pre-installed programs."""

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


# ═══════════════════════════════════════════════════════════════════════════
# Installer is fully offline (no downloads during installation)
# ═══════════════════════════════════════════════════════════════════════════
class TestInstallerFullyOffline(unittest.TestCase):
    """Verify the installer does NOT download anything from the internet."""

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

    def test_no_internet_check(self):
        """Installer must NOT check internet availability."""
        self.assertNotIn(
            "INTERNET_AVAILABLE", self.content,
            "Installer must not use INTERNET_AVAILABLE — it is 100% offline",
        )

    def test_no_git_clone(self):
        """Installer must NOT clone repos (everything comes from the ISO)."""
        self.assertNotIn(
            "git clone", self.content,
            "Installer must not git clone anything — everything comes from the ISO",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Graphical environment verification (now in chroot config script)
# ═══════════════════════════════════════════════════════════════════════════
class TestGraphicalEnvironmentVerification(unittest.TestCase):
    """Verify the config script checks graphical environment components."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_checks_cage_binary(self):
        """Config script must verify cage binary exists."""
        self.assertIn(
            "cage", self.content,
            "Config script must check for cage binary",
        )

    def test_checks_regreet_binary(self):
        """Config script must verify regreet binary exists."""
        self.assertIn(
            "regreet", self.content,
            "Config script must check for regreet binary",
        )

    def test_checks_cage_greeter_script(self):
        """Config script must verify cage-greeter script is executable."""
        self.assertIn(
            "cage-greeter", self.content,
            "Config script must check cage-greeter script",
        )

    def test_checks_greetd_service_enabled(self):
        """Config script must verify greetd.service is enabled."""
        self.assertIn(
            "greetd.service", self.content,
            "Config script must check greetd.service status",
        )

    def test_enables_getty_tty2_fallback(self):
        """Config script must enable getty@tty2 as a fallback login."""
        self.assertIn(
            "getty@tty2.service", self.content,
            "Config script must enable getty@tty2 as fallback login",
        )

    def test_checks_hyprland_session_script(self):
        """Config script must verify hyprland-session script is executable."""
        self.assertIn(
            "hyprland-session", self.content,
            "Config script must check hyprland-session script",
        )

    def test_checks_start_hyprland_script(self):
        """Config script must verify start-hyprland script is executable."""
        self.assertIn(
            "start-hyprland", self.content,
            "Config script must check start-hyprland script",
        )

    def test_checks_select_compositor_script(self):
        """Config script must verify select-compositor script is executable."""
        self.assertIn(
            "select-compositor", self.content,
            "Config script must check select-compositor script",
        )

    def test_checks_regreet_config(self):
        """Config script must verify regreet.toml config exists."""
        self.assertIn(
            "regreet.toml", self.content,
            "Config script must check regreet.toml config",
        )

    def test_checks_desktop_session_files(self):
        """Config script must verify wayland session .desktop files exist."""
        self.assertIn(
            "wayland-sessions/sway.desktop", self.content,
            "Config script must check sway.desktop session file",
        )
        self.assertIn(
            "wayland-sessions/hyprland.desktop", self.content,
            "Config script must check hyprland.desktop session file",
        )

    def test_fixes_desktop_exec_lines(self):
        """Config script must fix .desktop Exec= lines if they don't point to madOS scripts."""
        self.assertIn(
            "/usr/local/bin/", self.content,
            "Config script must verify Exec= points to /usr/local/bin/ session scripts",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Ollama and OpenCode are pre-installed programs (rsync)
# ═══════════════════════════════════════════════════════════════════════════
class TestToolsCopiedByRsync(unittest.TestCase):
    """Verify the installer copies Ollama and OpenCode binaries from live USB."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_copies_ollama_binary(self):
        """Installer must copy Ollama binary from live USB."""
        self.assertIn(
            "/usr/local/bin/ollama", self.content,
            "Installer must copy ollama binary from live USB",
        )

    def test_copies_opencode_binary(self):
        """Installer must copy OpenCode binary from live USB."""
        self.assertIn(
            "/usr/local/bin/opencode", self.content,
            "Installer must copy opencode binary from live USB",
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
# Config script structure validation
# ═══════════════════════════════════════════════════════════════════════════
class TestConfigScriptStructure(unittest.TestCase):
    """Validate the config script has proper structure."""

    def setUp(self):
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        if not os.path.isfile(install_py):
            self.skipTest("installation.py not found")
        with open(install_py) as f:
            self.content = f.read()

    def test_progress_markers_use_8_steps(self):
        """Config script must use 8 progress steps (no Phase 2)."""
        # Find all PROGRESS markers
        markers = re.findall(r'\[PROGRESS\s+(\d+)/(\d+)\]', self.content)
        self.assertGreater(len(markers), 0, "Must have PROGRESS markers")
        for step, total in markers:
            with self.subTest(step=step):
                self.assertEqual(total, "8",
                                 f"PROGRESS {step}/{total} should be {step}/8")

    def test_no_progress_9_of_9(self):
        """Config script must NOT have a 9th progress step."""
        self.assertNotIn(
            "PROGRESS 9/", self.content,
            "Config script must not have a 9th progress step",
        )


if __name__ == "__main__":
    unittest.main()
