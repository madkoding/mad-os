#!/usr/bin/env python3
"""
Tests for madOS persistence and system shell scripts.

Validates syntax, structure, and configuration of bash scripts used for
persistent storage, system setup, and user-facing tools.

These tests run in CI without requiring actual hardware or a live USB
environment.
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
ETC_DIR = os.path.join(AIROOTFS, "etc")


# ═══════════════════════════════════════════════════════════════════════════
# Shell script syntax validation
# ═══════════════════════════════════════════════════════════════════════════
class TestShellScriptSyntax(unittest.TestCase):
    """Verify all shell scripts have valid bash syntax."""

    SHELL_SCRIPTS = [
        os.path.join(BIN_DIR, 'setup-persistence.sh'),
        os.path.join(BIN_DIR, 'mados-persistence'),
        os.path.join(BIN_DIR, 'setup-ohmyzsh.sh'),
        os.path.join(BIN_DIR, 'setup-opencode.sh'),
        os.path.join(BIN_DIR, 'mados-audio-init.sh'),
        os.path.join(BIN_DIR, 'toggle-demo-mode.sh'),
        os.path.join(AIROOTFS, 'usr', 'local', 'lib', 'mados-media-helper.sh'),
    ]

    def test_all_scripts_compile(self):
        """Every shell script should pass bash -n syntax check."""
        for script in self.SHELL_SCRIPTS:
            if not os.path.exists(script):
                continue
            with self.subTest(script=os.path.basename(script)):
                result = subprocess.run(
                    ['bash', '-n', script],
                    capture_output=True, text=True,
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"Syntax error in {os.path.basename(script)}:\n{result.stderr}"
                )


class TestShellScriptShebangs(unittest.TestCase):
    """Verify shell scripts have proper shebangs."""

    def _get_shell_scripts(self):
        scripts = []
        for fname in os.listdir(BIN_DIR):
            fpath = os.path.join(BIN_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, 'rb') as f:
                first_bytes = f.read(4)
            if first_bytes[:2] == b'#!':
                with open(fpath) as f:
                    first_line = f.readline().strip()
                if 'bash' in first_line or 'sh' in first_line:
                    scripts.append(fpath)
        return scripts

    def test_shebangs_valid(self):
        for script in self._get_shell_scripts():
            with self.subTest(script=os.path.basename(script)):
                with open(script) as f:
                    shebang = f.readline().strip()
                self.assertTrue(
                    shebang.startswith('#!'),
                    f"{os.path.basename(script)}: Missing shebang"
                )
                self.assertTrue(
                    'bash' in shebang or 'sh' in shebang,
                    f"{os.path.basename(script)}: Shebang doesn't reference bash/sh: {shebang}"
                )


# ═══════════════════════════════════════════════════════════════════════════
# setup-persistence.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupPersistenceScript(unittest.TestCase):
    """Validate structure and content of setup-persistence.sh."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, 'setup-persistence.sh')
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ''

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_uses_strict_mode(self):
        """Should use set -euo pipefail for safety."""
        self.assertIn('set -euo pipefail', self.content)

    def test_defines_persist_label(self):
        self.assertIn('PERSIST_LABEL=', self.content)

    def test_defines_persist_mount(self):
        self.assertIn('PERSIST_MOUNT=', self.content)

    def test_defines_log_file(self):
        self.assertIn('LOG_FILE=', self.content)

    def test_has_log_function(self):
        self.assertRegex(self.content, r'log\(\)\s*\{')

    def test_has_is_usb_device_function(self):
        self.assertRegex(self.content, r'is_usb_device\(\)\s*\{')

    def test_has_find_iso_device_function(self):
        self.assertRegex(self.content, r'find_iso_device\(\)\s*\{')

    def test_has_setup_persistence_function(self):
        self.assertRegex(self.content, r'setup_persistence\(\)\s*\{')

    def test_overlay_dirs_defined(self):
        self.assertIn('OVERLAY_DIRS=', self.content)

    def test_references_archiso(self):
        """Should check for archiso boot mount point."""
        self.assertIn('/run/archiso', self.content)

    def test_has_is_optical_device_function(self):
        """Should have is_optical_device() to detect DVD/CD media."""
        self.assertRegex(self.content, r'is_optical_device\(\)\s*\{')

    def test_optical_device_checks_sr_pattern(self):
        """is_optical_device should check for /dev/sr* device names."""
        self.assertIn('sr*', self.content)

    def test_optical_device_checks_scsi_type(self):
        """is_optical_device should check SCSI device type 5 (CD-ROM)."""
        self.assertIn('"5"', self.content)

    def test_optical_detection_before_usb_check(self):
        """Optical media detection should happen before USB check in setup_persistence."""
        optical_pos = self.content.find('is_optical_device')
        usb_pos = self.content.find('is_usb_device "$iso_device"')
        self.assertNotEqual(optical_pos, -1, "Must have is_optical_device check")
        self.assertNotEqual(usb_pos, -1, "Must have is_usb_device check")
        self.assertLess(
            optical_pos, usb_pos,
            "Optical media detection must occur before USB check in setup_persistence",
        )

    def test_has_strip_partition_function(self):
        """Should have strip_partition() to handle nvme/mmcblk/standard devices."""
        self.assertRegex(self.content, r'strip_partition\(\)\s*\{')

    def test_strip_partition_handles_nvme(self):
        """strip_partition must handle nvme device names (nvme0n1p2 → nvme0n1)."""
        self.assertIn('nvme', self.content)
        self.assertIn('mmcblk', self.content)

    def test_is_usb_device_checks_removable_flag(self):
        """is_usb_device should check sysfs removable flag as fallback."""
        self.assertIn('/removable', self.content,
                      "is_usb_device must check sysfs removable flag")

    def test_find_iso_device_handles_loop_devices(self):
        """find_iso_device should resolve loop devices to backing device."""
        self.assertIn('losetup', self.content,
                      "find_iso_device must handle loop device resolution")

    def test_find_iso_device_validates_block_device(self):
        """find_iso_device should check that source is a block device."""
        # The -b check ensures we don't process non-block sources
        self.assertIn('-b "$raw_source"', self.content,
                      "find_iso_device must validate block device with -b")

    def test_setup_persistence_validates_block_device(self):
        """setup_persistence should validate iso_device is a block device."""
        self.assertIn('-b "$iso_device"', self.content,
                      "setup_persistence must validate device is a block device")

    def test_setup_persistence_waits_for_udev(self):
        """setup_persistence should wait for udev to settle before device detection."""
        udev_pos = self.content.find('udevadm settle')
        find_pos = self.content.find('find_iso_device')
        self.assertNotEqual(udev_pos, -1, "Must call udevadm settle")
        # The first udevadm settle should come before find_iso_device in setup_persistence
        # Find udevadm settle within the setup_persistence function
        setup_start = self.content.find('setup_persistence()')
        if setup_start != -1:
            setup_content = self.content[setup_start:]
            udev_in_setup = setup_content.find('udevadm settle')
            find_in_setup = setup_content.find('find_iso_device')
            self.assertNotEqual(udev_in_setup, -1, "setup_persistence must call udevadm settle")
            self.assertLess(
                udev_in_setup, find_in_setup,
                "udevadm settle must run before find_iso_device in setup_persistence",
            )

    def test_setup_persistence_has_debug_logging(self):
        """setup_persistence should log diagnostic info when device detection fails."""
        self.assertIn('Debug:', self.content,
                      "setup_persistence must include debug logging for diagnostics")


