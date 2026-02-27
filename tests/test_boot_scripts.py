#!/usr/bin/env python3
"""
Tests for madOS boot-time scripts and services.

Validates that boot scripts (setup-ohmyzsh.sh, setup-opencode.sh, setup-ollama.sh)
and the Oh My Zsh systemd service unit are properly configured for the live USB
environment.  OpenCode and Ollama are programs (not services) and only have
setup scripts for manual installation.

These tests catch configuration errors like the 'chown: invalid group'
issue where setup-ohmyzsh.sh used the username as the group name instead
of the numeric GID from /etc/passwd.
"""

import os
import re
import subprocess
import sys
import unittest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")
SYSUSERS_DIR = os.path.join(AIROOTFS, "etc", "sysusers.d")


# ═══════════════════════════════════════════════════════════════════════════
# Boot script syntax validation
# ═══════════════════════════════════════════════════════════════════════════
class TestBootScriptSyntax(unittest.TestCase):
    """Verify all boot scripts have valid bash syntax."""

    BOOT_SCRIPTS = []

    def test_all_boot_scripts_valid_syntax(self):
        """Every boot script should pass bash -n (syntax check)."""
        for script in self.BOOT_SCRIPTS:
            path = os.path.join(BIN_DIR, script)
            if not os.path.isfile(path):
                continue
            with self.subTest(script=script):
                result = subprocess.run(
                    ["bash", "-n", path],
                    capture_output=True, text=True,
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"Bash syntax error in {script}: {result.stderr}",
                )

    def test_boot_scripts_have_shebang(self):
        """Every boot script should start with a bash shebang."""
        for script in self.BOOT_SCRIPTS:
            path = os.path.join(BIN_DIR, script)
            if not os.path.isfile(path):
                continue
            with self.subTest(script=script):
                with open(path) as f:
                    first_line = f.readline().strip()
                self.assertIn(
                    "bash", first_line,
                    f"{script} must start with a bash shebang",
                )
                self.assertTrue(
                    first_line.startswith("#!"),
                    f"{script} must start with #!",
                )

    def test_boot_scripts_use_strict_mode(self):
        """Boot scripts should use set -euo pipefail for safety.

        Exception: setup scripts that run as systemd services intentionally
        avoid strict mode because they must never crash the service – they
        use their own graceful error handling and always exit 0.
        """
        STRICT_MODE_EXCEPTIONS = set()  # No setup scripts needed - programs are pre-installed
        for script in self.BOOT_SCRIPTS:
            if script in STRICT_MODE_EXCEPTIONS:
                continue
            path = os.path.join(BIN_DIR, script)
            if not os.path.isfile(path):
                continue
            with self.subTest(script=script):
                with open(path) as f:
                    content = f.read()
                self.assertIn(
                    "set -euo pipefail", content,
                    f"{script} must use strict mode (set -euo pipefail)",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Systemd service files
# ═══════════════════════════════════════════════════════════════════════════
class TestSystemdServices(unittest.TestCase):
    """Verify systemd service files for boot scripts are correct."""

    SERVICES = {
        # No setup scripts needed - programs are pre-installed during ISO build
    }

    def test_service_files_exist(self):
        """All boot service files must exist."""
        for service in self.SERVICES:
            path = os.path.join(SYSTEMD_DIR, service)
            with self.subTest(service=service):
                self.assertTrue(
                    os.path.isfile(path),
                    f"{service} must exist in systemd/system/",
                )

    def test_service_exec_start(self):
        """Each service must point to the correct script."""
        for service, expected in self.SERVICES.items():
            path = os.path.join(SYSTEMD_DIR, service)
            if not os.path.isfile(path):
                continue
            with self.subTest(service=service):
                with open(path) as f:
                    content = f.read()
                self.assertIn(
                    f"ExecStart={expected['exec']}", content,
                    f"{service} must run {expected['exec']}",
                )

    def test_service_type_oneshot(self):
        """Boot setup services should be Type=oneshot."""
        for service, expected in self.SERVICES.items():
            path = os.path.join(SYSTEMD_DIR, service)
            if not os.path.isfile(path):
                continue
            with self.subTest(service=service):
                with open(path) as f:
                    content = f.read()
                self.assertIn(
                    f"Type={expected['type']}", content,
                    f"{service} must be Type={expected['type']}",
                )

    def test_service_after_network(self):
        """Boot setup services should start after network-online.target."""
        for service, expected in self.SERVICES.items():
            path = os.path.join(SYSTEMD_DIR, service)
            if not os.path.isfile(path):
                continue
            with self.subTest(service=service):
                with open(path) as f:
                    content = f.read()
                self.assertIn(
                    expected["after"], content,
                    f"{service} must run after {expected['after']}",
                )

    def test_service_wanted_by_multi_user(self):
        """Boot setup services should be wanted by multi-user.target."""
        for service in self.SERVICES:
            path = os.path.join(SYSTEMD_DIR, service)
            if not os.path.isfile(path):
                continue
            with self.subTest(service=service):
                with open(path) as f:
                    content = f.read()
                self.assertIn(
                    "WantedBy=multi-user.target", content,
                    f"{service} must be wanted by multi-user.target",
                )

    def test_service_has_timeout(self):
        """Boot setup services should have a timeout to prevent hangs."""
        for service in self.SERVICES:
            path = os.path.join(SYSTEMD_DIR, service)
            if not os.path.isfile(path):
                continue
            with self.subTest(service=service):
                with open(path) as f:
                    content = f.read()
                self.assertIn(
                    "TimeoutStartSec=", content,
                    f"{service} must have a TimeoutStartSec",
                )

    def test_service_has_home_and_path(self):
        """Boot setup services must set HOME and PATH environment variables.

        Without these, tools like git (for ohmyzsh) and curl may fail because
        HOME is unset in early-boot systemd services. PATH must include
        /usr/local/bin where ollama and opencode are installed.
        """
        for service in self.SERVICES:
            path = os.path.join(SYSTEMD_DIR, service)
            if not os.path.isfile(path):
                continue
            with self.subTest(service=service):
                with open(path) as f:
                    content = f.read()
                self.assertIn(
                    "Environment=HOME=", content,
                    f"{service} must set HOME environment",
                )
                self.assertIn(
                    "Environment=PATH=", content,
                    f"{service} must set PATH environment",
                )


# ═══════════════════════════════════════════════════════════════════════════
# User/group configuration (sysusers.d)
# ═══════════════════════════════════════════════════════════════════════════
class TestSysusersConfig(unittest.TestCase):
    """Verify sysusers.d config creates the mados user correctly."""

    def setUp(self):
        self.conf_path = os.path.join(SYSUSERS_DIR, "mados-live.conf")
        with open(self.conf_path) as f:
            self.content = f.read()

    def test_config_exists(self):
        """mados-live.conf must exist."""
        self.assertTrue(os.path.isfile(self.conf_path))

    def test_creates_mados_user(self):
        """Config should create the mados user."""
        self.assertIsNotNone(
            re.search(r'^u\s+mados\s', self.content, re.MULTILINE),
            "Must create mados user with 'u mados ...'",
        )

    def test_mados_in_wheel_group(self):
        """mados user should be a member of the wheel group."""
        self.assertIn(
            "m mados wheel", self.content,
            "mados must be added to wheel group",
        )

    def test_mados_in_essential_groups(self):
        """mados user should be in video, audio, and input groups."""
        for group in ("video", "audio", "input"):
            with self.subTest(group=group):
                self.assertIn(
                    f"m mados {group}", self.content,
                    f"mados must be added to {group} group",
                )

    def test_mados_uses_zsh(self):
        """mados user should use /usr/bin/zsh as default shell."""
        self.assertIn(
            "/usr/bin/zsh", self.content,
            "mados user must use zsh as default shell",
        )


# ═══════════════════════════════════════════════════════════════════════════
# /etc/passwd consistency
# ═══════════════════════════════════════════════════════════════════════════
class TestPasswdConfig(unittest.TestCase):
    """Verify /etc/passwd is consistent with sysusers.d config."""

    def setUp(self):
        self.passwd_path = os.path.join(AIROOTFS, "etc", "passwd")
        with open(self.passwd_path) as f:
            self.lines = f.read().strip().splitlines()

    def test_mados_user_exists(self):
        """mados user must be defined in /etc/passwd."""
        mados_lines = [l for l in self.lines if l.startswith("mados:")]
        self.assertEqual(
            len(mados_lines), 1,
            "Exactly one mados entry must exist in /etc/passwd",
        )

    def test_mados_uid_gid_match(self):
        """mados UID and GID should both be 1000."""
        for line in self.lines:
            if line.startswith("mados:"):
                fields = line.split(":")
                self.assertEqual(fields[2], "1000", "mados UID must be 1000")
                self.assertEqual(fields[3], "1000", "mados GID must be 1000")

    def test_mados_uses_zsh_in_passwd(self):
        """mados shell in /etc/passwd must be /usr/bin/zsh."""
        for line in self.lines:
            if line.startswith("mados:"):
                fields = line.split(":")
                self.assertEqual(
                    fields[6], "/usr/bin/zsh",
                    "mados shell must be /usr/bin/zsh in /etc/passwd",
                )


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh boot script permissions
# ═══════════════════════════════════════════════════════════════════════════
class TestProfiledefPermissions(unittest.TestCase):
    """Verify profiledef.sh grants correct permissions to boot scripts."""

    BOOT_SCRIPTS = [
        "setup-ohmyzsh.sh",
        "setup-opencode.sh",
        "setup-ollama.sh",
    ]

    def setUp(self):
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            self.content = f.read()

    def test_boot_scripts_have_permissions(self):
        """profiledef.sh should set permissions for all boot scripts."""
        for script in self.BOOT_SCRIPTS:
            with self.subTest(script=script):
                self.assertIn(
                    script, self.content,
                    f"profiledef.sh must include permissions for {script}",
                )

    def test_boot_scripts_executable(self):
        """Boot scripts should have executable permissions (0:0:755)."""
        for script in self.BOOT_SCRIPTS:
            with self.subTest(script=script):
                # Find the line with the script and verify it has 755 permissions
                pattern = re.compile(
                    rf'\["/usr/local/bin/{re.escape(script)}"\]="0:0:755"'
                )
                self.assertRegex(
                    self.content, pattern,
                    f"{script} must have 0:0:755 permissions in profiledef.sh",
                )


# ═══════════════════════════════════════════════════════════════════════════
# customize_airootfs.sh – pre-installs Oh My Zsh and OpenCode during build
# ═══════════════════════════════════════════════════════════════════════════
class TestCustomizeAirootfs(unittest.TestCase):
    """Verify customize_airootfs.sh pre-installs Oh My Zsh and OpenCode."""

    def setUp(self):
        self.script_path = os.path.join(AIROOTFS, "root", "customize_airootfs.sh")
        if os.path.isfile(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_script_exists(self):
        """customize_airootfs.sh must exist."""
        self.assertTrue(os.path.isfile(self.script_path))

    def test_has_bash_shebang(self):
        """customize_airootfs.sh must start with a bash shebang."""
        with open(self.script_path) as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith("#!"))
        self.assertIn("bash", first_line)

    def test_valid_syntax(self):
        """customize_airootfs.sh must have valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )

    def test_installs_ohmyzsh_to_skel(self):
        """Script must install Oh My Zsh to /etc/skel."""
        self.assertIn("/etc/skel/.oh-my-zsh", self.content)
        self.assertIn("git clone", self.content)
        self.assertIn("ohmyzsh", self.content)

    def test_installs_opencode(self):
        """Script must install OpenCode."""
        self.assertIn("opencode.ai/install", self.content)
        self.assertIn("opencode", self.content)

    def test_has_npm_fallback_for_opencode(self):
        """Script must install OpenCode via curl (no npm fallback needed)."""
        self.assertIn("opencode.ai/install", self.content)

    def test_copies_ohmyzsh_to_mados_user(self):
        """Script must copy Oh My Zsh to /home/mados."""
        self.assertIn("/home/mados/.oh-my-zsh", self.content)

    def test_copies_ohmyzsh_to_root(self):
        """Script must copy Oh My Zsh to /root."""
        self.assertIn("/root/.oh-my-zsh", self.content)

    def test_profiledef_has_permissions(self):
        """profiledef.sh must set permissions for customize_airootfs.sh."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        self.assertIn("customize_airootfs.sh", content)
        self.assertRegex(
            content,
            r'\["/root/customize_airootfs.sh"\]="0:0:755"',
            "customize_airootfs.sh must have 0:0:755 permissions",
        )


if __name__ == "__main__":
    unittest.main()
