#!/usr/bin/env python3
"""
Tests for madOS persistence scripts (Ventoy-style).

Validates that persistence scripts are properly configured:
  - All persistence scripts exist and are executable
  - Systemd services reference valid scripts
  - Shell scripts have valid bash syntax
  - Configuration files are valid
"""

import os
import subprocess
import unittest

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")


class TestPersistenceScriptsExist(unittest.TestCase):
    """Test that all persistence scripts exist."""

    def test_mados_persistence_cli_exists(self):
        path = os.path.join(BIN_DIR, "mados-persistence")
        self.assertTrue(os.path.exists(path), "mados-persistence CLI not found")

    def test_mados_persist_sync_exists(self):
        path = os.path.join(BIN_DIR, "mados-persist-sync.sh")
        self.assertTrue(os.path.exists(path), "mados-persist-sync.sh not found")

    def test_mados_persist_detect_exists(self):
        path = os.path.join(BIN_DIR, "mados-persist-detect.sh")
        self.assertTrue(os.path.exists(path), "mados-persist-detect.sh not found")


class TestPersistenceScriptsExecutable(unittest.TestCase):
    """Test that persistence scripts are executable."""

    def test_mados_persistence_is_executable(self):
        path = os.path.join(BIN_DIR, "mados-persistence")
        self.assertTrue(os.access(path, os.X_OK), "mados-persistence not executable")

    def test_mados_persist_sync_is_executable(self):
        path = os.path.join(BIN_DIR, "mados-persist-sync.sh")
        self.assertTrue(
            os.access(path, os.X_OK), "mados-persist-sync.sh not executable"
        )

    def test_mados_persist_detect_is_executable(self):
        path = os.path.join(BIN_DIR, "mados-persist-detect.sh")
        self.assertTrue(
            os.access(path, os.X_OK), "mados-persist-detect.sh not executable"
        )


class TestPersistenceScriptsSyntax(unittest.TestCase):
    """Test that shell scripts have valid bash syntax."""

    def test_mados_persist_sync_syntax(self):
        path = os.path.join(BIN_DIR, "mados-persist-sync.sh")
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")

    def test_mados_persist_detect_syntax(self):
        path = os.path.join(BIN_DIR, "mados-persist-detect.sh")
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")


class TestPersistenceServicesExist(unittest.TestCase):
    """Test that persistence systemd services exist."""

    def test_mados_persist_sync_service_exists(self):
        path = os.path.join(SYSTEMD_DIR, "mados-persist-sync.service")
        self.assertTrue(os.path.exists(path), "mados-persist-sync.service not found")

    def test_mados_persistence_detect_service_exists(self):
        path = os.path.join(SYSTEMD_DIR, "mados-persistence-detect.service")
        self.assertTrue(
            os.path.exists(path), "mados-persistence-detect.service not found"
        )


class TestPersistenceServiceReferences(unittest.TestCase):
    """Test that services reference valid scripts."""

    def test_mados_persist_sync_service_references_script(self):
        service_path = os.path.join(SYSTEMD_DIR, "mados-persist-sync.service")
        if not os.path.exists(service_path):
            self.skipTest("Service file not found")

        with open(service_path, "r") as f:
            content = f.read()

        script_path = os.path.join(BIN_DIR, "mados-persist-sync.sh")
        self.assertIn(
            "mados-persist-sync.sh",
            content,
            "Service does not reference mados-persist-sync.sh",
        )

    def test_mados_persistence_detect_service_references_script(self):
        service_path = os.path.join(SYSTEMD_DIR, "mados-persistence-detect.service")
        if not os.path.exists(service_path):
            self.skipTest("Service file not found")

        with open(service_path, "r") as f:
            content = f.read()

        script_path = os.path.join(BIN_DIR, "mados-persist-detect.sh")
        self.assertIn(
            "mados-persist-detect.sh",
            content,
            "Service does not reference mados-persist-detect.sh",
        )


class TestPersistenceCLICommands(unittest.TestCase):
    """Test that mados-persistence CLI has expected commands."""

    def test_mados_persistence_has_status_command(self):
        path = os.path.join(BIN_DIR, "mados-persistence")
        if not os.path.exists(path):
            self.skipTest("CLI not found")

        with open(path, "r") as f:
            content = f.read()

        self.assertIn("status", content, "CLI missing 'status' command")

    def test_mados_persistence_has_info_command(self):
        path = os.path.join(BIN_DIR, "mados-persistence")
        if not os.path.exists(path):
            self.skipTest("CLI not found")

        with open(path, "r") as f:
            content = f.read()

        self.assertIn("info", content, "CLI missing 'info' command")

    def test_mados_persistence_has_ventoy_docs(self):
        path = os.path.join(BIN_DIR, "mados-persistence")
        if not os.path.exists(path):
            self.skipTest("CLI not found")

        with open(path, "r") as f:
            content = f.read()

        self.assertIn("Ventoy", content, "CLI missing Ventoy documentation")


if __name__ == "__main__":
    unittest.main()