# ═══════════════════════════════════════════════════════════════════════════
# Persistence service configuration validation
# ═══════════════════════════════════════════════════════════════════════════
class TestPersistenceServiceConfig(unittest.TestCase):
    """Validate mados-persistence.service is correctly configured for boot."""

    def setUp(self):
        self.service_path = os.path.join(
            ETC_DIR, 'systemd', 'system', 'mados-persistence.service'
        )
        if os.path.exists(self.service_path):
            with open(self.service_path) as f:
                self.content = f.read()
        else:
            self.content = ''

    def test_service_exists(self):
        self.assertTrue(os.path.exists(self.service_path))

    def test_service_has_timeout(self):
        """Service must have TimeoutStartSec to allow partition creation on slow USB."""
        self.assertIn('TimeoutStartSec=', self.content,
                      "Service needs TimeoutStartSec for slow USB devices")

    def test_service_timeout_sufficient(self):
        """TimeoutStartSec must be at least 120s for partition creation."""
        match = re.search(r'TimeoutStartSec=(\d+)', self.content)
        self.assertIsNotNone(match, "TimeoutStartSec must have a numeric value")
        timeout = int(match.group(1))
        self.assertGreaterEqual(timeout, 120,
                                "TimeoutStartSec must be >= 120s for partition creation")

    def test_service_after_udev(self):
        """Service should start after udev to ensure device nodes exist."""
        self.assertIn('systemd-udevd.service', self.content,
                      "Service must start after systemd-udevd.service")

    def test_service_condition_matches_script_guard(self):
        """Service ConditionPathExists must match script's execution guard.

        The service has ConditionPathExists=/run/archiso and the script
        checks 'if [ -d /run/archiso ]'. These must be consistent.
        """
        self.assertIn('ConditionPathExists=/run/archiso', self.content)
        # Also verify the script uses the same path
        script_path = os.path.join(BIN_DIR, 'setup-persistence.sh')
        with open(script_path) as f:
            script = f.read()
        self.assertIn('/run/archiso', script,
                      "Script guard must reference /run/archiso")

    def test_service_outputs_to_console(self):
        """Service should output to console+journal for debugging."""
        self.assertIn('journal+console', self.content,
                      "Service must output to journal+console for boot-time debugging")

    def test_service_wanted_by_sysinit(self):
        """Service must be wanted by sysinit.target (early boot)."""
        self.assertIn('WantedBy=sysinit.target', self.content)

    def test_service_is_enabled(self):
        """Service must have an enable symlink in sysinit.target.wants."""
        symlink = os.path.join(
            ETC_DIR, 'systemd', 'system',
            'sysinit.target.wants', 'mados-persistence.service'
        )
        self.assertTrue(
            os.path.islink(symlink),
            "mados-persistence.service must be enabled in sysinit.target.wants"
        )


