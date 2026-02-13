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


if __name__ == '__main__':
    unittest.main()
