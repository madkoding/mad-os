#!/usr/bin/env python3
"""
Tests for madOS boot-time scripts and services.

Validates that boot scripts (setup-ohmyzsh.sh, setup-claude-code.sh) and their
corresponding systemd service units are properly configured for the live USB
environment.

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

    BOOT_SCRIPTS = [
        "setup-ohmyzsh.sh",
        "setup-claude-code.sh",
        "setup-persistence.sh",
    ]

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
        """Every boot script should use set -euo pipefail for safety."""
        for script in self.BOOT_SCRIPTS:
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
# setup-ohmyzsh.sh – the script that had the chown bug
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupOhmyzsh(unittest.TestCase):
    """Verify setup-ohmyzsh.sh handles user/group ownership correctly."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-ohmyzsh.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_script_exists(self):
        """setup-ohmyzsh.sh must exist."""
        self.assertTrue(os.path.isfile(self.script_path))

    def test_chown_uses_gid_not_username_as_group(self):
        """chown must use the numeric GID variable, not $username as group.

        This is the regression test for the bug:
          chown: invalid group: 'mados:mados'

        The fix reads the GID field from /etc/passwd and uses it:
          chown -R "$username:$gid"
        instead of the broken:
          chown -R "$username:$username"
        """
        # The script must NOT use $username:$username in chown
        self.assertNotRegex(
            self.content,
            r'chown.*\$username:\$username',
            "chown must NOT use $username as the group name "
            "(causes 'invalid group' error when no matching group exists)",
        )

        # The script SHOULD use $gid in the chown command
        self.assertRegex(
            self.content,
            r'chown.*\$gid',
            "chown should use the $gid variable from /etc/passwd",
        )

    def test_passwd_read_captures_gid_field(self):
        """The while-read loop must capture the GID field from /etc/passwd.

        /etc/passwd format: username:x:uid:gid:gecos:home:shell
        The read command must assign field 4 to a variable (not skip it).
        """
        # Look for the IFS=: read line that parses /etc/passwd
        read_match = re.search(
            r'IFS=:\s+read\s+-r\s+(.*?)\s*;', self.content
        )
        self.assertIsNotNone(
            read_match,
            "Script must contain an IFS=: read -r ... line to parse /etc/passwd",
        )

        fields = read_match.group(1).split()
        # /etc/passwd fields: username:password:uid:gid:gecos:home:shell
        # Position 3 (0-indexed) should be the GID field
        self.assertGreaterEqual(
            len(fields), 4,
            "read command must capture at least 4 fields from /etc/passwd",
        )

        gid_field = fields[3]
        self.assertNotEqual(
            gid_field, "_",
            "GID field (position 4 in /etc/passwd) must NOT be discarded with _",
        )

    def test_checks_internet_before_clone(self):
        """Script should check connectivity before attempting git clone."""
        curl_pos = self.content.find("curl")
        clone_pos = self.content.find("git clone")
        self.assertNotEqual(curl_pos, -1, "Script must check connectivity")
        self.assertNotEqual(clone_pos, -1, "Script must clone Oh My Zsh")
        self.assertLess(
            curl_pos, clone_pos,
            "Connectivity check must come before git clone",
        )

    def test_copies_to_etc_skel(self):
        """Script should install Oh My Zsh to /etc/skel first."""
        self.assertIn(
            "/etc/skel/.oh-my-zsh", self.content,
            "Script must install to /etc/skel/.oh-my-zsh",
        )

    def test_handles_root_user(self):
        """Script should handle the root user separately."""
        self.assertIn(
            "/root/.oh-my-zsh", self.content,
            "Script must handle root user's Oh My Zsh installation",
        )


# ═══════════════════════════════════════════════════════════════════════════
# setup-claude-code.sh
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupClaudeCode(unittest.TestCase):
    """Verify setup-claude-code.sh is properly configured."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-claude-code.sh")
        if os.path.isfile(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()

    def test_script_exists(self):
        """setup-claude-code.sh must exist."""
        self.assertTrue(os.path.isfile(self.script_path))

    def test_checks_npm_availability(self):
        """Script should verify npm is available before installing."""
        self.assertIn("npm", self.content)

    def test_checks_connectivity(self):
        """Script should check internet before attempting install."""
        self.assertIn("curl", self.content)

    def test_graceful_exit_on_no_network(self):
        """Script should exit 0 (not fail) when network is unavailable."""
        # After the connectivity check, script should exit 0
        self.assertIn("exit 0", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# Systemd service files
# ═══════════════════════════════════════════════════════════════════════════
class TestSystemdServices(unittest.TestCase):
    """Verify systemd service files for boot scripts are correct."""

    SERVICES = {
        "setup-ohmyzsh.service": {
            "exec": "/usr/local/bin/setup-ohmyzsh.sh",
            "after": "network-online.target",
            "type": "oneshot",
        },
        "setup-claude-code.service": {
            "exec": "/usr/local/bin/setup-claude-code.sh",
            "after": "network-online.target",
            "type": "oneshot",
        },
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
        "setup-claude-code.sh",
        "setup-persistence.sh",
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


if __name__ == "__main__":
    unittest.main()