# ═══════════════════════════════════════════════════════════════════════════
# mados-persistence tool validation
# ═══════════════════════════════════════════════════════════════════════════
class TestMadosPersistenceTool(unittest.TestCase):
    """Validate structure and content of mados-persistence CLI tool."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, 'mados-persistence')
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ''

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_has_check_live_env(self):
        self.assertRegex(self.content, r'check_live_env\(\)\s*\{')

    def test_has_find_persist_partition(self):
        self.assertRegex(self.content, r'find_persist_partition\(\)\s*\{')

    def test_has_show_status(self):
        self.assertRegex(self.content, r'show_status\(\)\s*\{')

    def test_has_enable_persistence(self):
        self.assertRegex(self.content, r'enable_persistence\(\)\s*\{')

    def test_has_disable_persistence(self):
        self.assertRegex(self.content, r'disable_persistence\(\)\s*\{')

    def test_has_remove_persistence(self):
        self.assertRegex(self.content, r'remove_persistence\(\)\s*\{')

    def test_defines_color_codes(self):
        for color in ('RED', 'GREEN', 'YELLOW', 'BLUE', 'NC'):
            with self.subTest(color=color):
                self.assertIn(f"{color}=", self.content)

    def test_has_print_helpers(self):
        for func in ('print_header', 'print_status', 'print_error',
                      'print_warning', 'print_info'):
            with self.subTest(func=func):
                self.assertRegex(self.content, rf'{func}\(\)\s*\{{')

    def test_supports_status_command(self):
        self.assertIn('status', self.content)

    def test_supports_enable_command(self):
        self.assertIn('enable', self.content)

    def test_supports_disable_command(self):
        self.assertIn('disable', self.content)

    def test_supports_remove_command(self):
        self.assertIn('remove', self.content)


# ═══════════════════════════════════════════════════════════════════════════
# setup-opencode.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupOpencodeScript(unittest.TestCase):
    """Validate structure of setup-opencode.sh."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, 'setup-opencode.sh')
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ''

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_references_npm(self):
        """Should install opencode via npm."""
        self.assertIn('npm', self.content)

    def test_references_opencode(self):
        self.assertIn('opencode', self.content)


