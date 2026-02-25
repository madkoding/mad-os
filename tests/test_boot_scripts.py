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

    BOOT_SCRIPTS = [
        "setup-ohmyzsh.sh",
        "setup-opencode.sh",
        "setup-ollama.sh",
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
        """Boot scripts should use set -euo pipefail for safety.

        Exception: setup scripts that run as systemd services intentionally
        avoid strict mode because they must never crash the service – they
        use their own graceful error handling and always exit 0.
        """
        STRICT_MODE_EXCEPTIONS = {"setup-opencode.sh", "setup-ollama.sh", "setup-ohmyzsh.sh"}
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

    def test_no_strict_mode(self):
        """setup-ohmyzsh.sh must NOT use set -euo pipefail (must never crash service)."""
        self.assertNotIn("set -euo pipefail", self.content)

    def test_always_exits_zero_on_failure(self):
        """setup-ohmyzsh.sh must exit 0 on failure to not crash the systemd service."""
        # Check that the git clone failure handler exits 0
        self.assertIn("exit 0", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# setup-opencode.sh
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupClaudeCode(unittest.TestCase):
    """Verify setup-opencode.sh is properly configured."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-opencode.sh")
        if os.path.isfile(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()

    def test_script_exists(self):
        """setup-opencode.sh must exist."""
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

    def test_uses_curl_install_method(self):
        """Script should use curl install (opencode.ai/install) as primary method."""
        self.assertIn("opencode.ai/install", self.content)

    def test_npm_uses_unsafe_perm(self):
        """npm install must use --unsafe-perm to allow postinstall scripts as root."""
        self.assertIn("--unsafe-perm", self.content)

    def test_no_strict_mode(self):
        """setup-opencode.sh must NOT use set -euo pipefail (must never crash service)."""
        self.assertNotIn("set -euo pipefail", self.content)

    def test_always_exits_zero(self):
        """setup-opencode.sh must always exit 0 to not crash the systemd service."""
        # All exit statements in the script should be exit 0
        import re
        exits = re.findall(r'exit\s+(\d+)', self.content)
        for code in exits:
            self.assertEqual(code, "0",
                             "All exit codes in setup-opencode.sh must be 0")


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
        """Script must have npm fallback for OpenCode installation."""
        self.assertIn("npm", self.content)
        self.assertIn("opencode-ai", self.content)

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
