#!/usr/bin/env python3
"""
Tests for madOS OTA Update System.

Validates that update scripts exist and have correct structure.
"""

import os
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")


class TestOTAUpdateScript(unittest.TestCase):
    """Test mados-update script."""

    def test_script_exists(self):
        """mados-update script must exist."""
        script_path = os.path.join(BIN_DIR, "mados-update")
        self.assertTrue(os.path.isfile(script_path))

    def test_script_is_executable(self):
        """mados-update must be executable."""
        script_path = os.path.join(BIN_DIR, "mados-update")
        self.assertTrue(os.access(script_path, os.X_OK))

    def test_script_has_shebang(self):
        """mados-update must start with bash shebang."""
        script_path = os.path.join(BIN_DIR, "mados-update")
        with open(script_path) as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith("#!"))
        self.assertTrue("bash" in first_line)

    def test_script_uses_strict_mode(self):
        """mados-update must use set -e."""
        script_path = os.path.join(BIN_DIR, "mados-update")
        with open(script_path) as f:
            content = f.read()
        self.assertIn("set -e", content)

    def test_script_has_check_command(self):
        """mados-update must have check command."""
        script_path = os.path.join(BIN_DIR, "mados-update")
        with open(script_path) as f:
            content = f.read()
        self.assertIn("cmd_check", content)
        self.assertIn("check_for_updates", content)

    def test_script_has_download_command(self):
        """mados-update must have download command."""
        script_path = os.path.join(BIN_DIR, "mados-update")
        with open(script_path) as f:
            content = f.read()
        self.assertIn("cmd_download", content)
        self.assertIn("download_update", content)

    def test_script_has_github_api(self):
        """mados-update must reference GitHub API."""
        script_path = os.path.join(BIN_DIR, "mados-update")
        with open(script_path) as f:
            content = f.read()
        self.assertIn("api.github.com", content)
        self.assertIn("releases", content)


class TestOTANotifier(unittest.TestCase):
    """Test mados-update-notifier script."""

    def test_notifier_exists(self):
        """mados-update-notifier must exist."""
        script_path = os.path.join(BIN_DIR, "mados-update-notifier")
        self.assertTrue(os.path.isfile(script_path))

    def test_notifier_is_executable(self):
        """mados-update-notifier must be executable."""
        script_path = os.path.join(BIN_DIR, "mados-update-notifier")
        self.assertTrue(os.access(script_path, os.X_OK))

    def test_notifier_is_python(self):
        """mados-update-notifier must be Python script."""
        script_path = os.path.join(BIN_DIR, "mados-update-notifier")
        with open(script_path) as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith("#!/usr/bin/env python3"))

    def test_notifier_outputs_json(self):
        """mados-update-notifier must output JSON."""
        script_path = os.path.join(BIN_DIR, "mados-update-notifier")
        with open(script_path) as f:
            content = f.read()
        self.assertIn("json.dumps", content)
        self.assertIn('"text"', content)
        self.assertIn('"tooltip"', content)


class TestSystemdService(unittest.TestCase):
    """Test systemd service for OTA updates."""

    def test_service_exists(self):
        """mados-update-check.service must exist."""
        service_path = os.path.join(SYSTEMD_DIR, "mados-update-check.service")
        self.assertTrue(os.path.isfile(service_path))

    def test_service_has_unit_section(self):
        """Service must have [Unit] section."""
        service_path = os.path.join(SYSTEMD_DIR, "mados-update-check.service")
        with open(service_path) as f:
            content = f.read()
        self.assertIn("[Unit]", content)

    def test_service_has_service_section(self):
        """Service must have [Service] section."""
        service_path = os.path.join(SYSTEMD_DIR, "mados-update-check.service")
        with open(service_path) as f:
            content = f.read()
        self.assertIn("[Service]", content)

    def test_service_runs_mados_update(self):
        """Service must run mados-update."""
        service_path = os.path.join(SYSTEMD_DIR, "mados-update-check.service")
        with open(service_path) as f:
            content = f.read()
        self.assertIn("/usr/local/bin/mados-update", content)


if __name__ == "__main__":
    unittest.main()