# ═══════════════════════════════════════════════════════════════════════════
# setup-ohmyzsh.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupOhMyZshScript(unittest.TestCase):
    """Validate structure of setup-ohmyzsh.sh."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, 'setup-ohmyzsh.sh')
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ''

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_references_ohmyzsh(self):
        """Should reference oh-my-zsh repository or install."""
        content_lower = self.content.lower()
        self.assertTrue(
            'oh-my-zsh' in content_lower or 'ohmyzsh' in content_lower,
            "setup-ohmyzsh.sh should reference oh-my-zsh"
        )

    def test_references_skel(self):
        """Should install to /etc/skel for new users."""
        self.assertIn('/etc/skel', self.content)


# ═══════════════════════════════════════════════════════════════════════════
# Systemd service files validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSystemdServiceFiles(unittest.TestCase):
    """Validate systemd service files are properly structured."""

    def _get_service_files(self):
        service_dir = os.path.join(ETC_DIR, 'systemd', 'system')
        if not os.path.isdir(service_dir):
            return []
        services = []
        for fname in os.listdir(service_dir):
            fpath = os.path.join(service_dir, fname)
            # Skip symlinks (they point to system paths not in the repo)
            if fname.endswith('.service') and os.path.isfile(fpath) and not os.path.islink(fpath):
                services.append(fpath)
        return services

    def test_service_files_exist(self):
        """At least one systemd service should be defined."""
        services = self._get_service_files()
        self.assertGreater(len(services), 0)

    def test_service_files_have_unit_section(self):
        for svc in self._get_service_files():
            with self.subTest(service=os.path.basename(svc)):
                with open(svc) as f:
                    content = f.read()
                self.assertIn('[Unit]', content,
                              f"{os.path.basename(svc)} missing [Unit] section")

    def test_service_files_have_service_section(self):
        for svc in self._get_service_files():
            with self.subTest(service=os.path.basename(svc)):
                with open(svc) as f:
                    content = f.read()
                # Timer units won't have [Service], but .service files should
                if svc.endswith('.service'):
                    self.assertIn('[Service]', content,
                                  f"{os.path.basename(svc)} missing [Service] section")

    def test_service_files_have_description(self):
        for svc in self._get_service_files():
            with self.subTest(service=os.path.basename(svc)):
                with open(svc) as f:
                    content = f.read()
                self.assertRegex(content, r'Description=.+',
                                 f"{os.path.basename(svc)} missing Description")


# ═══════════════════════════════════════════════════════════════════════════
# Welcome script validation
# ═══════════════════════════════════════════════════════════════════════════
class TestWelcomeScript(unittest.TestCase):
    """Validate mados-welcome.sh profile script."""

    def setUp(self):
        self.script_path = os.path.join(ETC_DIR, 'profile.d', 'mados-welcome.sh')
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ''

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_has_shebang_or_comment(self):
        first_line = self.content.split('\n')[0] if self.content else ''
        self.assertTrue(
            first_line.startswith('#'),
            "Welcome script should start with a comment or shebang"
        )

    def test_valid_bash_syntax(self):
        if not os.path.exists(self.script_path):
            self.skipTest("Script not found")
        result = subprocess.run(
            ['bash', '-n', self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0,
                         f"Syntax error:\n{result.stderr}")


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestProfileDef(unittest.TestCase):
    """Validate profiledef.sh archiso configuration."""

    def setUp(self):
        self.script_path = os.path.join(REPO_DIR, 'profiledef.sh')
        with open(self.script_path) as f:
            self.content = f.read()

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_valid_bash_syntax(self):
        result = subprocess.run(
            ['bash', '-n', self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0,
                         f"Syntax error:\n{result.stderr}")

    def test_defines_iso_name(self):
        self.assertRegex(self.content, r'iso_name=')

    def test_defines_iso_publisher(self):
        self.assertRegex(self.content, r'iso_publisher=')

    def test_defines_file_permissions(self):
        self.assertIn('file_permissions', self.content)


# ═══════════════════════════════════════════════════════════════════════════
# packages.x86_64 validation
# ═══════════════════════════════════════════════════════════════════════════
class TestPackagesFile(unittest.TestCase):
    """Validate packages.x86_64 ISO package list."""

    def setUp(self):
        pkg_file = os.path.join(REPO_DIR, 'packages.x86_64')
        with open(pkg_file) as f:
            self.lines = f.readlines()
        self.packages = [
            line.strip() for line in self.lines
            if line.strip() and not line.strip().startswith('#')
        ]

    def test_not_empty(self):
        self.assertGreater(len(self.packages), 0)

    def test_no_duplicate_packages(self):
        seen = set()
        for pkg in self.packages:
            self.assertNotIn(pkg, seen, f"Duplicate package: {pkg}")
            seen.add(pkg)

    def test_essential_packages(self):
        """Live ISO should include core packages."""
        essential = ['base', 'linux', 'linux-firmware', 'grub',
                     'networkmanager', 'python']
        for pkg in essential:
            with self.subTest(package=pkg):
                self.assertIn(pkg, self.packages)

    def test_valid_package_names(self):
        pattern = re.compile(r'^[a-z0-9][a-z0-9._+-]*$')
        for pkg in self.packages:
            with self.subTest(package=pkg):
                self.assertRegex(pkg, pattern)

    def test_no_trailing_whitespace(self):
        for i, line in enumerate(self.lines, 1):
            if line.strip():
                with self.subTest(line=i):
                    self.assertEqual(line.rstrip('\n'), line.rstrip(),
                                     f"Line {i} has trailing whitespace")


# ═══════════════════════════════════════════════════════════════════════════
# mados-media-helper.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestMediaHelperScript(unittest.TestCase):
    """Validate structure and content of mados-media-helper.sh."""

    def setUp(self):
        self.script_path = os.path.join(
            AIROOTFS, 'usr', 'local', 'lib', 'mados-media-helper.sh'
        )
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ''

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_valid_bash_syntax(self):
        """Should pass bash -n syntax check."""
        result = subprocess.run(
            ['bash', '-n', self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Syntax error in mados-media-helper.sh:\n{result.stderr}"
        )

    def test_has_is_optical_media_function(self):
        """Should have is_optical_media() function."""
        self.assertRegex(self.content, r'is_optical_media\(\)\s*\{')

    def test_has_has_persistence_function(self):
        """Should have has_persistence() function."""
        self.assertRegex(self.content, r'has_persistence\(\)\s*\{')

    def test_has_can_install_software_function(self):
        """Should have can_install_software() function."""
        self.assertRegex(self.content, r'can_install_software\(\)\s*\{')

    def test_optical_media_checks_sr_devices(self):
        """is_optical_media should detect /dev/sr* devices."""
        self.assertIn('/dev/sr', self.content)

    def test_optical_media_checks_scsi_type(self):
        """is_optical_media should check SCSI type 5 (CD-ROM)."""
        self.assertIn('"5"', self.content)

    def test_optical_media_checks_udevadm(self):
        """is_optical_media should check ID_CDROM via udevadm."""
        self.assertIn('ID_CDROM', self.content)

    def test_can_install_checks_persistence(self):
        """can_install_software should check has_persistence."""
        self.assertIn('has_persistence', self.content)

    def test_can_install_checks_optical(self):
        """can_install_software should check is_optical_media."""
        self.assertIn('is_optical_media', self.content)

    def test_allows_install_outside_live_env(self):
        """can_install_software should allow installs outside live environment."""
        self.assertIn('/run/archiso', self.content)


# ═══════════════════════════════════════════════════════════════════════════
# Setup scripts DVD/CD detection validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupScriptsDvdDetection(unittest.TestCase):
    """Validate that setup scripts check for optical media before installing."""

    SETUP_SCRIPTS = [
        'setup-opencode.sh',
        'setup-ollama.sh',
        'setup-ohmyzsh.sh',
    ]

    def _read_script(self, name):
        path = os.path.join(BIN_DIR, name)
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ''

    def test_scripts_source_media_helper(self):
        """Setup scripts should source mados-media-helper.sh."""
        for script in self.SETUP_SCRIPTS:
            with self.subTest(script=script):
                content = self._read_script(script)
                self.assertIn(
                    'mados-media-helper.sh', content,
                    f"{script} must reference mados-media-helper.sh",
                )

    def test_scripts_check_can_install_software(self):
        """Setup scripts should call can_install_software before installing."""
        for script in self.SETUP_SCRIPTS:
            with self.subTest(script=script):
                content = self._read_script(script)
                self.assertIn(
                    'can_install_software', content,
                    f"{script} must check can_install_software",
                )

    def test_scripts_exit_zero_on_dvd(self):
        """Setup scripts should exit 0 (not fail) when on DVD."""
        for script in self.SETUP_SCRIPTS:
            with self.subTest(script=script):
                content = self._read_script(script)
                # The DVD check block should end with exit 0
                self.assertIn(
                    'exit 0', content,
                    f"{script} must exit 0 when skipping DVD install",
                )

    def test_dvd_check_before_install(self):
        """DVD media check must happen before any install attempt."""
        for script in self.SETUP_SCRIPTS:
            with self.subTest(script=script):
                content = self._read_script(script)
                dvd_pos = content.find('can_install_software')
                install_pos = content.find('curl')
                if install_pos == -1:
                    install_pos = content.find('git clone')
                self.assertNotEqual(dvd_pos, -1, f"{script} must check can_install_software")
                self.assertNotEqual(install_pos, -1, f"{script} must have install logic")
                self.assertLess(
                    dvd_pos, install_pos,
                    f"{script}: DVD check must come before install attempt",
                )


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh media helper permissions
# ═══════════════════════════════════════════════════════════════════════════
class TestProfiledefMediaHelperPermissions(unittest.TestCase):
    """Validate profiledef.sh includes permissions for mados-media-helper.sh."""

    def setUp(self):
        profiledef = os.path.join(REPO_DIR, 'profiledef.sh')
        with open(profiledef) as f:
            self.content = f.read()

    def test_media_helper_has_permissions(self):
        """profiledef.sh should set permissions for mados-media-helper.sh."""
        self.assertIn(
            'mados-media-helper.sh', self.content,
            "profiledef.sh must include permissions for mados-media-helper.sh",
        )

    def test_media_helper_executable(self):
        """mados-media-helper.sh should have executable permissions."""
        pattern = re.compile(
            r'\["/usr/local/lib/mados-media-helper\.sh"\]="0:0:755"'
        )
        self.assertRegex(
            self.content, pattern,
            "mados-media-helper.sh must have 0:0:755 permissions",
        )


if __name__ == '__main__':
    unittest.main()
