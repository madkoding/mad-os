#!/usr/bin/env python3
"""
Tests for Meli Tech Demo integration in madOS.

Validates that the Meli Tech Demo game (by WilliamsMyGL, itch.io) is properly
integrated into the live USB environment:
  - Launcher script exists and checks for Vulkan/3D acceleration
  - Setup/download script exists with correct structure
  - Systemd service is properly configured
  - Desktop entry is present
  - File permissions are set in profiledef.sh
  - Python download module exists
  - Only launches when 3D acceleration is available
"""

import os
import re
import subprocess
import unittest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")
WANTS_DIR = os.path.join(SYSTEMD_DIR, "multi-user.target.wants")
APPS_DIR = os.path.join(AIROOTFS, "usr", "share", "applications")
PROFILEDEF = os.path.join(REPO_DIR, "profiledef.sh")
PACKAGES = os.path.join(REPO_DIR, "packages.x86_64")


# ═══════════════════════════════════════════════════════════════════════════
# Launcher script: mados-meli-demo
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliDemoLauncher(unittest.TestCase):
    """Verify the mados-meli-demo launcher script."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "mados-meli-demo")
        if not os.path.isfile(self.script_path):
            self.skipTest("mados-meli-demo script not found")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_script_exists(self):
        """mados-meli-demo launcher must exist."""
        self.assertTrue(os.path.isfile(self.script_path))

    def test_has_shebang(self):
        """Launcher must start with a bash shebang."""
        first_line = self.content.splitlines()[0]
        self.assertTrue(first_line.startswith("#!"), "Must start with #!")
        self.assertIn("bash", first_line, "Must use bash")

    def test_valid_bash_syntax(self):
        """Launcher must have valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )

    def test_checks_vulkan_support(self):
        """Launcher must check for Vulkan/3D support before running."""
        self.assertIn(
            "check_vulkan_support", self.content,
            "Must have a check_vulkan_support function",
        )

    def test_checks_drm_render_node(self):
        """Launcher must check for DRM render node (/dev/dri/renderD128)."""
        self.assertIn(
            "/dev/dri/renderD128", self.content,
            "Must check for DRM render node",
        )

    def test_checks_vulkan_icd(self):
        """Launcher must check for Vulkan ICD driver files."""
        self.assertIn(
            "vulkan/icd.d", self.content,
            "Must check for Vulkan ICD driver files",
        )

    def test_checks_nomodeset(self):
        """Launcher must check for nomodeset kernel parameter."""
        self.assertIn(
            "nomodeset", self.content,
            "Must detect nomodeset (disables GPU acceleration)",
        )

    def test_uses_detect_legacy_hardware(self):
        """Launcher should use detect-legacy-hardware for 3D detection."""
        self.assertIn(
            "detect-legacy-hardware", self.content,
            "Must reference detect-legacy-hardware script",
        )

    def test_has_game_install_dir(self):
        """Launcher must define an installation directory."""
        self.assertRegex(
            self.content, r'INSTALL_DIR=.*meli',
            "Must define INSTALL_DIR for the game",
        )

    def test_has_persistence_support(self):
        """Launcher must check persistence storage for the game."""
        self.assertIn(
            "/mnt/persistence", self.content,
            "Must support persistence storage location",
        )

    def test_offers_download_if_not_installed(self):
        """Launcher must offer to download the game if not installed."""
        self.assertIn(
            "setup-meli-demo", self.content,
            "Must reference the setup/download script",
        )

    def test_sets_sdl_video_driver(self):
        """Launcher must set SDL_VIDEODRIVER for compatibility."""
        self.assertIn(
            "SDL_VIDEODRIVER", self.content,
            "Must configure SDL_VIDEODRIVER for Wayland/X11",
        )

    def test_find_game_dir_function(self):
        """Launcher must have a function to find the game directory."""
        self.assertIn(
            "find_game_dir", self.content,
            "Must have find_game_dir function",
        )

    def test_shows_no_vulkan_message(self):
        """Launcher must show a message when Vulkan is not available."""
        self.assertIn(
            "show_no_vulkan_message", self.content,
            "Must have show_no_vulkan_message function",
        )

    def test_uses_swaynag_for_notifications(self):
        """Launcher should use swaynag for graphical notifications."""
        self.assertIn(
            "swaynag", self.content,
            "Must use swaynag for user notifications",
        )

    def test_uses_exec_for_launch(self):
        """Launcher must use exec to replace shell process with game."""
        self.assertRegex(
            self.content, r'\bexec\b.*\$game_exe',
            "Must exec the game executable (replace shell process)",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Setup/download script: setup-meli-demo.sh
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliDemoSetup(unittest.TestCase):
    """Verify the setup-meli-demo.sh download/install script."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-meli-demo.sh")
        if not os.path.isfile(self.script_path):
            self.skipTest("setup-meli-demo.sh script not found")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_script_exists(self):
        """setup-meli-demo.sh must exist."""
        self.assertTrue(os.path.isfile(self.script_path))

    def test_has_shebang(self):
        """Setup script must start with a bash shebang."""
        first_line = self.content.splitlines()[0]
        self.assertTrue(first_line.startswith("#!"), "Must start with #!")
        self.assertIn("bash", first_line, "Must use bash")

    def test_valid_bash_syntax(self):
        """Setup script must have valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )

    def test_has_itch_io_url(self):
        """Setup script must contain the itch.io game URL."""
        self.assertIn(
            "williamsmygl.itch.io", self.content,
            "Must contain the itch.io game URL",
        )

    def test_checks_network_connectivity(self):
        """Setup script must verify network connectivity."""
        self.assertIn(
            "curl", self.content,
            "Must use curl to check network connectivity",
        )

    def test_checks_read_only_media(self):
        """Setup script must check for read-only media (DVD/CD)."""
        self.assertIn(
            "mados-media-helper.sh", self.content,
            "Must reference mados-media-helper.sh",
        )

    def test_checks_already_installed(self):
        """Setup script must check if game is already installed."""
        self.assertIn(
            "check_already_installed", self.content,
            "Must have check_already_installed function",
        )

    def test_checks_disk_space(self):
        """Setup script must check available disk space."""
        self.assertIn(
            "MIN_SPACE_MB", self.content,
            "Must define minimum space requirement",
        )

    def test_prefers_persistence(self):
        """Setup script must prefer persistence storage."""
        self.assertIn(
            "/mnt/persistence", self.content,
            "Must check for persistence storage",
        )

    def test_provides_manual_download_instructions(self):
        """Setup script must provide manual download instructions on failure."""
        self.assertIn(
            "Descarga manual", self.content,
            "Must provide manual download instructions",
        )

    def test_uses_python_download_module(self):
        """Setup script must use the Python download module."""
        self.assertIn(
            "mados_meli_demo", self.content,
            "Must use mados_meli_demo Python module",
        )

    def test_extracts_zip_with_fallback(self):
        """Setup script must have ZIP extraction with fallback."""
        self.assertIn("bsdtar", self.content, "Must try bsdtar for extraction")
        # Should have at least one fallback
        self.assertTrue(
            "unzip" in self.content or "zipfile" in self.content,
            "Must have a fallback extraction method (unzip or Python zipfile)",
        )

    def test_makes_files_executable(self):
        """Setup script must make game files executable after extraction."""
        self.assertIn(
            "chmod +x", self.content,
            "Must chmod executable files after extraction",
        )

    def test_finds_game_executable(self):
        """Setup script must auto-detect the game executable."""
        self.assertIn(
            "find_game_executable", self.content,
            "Must have find_game_executable function",
        )

    def test_exits_zero_on_failure(self):
        """Setup script should exit 0 for non-critical failures (systemd compat)."""
        # Check that network failures don't break the service
        self.assertRegex(
            self.content,
            r'No hay conexión a Internet[\s\S]*?return 0',
            "Must return 0 when network unavailable (systemd service safety)",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Python download module: mados_meli_demo
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliDownloadModule(unittest.TestCase):
    """Verify the mados_meli_demo Python download module."""

    def setUp(self):
        self.module_dir = os.path.join(LIB_DIR, "mados_meli_demo")

    def test_module_directory_exists(self):
        """mados_meli_demo module directory must exist."""
        self.assertTrue(
            os.path.isdir(self.module_dir),
            "mados_meli_demo module directory must exist",
        )

    def test_init_file_exists(self):
        """Module must have __init__.py."""
        init_path = os.path.join(self.module_dir, "__init__.py")
        self.assertTrue(
            os.path.isfile(init_path),
            "__init__.py must exist in mados_meli_demo",
        )

    def test_download_itch_module_exists(self):
        """download_itch.py module must exist."""
        mod_path = os.path.join(self.module_dir, "download_itch.py")
        self.assertTrue(
            os.path.isfile(mod_path),
            "download_itch.py must exist in mados_meli_demo",
        )

    def test_download_itch_is_valid_python(self):
        """download_itch.py must have valid Python syntax."""
        mod_path = os.path.join(self.module_dir, "download_itch.py")
        result = subprocess.run(
            ["python3", "-c", f"import py_compile; py_compile.compile('{mod_path}', doraise=True)"],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Python syntax error: {result.stderr}",
        )

    def test_download_itch_has_main_function(self):
        """download_itch.py must define download_from_itch function."""
        mod_path = os.path.join(self.module_dir, "download_itch.py")
        with open(mod_path) as f:
            content = f.read()
        self.assertIn(
            "def download_from_itch", content,
            "Must define download_from_itch function",
        )

    def test_download_itch_uses_stdlib_only(self):
        """download_itch.py must use only standard library (no pip deps)."""
        mod_path = os.path.join(self.module_dir, "download_itch.py")
        with open(mod_path) as f:
            content = f.read()
        # Check that no third-party imports are used
        import_lines = [
            line.strip() for line in content.splitlines()
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        stdlib_prefixes = {
            "http", "json", "os", "re", "sys", "urllib", "zipfile",
            "pathlib", "tempfile", "shutil", "io", "hashlib", "time",
            "html", "ssl", "socket", "collections", "functools",
        }
        for imp in import_lines:
            # Extract module name
            if imp.startswith("from "):
                mod_name = imp.split()[1].split(".")[0]
            else:
                mod_name = imp.split()[1].split(".")[0]
            self.assertIn(
                mod_name, stdlib_prefixes,
                f"Import '{imp}' uses non-stdlib module '{mod_name}'. "
                f"Only standard library is allowed.",
            )

    def test_download_itch_has_progress_tracking(self):
        """download_itch.py must show download progress."""
        mod_path = os.path.join(self.module_dir, "download_itch.py")
        with open(mod_path) as f:
            content = f.read()
        self.assertIn(
            "progress", content.lower(),
            "Must have progress tracking during download",
        )

    def test_download_itch_extracts_csrf(self):
        """download_itch.py must extract CSRF token from itch.io."""
        mod_path = os.path.join(self.module_dir, "download_itch.py")
        with open(mod_path) as f:
            content = f.read()
        self.assertIn(
            "csrf", content.lower(),
            "Must handle itch.io CSRF tokens",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Systemd service
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliDemoService(unittest.TestCase):
    """Verify the setup-meli-demo.service systemd unit."""

    def setUp(self):
        self.service_path = os.path.join(SYSTEMD_DIR, "setup-meli-demo.service")
        if not os.path.isfile(self.service_path):
            self.skipTest("setup-meli-demo.service not found")
        with open(self.service_path) as f:
            self.content = f.read()

    def test_service_exists(self):
        """setup-meli-demo.service must exist."""
        self.assertTrue(os.path.isfile(self.service_path))

    def test_service_is_oneshot(self):
        """Service must be Type=oneshot."""
        self.assertIn(
            "Type=oneshot", self.content,
            "Service must be Type=oneshot",
        )

    def test_service_after_network(self):
        """Service must start after network-online.target."""
        self.assertIn(
            "network-online.target", self.content,
            "Must start after network-online.target",
        )

    def test_service_after_persistence(self):
        """Service must start after persistence detection."""
        self.assertIn(
            "mados-persistence-detect", self.content,
            "Must start after mados-persistence-detect service",
        )

    def test_service_exec_start(self):
        """Service must call setup-meli-demo.sh."""
        self.assertIn(
            "setup-meli-demo.sh", self.content,
            "ExecStart must reference setup-meli-demo.sh",
        )

    def test_service_condition_drm(self):
        """Service must have a condition for DRM render node (3D present)."""
        self.assertIn(
            "renderD128", self.content,
            "Must check for DRM render node as a launch condition",
        )

    def test_service_condition_persistence(self):
        """Service must require persistence directory."""
        self.assertIn(
            "/mnt/persistence", self.content,
            "Must require persistence directory",
        )

    def test_service_has_timeout(self):
        """Service must have a generous timeout for download."""
        self.assertIn(
            "TimeoutStartSec", self.content,
            "Must set TimeoutStartSec for download time",
        )
        # Extract timeout value
        match = re.search(r'TimeoutStartSec=(\d+)', self.content)
        self.assertIsNotNone(match, "TimeoutStartSec must have a numeric value")
        timeout = int(match.group(1))
        self.assertGreaterEqual(
            timeout, 300,
            "Timeout must be at least 300s (5min) for ~400MB download",
        )

    def test_service_includes_pythonpath(self):
        """Service must set PYTHONPATH for the download module."""
        self.assertIn(
            "PYTHONPATH", self.content,
            "Must set PYTHONPATH for mados_meli_demo module",
        )

    def test_service_enabled_in_target(self):
        """Service must be enabled (symlinked in multi-user.target.wants)."""
        wants_link = os.path.join(WANTS_DIR, "setup-meli-demo.service")
        self.assertTrue(
            os.path.islink(wants_link) or os.path.isfile(wants_link),
            "setup-meli-demo.service must be enabled in multi-user.target.wants",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Desktop entry
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliDemoDesktopEntry(unittest.TestCase):
    """Verify the .desktop file for Meli Tech Demo."""

    def setUp(self):
        self.desktop_path = os.path.join(APPS_DIR, "mados-meli-demo.desktop")
        if not os.path.isfile(self.desktop_path):
            self.skipTest("mados-meli-demo.desktop not found")
        with open(self.desktop_path) as f:
            self.content = f.read()

    def test_desktop_file_exists(self):
        """Desktop entry must exist."""
        self.assertTrue(os.path.isfile(self.desktop_path))

    def test_has_desktop_entry_header(self):
        """Desktop file must have [Desktop Entry] header."""
        self.assertIn(
            "[Desktop Entry]", self.content,
            "Must have [Desktop Entry] section",
        )

    def test_has_name(self):
        """Desktop entry must have a Name."""
        self.assertIn("Name=", self.content, "Must have Name= field")
        self.assertIn("Meli", self.content, "Name must mention Meli")

    def test_exec_is_launcher(self):
        """Desktop entry Exec must call mados-meli-demo."""
        self.assertRegex(
            self.content, r'Exec=.*mados-meli-demo',
            "Exec must call mados-meli-demo launcher",
        )

    def test_has_game_category(self):
        """Desktop entry must be categorized as a Game."""
        self.assertIn(
            "Game", self.content,
            "Must be in Game category",
        )

    def test_terminal_false(self):
        """Desktop entry should not require a terminal."""
        self.assertIn(
            "Terminal=false", self.content,
            "Terminal must be false (game has its own window)",
        )

    def test_has_spanish_translation(self):
        """Desktop entry should have Spanish translation."""
        self.assertIn(
            "Name[es]=", self.content,
            "Should have Spanish name translation",
        )


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh permissions
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliDemoProfileDef(unittest.TestCase):
    """Verify file permissions are set in profiledef.sh."""

    def setUp(self):
        if not os.path.isfile(PROFILEDEF):
            self.skipTest("profiledef.sh not found")
        with open(PROFILEDEF) as f:
            self.content = f.read()

    def test_launcher_permissions(self):
        """mados-meli-demo must have 755 permissions in profiledef.sh."""
        self.assertIn(
            'mados-meli-demo', self.content,
            "mados-meli-demo must be in profiledef.sh",
        )
        self.assertRegex(
            self.content, r'mados-meli-demo.*755',
            "mados-meli-demo must have 755 permissions",
        )

    def test_setup_script_permissions(self):
        """setup-meli-demo.sh must have 755 permissions in profiledef.sh."""
        self.assertIn(
            'setup-meli-demo.sh', self.content,
            "setup-meli-demo.sh must be in profiledef.sh",
        )
        self.assertRegex(
            self.content, r'setup-meli-demo\.sh.*755',
            "setup-meli-demo.sh must have 755 permissions",
        )

    def test_python_module_permissions(self):
        """mados_meli_demo module must have permissions in profiledef.sh."""
        self.assertIn(
            'mados_meli_demo', self.content,
            "mados_meli_demo module must be in profiledef.sh",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Packages
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliDemoPackages(unittest.TestCase):
    """Verify required packages for Meli Tech Demo."""

    def setUp(self):
        if not os.path.isfile(PACKAGES):
            self.skipTest("packages.x86_64 not found")
        with open(PACKAGES) as f:
            self.packages = [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

    def test_vulkan_intel_present(self):
        """vulkan-intel must be in packages for Intel GPU Vulkan support."""
        self.assertIn("vulkan-intel", self.packages)

    def test_vulkan_radeon_present(self):
        """vulkan-radeon must be in packages for AMD GPU Vulkan support."""
        self.assertIn("vulkan-radeon", self.packages)

    def test_mesa_present(self):
        """mesa must be in packages for OpenGL/Vulkan base."""
        self.assertIn("mesa", self.packages)

    def test_unzip_present(self):
        """unzip must be in packages for game extraction."""
        self.assertIn("unzip", self.packages)

    def test_curl_present(self):
        """curl must be in packages for downloading."""
        self.assertIn("curl", self.packages)

    def test_python_present(self):
        """python must be in packages for download module."""
        self.assertIn("python", self.packages)


# ═══════════════════════════════════════════════════════════════════════════
# Vulkan 3D check logic simulation
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliVulkanCheckLogic(unittest.TestCase):
    """Verify the Vulkan check logic in the launcher script."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "mados-meli-demo")
        if not os.path.isfile(self.script_path):
            self.skipTest("mados-meli-demo script not found")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_nomodeset_blocks_game(self):
        """nomodeset in cmdline must prevent the game from launching."""
        # The script checks nomodeset FIRST before Vulkan check
        lines = self.content.splitlines()
        nomodeset_line = None
        vulkan_check_line = None
        for i, line in enumerate(lines):
            if "check_nomodeset" in line and "main" not in line.lower() and "function" not in line.lower() and "show" not in line.lower():
                if nomodeset_line is None:
                    nomodeset_line = i
            if "check_vulkan_support" in line and "main" not in line.lower() and "function" not in line.lower() and "!" in line:
                if vulkan_check_line is None:
                    vulkan_check_line = i

        self.assertIsNotNone(nomodeset_line, "Must have nomodeset check in main flow")
        self.assertIsNotNone(vulkan_check_line, "Must have vulkan check in main flow")
        self.assertLess(
            nomodeset_line, vulkan_check_line,
            "nomodeset check must come before Vulkan check",
        )

    def test_check_vulkan_support_checks_render_node_first(self):
        """check_vulkan_support must check render node as first step."""
        # Extract the function body
        func_match = re.search(
            r'check_vulkan_support\(\)\s*\{(.*?)\n\}',
            self.content, re.DOTALL,
        )
        self.assertIsNotNone(func_match, "Must define check_vulkan_support function")
        func_body = func_match.group(1)

        # First check should be renderD128
        first_check = re.search(r'renderD128|dri', func_body)
        self.assertIsNotNone(
            first_check,
            "First check in check_vulkan_support must be DRM render node",
        )

    def test_multiple_detection_methods(self):
        """check_vulkan_support must have multiple detection fallbacks."""
        methods_count = 0
        if "renderD128" in self.content:
            methods_count += 1
        if "vulkan/icd.d" in self.content:
            methods_count += 1
        if "vulkaninfo" in self.content:
            methods_count += 1
        if "detect-legacy-hardware" in self.content:
            methods_count += 1
        if "eglinfo" in self.content:
            methods_count += 1
        if "drm_driver" in self.content:
            methods_count += 1

        self.assertGreaterEqual(
            methods_count, 3,
            f"Must have at least 3 Vulkan/3D detection methods (found {methods_count})",
        )

    def test_drm_driver_check_includes_common_drivers(self):
        """DRM driver check must include common GPU driver names."""
        for driver in ["i915", "amdgpu", "nouveau"]:
            self.assertIn(
                driver, self.content,
                f"Must check for {driver} DRM driver",
            )

    def test_vm_3d_support(self):
        """Vulkan check must support VMs with 3D acceleration."""
        for vm_driver in ["vmwgfx", "virtio-gpu", "virgl"]:
            self.assertIn(
                vm_driver, self.content,
                f"Must recognize {vm_driver} as 3D-capable VM driver",
            )


# ═══════════════════════════════════════════════════════════════════════════
# Installer integration
# ═══════════════════════════════════════════════════════════════════════════
class TestMeliDemoInstallerIntegration(unittest.TestCase):
    """Verify Meli demo can be found by the system."""

    def test_setup_script_path_consistent(self):
        """Launcher and service must reference the same setup script path."""
        launcher_path = os.path.join(BIN_DIR, "mados-meli-demo")
        service_path = os.path.join(SYSTEMD_DIR, "setup-meli-demo.service")

        with open(launcher_path) as f:
            launcher_content = f.read()
        with open(service_path) as f:
            service_content = f.read()

        # Both must reference the same setup script
        self.assertIn("setup-meli-demo.sh", launcher_content)
        self.assertIn("setup-meli-demo.sh", service_content)

    def test_install_dir_consistent(self):
        """Launcher and setup script must use the same install directory."""
        launcher_path = os.path.join(BIN_DIR, "mados-meli-demo")
        setup_path = os.path.join(BIN_DIR, "setup-meli-demo.sh")

        with open(launcher_path) as f:
            launcher_content = f.read()
        with open(setup_path) as f:
            setup_content = f.read()

        # Extract INSTALL_DIR from both
        launcher_match = re.search(r'INSTALL_DIR="([^"]+)"', launcher_content)
        setup_match = re.search(r'INSTALL_DIR="([^"]+)"', setup_content)

        self.assertIsNotNone(launcher_match, "Launcher must define INSTALL_DIR")
        self.assertIsNotNone(setup_match, "Setup must define INSTALL_DIR")
        self.assertEqual(
            launcher_match.group(1), setup_match.group(1),
            "INSTALL_DIR must be the same in launcher and setup",
        )

    def test_executable_marker_consistent(self):
        """Launcher and setup must use the same executable marker."""
        launcher_path = os.path.join(BIN_DIR, "mados-meli-demo")
        setup_path = os.path.join(BIN_DIR, "setup-meli-demo.sh")

        with open(launcher_path) as f:
            launcher_content = f.read()
        with open(setup_path) as f:
            setup_content = f.read()

        launcher_match = re.search(r'EXECUTABLE_MARKER="([^"]+)"', launcher_content)
        setup_match = re.search(r'EXECUTABLE_MARKER="([^"]+)"', setup_content)

        self.assertIsNotNone(launcher_match)
        self.assertIsNotNone(setup_match)
        self.assertEqual(
            launcher_match.group(1), setup_match.group(1),
            "EXECUTABLE_MARKER must match between launcher and setup",
        )


if __name__ == "__main__":
    unittest.main()
