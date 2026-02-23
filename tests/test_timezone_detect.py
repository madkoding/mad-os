#!/usr/bin/env python3
"""
Tests for madOS timezone auto-detection script and service.

Validates that the timezone detection script exists, has valid syntax,
and the systemd service is properly configured.
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
# Timezone detect script validation
# ═══════════════════════════════════════════════════════════════════════════
class TestTimezoneDetectScript(unittest.TestCase):
    """Validate mados-timezone-detect.sh script."""

    SCRIPT = os.path.join(BIN_DIR, "mados-timezone-detect.sh")

    def test_script_exists(self):
        """Timezone detection script must exist."""
        self.assertTrue(
            os.path.isfile(self.SCRIPT),
            "mados-timezone-detect.sh not found in usr/local/bin/",
        )

    def test_valid_bash_syntax(self):
        """Script must have valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", self.SCRIPT],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Bash syntax error: {result.stderr}",
        )

    def test_has_shebang(self):
        """Script must start with a bash shebang."""
        with open(self.SCRIPT) as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith("#!"), "Must start with #!")
        self.assertIn("bash", first_line, "Must use bash shebang")

    def test_uses_strict_mode(self):
        """Script must use set -euo pipefail."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn(
            "set -euo pipefail", content,
            "Must use strict mode (set -euo pipefail)",
        )

    def test_detects_linux_timezone(self):
        """Script must have Linux timezone detection strategy."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn("detect_from_linux", content)
        self.assertIn("/etc/localtime", content)
        self.assertIn("zoneinfo", content)

    def test_detects_windows_timezone(self):
        """Script must have Windows timezone detection strategy."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn("detect_from_windows", content)
        self.assertIn("ntfs", content)

    def test_detects_geolocation_timezone(self):
        """Script must have IP geolocation detection strategy."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn("detect_from_geolocation", content)
        self.assertIn("curl", content)

    def test_supports_kernel_boot_parameter(self):
        """Script must support timezone= kernel boot parameter."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn("/proc/cmdline", content)
        self.assertIn("timezone=", content)

    def test_handles_local_rtc(self):
        """Script must handle local RTC for Windows dual-boot."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn("DETECTED_LOCAL_RTC", content)
        self.assertIn("set-local-rtc", content)

    def test_maps_common_windows_timezones(self):
        """Script must map common Windows timezone names to IANA."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn("America/Santiago", content)
        self.assertIn("America/New_York", content)
        self.assertIn("America/Mexico_City", content)
        self.assertIn("Europe/London", content)
        self.assertIn("Asia/Tokyo", content)

    def test_uses_timedatectl(self):
        """Script must use timedatectl to apply timezone."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn("timedatectl set-timezone", content)

    def test_fallback_to_utc(self):
        """Script must fall back to UTC if no timezone detected."""
        with open(self.SCRIPT) as f:
            content = f.read()
        self.assertIn("keeping UTC", content)


# ═══════════════════════════════════════════════════════════════════════════
# Systemd service validation
# ═══════════════════════════════════════════════════════════════════════════
class TestTimezoneService(unittest.TestCase):
    """Validate mados-timezone.service systemd unit."""

    SERVICE = os.path.join(SYSTEMD_DIR, "mados-timezone.service")
    WANTS_LINK = os.path.join(
        SYSTEMD_DIR, "multi-user.target.wants", "mados-timezone.service"
    )

    def test_service_file_exists(self):
        """Systemd service file must exist."""
        self.assertTrue(
            os.path.isfile(self.SERVICE),
            "mados-timezone.service not found",
        )

    def test_service_enabled_via_wants(self):
        """Service must be enabled via multi-user.target.wants symlink."""
        self.assertTrue(
            os.path.islink(self.WANTS_LINK) or os.path.isfile(self.WANTS_LINK),
            "mados-timezone.service not linked in multi-user.target.wants/",
        )

    def test_service_references_correct_script(self):
        """Service ExecStart must point to the detection script."""
        with open(self.SERVICE) as f:
            content = f.read()
        self.assertIn(
            "ExecStart=/usr/local/bin/mados-timezone-detect.sh", content,
        )

    def test_service_is_oneshot(self):
        """Service must be oneshot type."""
        with open(self.SERVICE) as f:
            content = f.read()
        self.assertIn("Type=oneshot", content)

    def test_service_runs_before_timesyncd(self):
        """Service must run before timesyncd to set timezone first."""
        with open(self.SERVICE) as f:
            content = f.read()
        self.assertIn("Before=systemd-timesyncd.service", content)

    def test_service_has_timeout(self):
        """Service must have a timeout to prevent hanging at boot."""
        with open(self.SERVICE) as f:
            content = f.read()
        self.assertIn("TimeoutSec=", content)


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestTimezoneProfiledef(unittest.TestCase):
    """Validate that profiledef.sh includes timezone script permissions."""

    def test_script_in_profiledef(self):
        """Timezone detect script must have permissions in profiledef.sh."""
        with open(PROFILEDEF) as f:
            content = f.read()
        self.assertIn(
            "mados-timezone-detect.sh", content,
            "mados-timezone-detect.sh must be listed in profiledef.sh",
        )

    def test_script_is_executable_in_profiledef(self):
        """Script must be set as executable (755) in profiledef.sh."""
        with open(PROFILEDEF) as f:
            content = f.read()
        match = re.search(
            r'mados-timezone-detect\.sh.*"0:0:755"', content
        )
        self.assertIsNotNone(
            match,
            "mados-timezone-detect.sh must have 0:0:755 permissions",
        )


if __name__ == "__main__":
    unittest.main()
