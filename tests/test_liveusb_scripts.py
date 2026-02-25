#!/usr/bin/env python3
"""
Tests for madOS live USB script execution readiness.

Validates that all scripts intended to run in the live USB environment
are properly configured to execute:
  - Systemd services reference scripts that actually exist
  - All scripts have executable permissions defined in profiledef.sh
  - All shell scripts have valid bash syntax and shebangs
  - Enabled systemd services point to valid service files
  - No broken references between services, scripts, and permissions

These tests ensure that the live USB boots correctly and all automated
scripts will execute as expected.
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
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")
PROFILEDEF = os.path.join(REPO_DIR, "profiledef.sh")


# ═══════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════
def _get_custom_service_files():
    """Return list of (name, path) for non-symlink .service files."""
    services = []
    if not os.path.isdir(SYSTEMD_DIR):
        return services
    for fname in sorted(os.listdir(SYSTEMD_DIR)):
        fpath = os.path.join(SYSTEMD_DIR, fname)
        if (
            fname.endswith(".service")
            and os.path.isfile(fpath)
            and not os.path.islink(fpath)
        ):
            services.append((fname, fpath))
    return services


def _get_enabled_service_symlinks():
    """Return list of (symlink_name, target, wants_dir) for enabled services."""
    symlinks = []
    if not os.path.isdir(SYSTEMD_DIR):
        return symlinks
    for entry in sorted(os.listdir(SYSTEMD_DIR)):
        wants_dir = os.path.join(SYSTEMD_DIR, entry)
        if not os.path.isdir(wants_dir) or not entry.endswith(".wants"):
            continue
        for svc in sorted(os.listdir(wants_dir)):
            svc_path = os.path.join(wants_dir, svc)
            if os.path.islink(svc_path) and svc.endswith(".service"):
                target = os.readlink(svc_path)
                symlinks.append((svc, target, entry))
    return symlinks


def _parse_exec_paths(service_path):
    """Extract all ExecStart/ExecStartPre/ExecStartPost script paths from a service file."""
    paths = []
    with open(service_path) as f:
        for line in f:
            line = line.strip()
            for directive in ("ExecStart=", "ExecStartPre=", "ExecStartPost="):
                if line.startswith(directive):
                    cmd = line[len(directive) :]
                    # Remove optional prefix flags like - (ignore errors)
                    cmd = cmd.lstrip("-")
                    # First token is the executable path
                    tokens = cmd.split()
                    exe = tokens[0] if tokens else ""
                    if exe.startswith("/usr/local/"):
                        paths.append(exe)
    return paths


def _get_bin_scripts():
    """Return list of (name, path) for all files in /usr/local/bin/."""
    scripts = []
    if not os.path.isdir(BIN_DIR):
        return scripts
    for fname in sorted(os.listdir(BIN_DIR)):
        fpath = os.path.join(BIN_DIR, fname)
        if os.path.isfile(fpath):
            scripts.append((fname, fpath))
    return scripts


def _is_shell_script(fpath):
    """Check if file is a shell script (by shebang)."""
    try:
        with open(fpath, "rb") as f:
            first_bytes = f.read(256)
        if not first_bytes.startswith(b"#!"):
            return False
        first_line = first_bytes.split(b"\n")[0].decode("utf-8", errors="replace")
        return "bash" in first_line or "/sh" in first_line
    except (IOError, UnicodeDecodeError):
        return False


def _read_profiledef():
    """Read profiledef.sh content."""
    with open(PROFILEDEF) as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════════════════
# Test: Systemd services reference scripts that exist
# ═══════════════════════════════════════════════════════════════════════════
class TestSystemdServicesReferenceExistingScripts(unittest.TestCase):
    """Every ExecStart in a custom systemd service must point to a script
    that exists in the airootfs tree."""

    def test_all_exec_scripts_exist(self):
        """All ExecStart/Pre/Post scripts in custom services must exist in airootfs."""
        for svc_name, svc_path in _get_custom_service_files():
            exec_paths = _parse_exec_paths(svc_path)
            for exe in exec_paths:
                with self.subTest(service=svc_name, exec_path=exe):
                    # Map absolute path to airootfs location
                    airootfs_path = os.path.join(AIROOTFS, exe.lstrip("/"))
                    self.assertTrue(
                        os.path.isfile(airootfs_path),
                        f"{svc_name}: ExecStart script {exe} not found at "
                        f"{airootfs_path}",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Test: All scripts in /usr/local/bin/ have permissions in profiledef.sh
# ═══════════════════════════════════════════════════════════════════════════
class TestAllScriptsHavePermissions(unittest.TestCase):
    """Every script in /usr/local/bin/ must have permissions set in profiledef.sh."""

    def setUp(self):
        self.profiledef = _read_profiledef()

    def test_all_bin_scripts_in_profiledef(self):
        """All scripts in /usr/local/bin/ must appear in profiledef.sh."""
        for name, _ in _get_bin_scripts():
            with self.subTest(script=name):
                expected = f"/usr/local/bin/{name}"
                self.assertIn(
                    expected,
                    self.profiledef,
                    f"{name} is in /usr/local/bin/ but has no permissions "
                    f"entry in profiledef.sh",
                )

    def test_all_bin_scripts_are_executable(self):
        """All scripts in /usr/local/bin/ must have 755 permissions."""
        for name, _ in _get_bin_scripts():
            with self.subTest(script=name):
                pattern = re.compile(
                    rf'\["/usr/local/bin/{re.escape(name)}"\]="0:0:755"'
                )
                self.assertRegex(
                    self.profiledef,
                    pattern,
                    f"{name} must have 0:0:755 permissions in profiledef.sh",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Test: All shell scripts have valid syntax and shebangs
# ═══════════════════════════════════════════════════════════════════════════
class TestAllShellScriptsValid(unittest.TestCase):
    """Every shell script in /usr/local/bin/ must have valid bash syntax."""

    def test_all_shell_scripts_compile(self):
        """bash -n must succeed for all shell scripts."""
        for name, fpath in _get_bin_scripts():
            if not _is_shell_script(fpath):
                continue
            with self.subTest(script=name):
                result = subprocess.run(
                    ["bash", "-n", fpath],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Bash syntax error in {name}:\n{result.stderr}",
                )

    def test_all_shell_scripts_have_shebang(self):
        """All shell scripts must start with #!/bin/bash or similar."""
        for name, fpath in _get_bin_scripts():
            if not _is_shell_script(fpath):
                continue
            with self.subTest(script=name):
                with open(fpath) as f:
                    first_line = f.readline().strip()
                self.assertTrue(
                    first_line.startswith("#!"),
                    f"{name} must start with #!",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Test: Enabled services point to valid service files
# ═══════════════════════════════════════════════════════════════════════════
class TestEnabledServicesValid(unittest.TestCase):
    """Enabled services (symlinks in .wants dirs) must point to valid files."""

    def test_enabled_service_targets_exist(self):
        """Every enabled service symlink must resolve to an existing file."""
        for svc_name, target, wants_dir in _get_enabled_service_symlinks():
            with self.subTest(service=svc_name, wants=wants_dir):
                # Skip system-provided services (not managed by this repo)
                if target.startswith(("/usr/lib/systemd/", "/lib/systemd/")):
                    continue
                # Resolve relative paths
                if not target.startswith("/"):
                    wants_path = os.path.join(SYSTEMD_DIR, wants_dir)
                    resolved = os.path.normpath(os.path.join(wants_path, target))
                else:
                    resolved = os.path.join(AIROOTFS, target.lstrip("/"))
                self.assertTrue(
                    os.path.isfile(resolved),
                    f"Enabled service {svc_name} in {wants_dir} points to "
                    f"{target} which does not exist at {resolved}",
                )

    # Services intentionally not pre-enabled (enabled at runtime or conditionally)
    OPTIONAL_SERVICES = {
        "mados-persist-sync.service",  # enabled at runtime if persistence detected
        "mados-persistence-detect.service",  # enabled at runtime if persistence detected
    }

    def test_custom_services_are_enabled(self):
        """Custom services with [Install] WantedBy should have enable symlinks."""
        enabled_names = {s[0] for s in _get_enabled_service_symlinks()}
        for svc_name, svc_path in _get_custom_service_files():
            if svc_name in self.OPTIONAL_SERVICES:
                continue
            with open(svc_path) as f:
                content = f.read()
            # Check if service has a WantedBy directive
            match = re.search(r"WantedBy=(\S+)", content)
            if not match:
                continue
            wanted_by = match.group(1)
            with self.subTest(service=svc_name, wanted_by=wanted_by):
                self.assertIn(
                    svc_name,
                    enabled_names,
                    f"{svc_name} declares WantedBy={wanted_by} but has no "
                    f"enable symlink in any .wants directory",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Test: Critical live USB scripts exist
# ═══════════════════════════════════════════════════════════════════════════
class TestCriticalLiveUSBScriptsExist(unittest.TestCase):
    """Critical scripts that must be present for live USB to function."""

    CRITICAL_SCRIPTS = [
        "install-mados",
        "install-mados-gtk.py",
        "livecd-sound",
        "choose-mirror",
        "select-compositor",
        "sway-session",
        "hyprland-session",
        "cage-greeter",
        "setup-opencode.sh",
        "setup-ohmyzsh.sh",
        "setup-ollama.sh",
        "mados-audio-init.sh",
        "mados-debug",
        "detect-legacy-hardware",
    ]

    def test_critical_scripts_exist(self):
        """All critical live USB scripts must exist."""
        for script in self.CRITICAL_SCRIPTS:
            with self.subTest(script=script):
                path = os.path.join(BIN_DIR, script)
                self.assertTrue(
                    os.path.isfile(path),
                    f"Critical script {script} is missing from airootfs/usr/local/bin/",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Test: Systemd service ExecStart scripts have matching profiledef perms
# ═══════════════════════════════════════════════════════════════════════════
class TestServiceScriptsHavePermissions(unittest.TestCase):
    """Scripts launched by systemd services must be executable via profiledef."""

    def setUp(self):
        self.profiledef = _read_profiledef()

    def test_service_exec_scripts_in_profiledef(self):
        """Every ExecStart script must have 755 permissions in profiledef.sh."""
        for svc_name, svc_path in _get_custom_service_files():
            exec_paths = _parse_exec_paths(svc_path)
            for exe in exec_paths:
                if not exe.startswith("/usr/local/"):
                    continue
                with self.subTest(service=svc_name, exec_path=exe):
                    # Escape special chars for regex
                    escaped = re.escape(exe)
                    pattern = re.compile(rf'\["{escaped}"\]="0:0:755"')
                    self.assertRegex(
                        self.profiledef,
                        pattern,
                        f"{svc_name}: ExecStart script {exe} must have "
                        f"0:0:755 permissions in profiledef.sh",
                    )


if __name__ == "__main__":
    unittest.main()


# ═══════════════════════════════════════════════════════════════════════════
# livecd-sound pick_a_card array handling
# ═══════════════════════════════════════════════════════════════════════════
class TestLivecdSoundPickACard(unittest.TestCase):
    """Verify livecd-sound pick_a_card uses proper bash array iteration."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "livecd-sound")
        if not os.path.isfile(self.script_path):
            self.skipTest("livecd-sound script not found")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_usable_cards_is_array(self):
        """usable_cards must be declared as a proper bash array.

        Regression test: previously usable_cards was a plain string but
        iterated with ${usable_cards[@]}, which treats the entire string
        as one element instead of iterating per card index.
        """
        # Must use mapfile/readarray or declare -a to create a real array
        self.assertRegex(
            self.content,
            r'(mapfile|readarray|local -a) .* usable_cards',
            "usable_cards must be a proper bash array (mapfile or declare -a)",
        )

    def test_array_count_uses_hash(self):
        """Card count must use ${#usable_cards[@]} (array length), not wc."""
        self.assertIn(
            "${#usable_cards[@]}",
            self.content,
            "Must use ${#usable_cards[@]} for array length",
        )

    def test_valid_bash_syntax(self):
        """livecd-sound must have valid bash syntax after fix."""
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )
