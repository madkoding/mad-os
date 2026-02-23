#!/usr/bin/env python3
"""
Tests for madOS persistence scripts.

Validates that persistence scripts are properly configured:
  - All persistence scripts exist and are executable
  - Systemd services reference valid scripts and have correct Type
  - Shell scripts have valid bash syntax
  - Services are properly chained (ventoy-setup → detect → sync)
  - GRUB/syslinux entries use cow_label for real persistence
  - State file path is consistent across scripts
"""

import os
import subprocess
import unittest

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")
SYSTEMD_DIR = os.path.join(AIROOTFS, "etc", "systemd", "system")
GRUB_DIR = os.path.join(REPO_DIR, "grub")
SYSLINUX_DIR = os.path.join(REPO_DIR, "syslinux")


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

    def test_mados_ventoy_setup_exists(self):
        path = os.path.join(BIN_DIR, "mados-ventoy-setup.sh")
        self.assertTrue(os.path.exists(path), "mados-ventoy-setup.sh not found")


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

    def test_mados_ventoy_setup_is_executable(self):
        path = os.path.join(BIN_DIR, "mados-ventoy-setup.sh")
        self.assertTrue(
            os.access(path, os.X_OK), "mados-ventoy-setup.sh not executable"
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

    def test_mados_ventoy_setup_syntax(self):
        path = os.path.join(BIN_DIR, "mados-ventoy-setup.sh")
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")

    def test_mados_persistence_cli_syntax(self):
        path = os.path.join(BIN_DIR, "mados-persistence")
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

    def test_mados_ventoy_setup_service_exists(self):
        path = os.path.join(SYSTEMD_DIR, "mados-ventoy-setup.service")
        self.assertTrue(
            os.path.exists(path), "mados-ventoy-setup.service not found"
        )


class TestPersistenceServiceReferences(unittest.TestCase):
    """Test that services reference valid scripts."""

    def test_mados_persist_sync_service_references_script(self):
        service_path = os.path.join(SYSTEMD_DIR, "mados-persist-sync.service")
        if not os.path.exists(service_path):
            self.skipTest("Service file not found")

        with open(service_path, "r") as f:
            content = f.read()

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

        self.assertIn(
            "mados-persist-detect.sh",
            content,
            "Service does not reference mados-persist-detect.sh",
        )

    def test_mados_ventoy_setup_service_references_script(self):
        service_path = os.path.join(SYSTEMD_DIR, "mados-ventoy-setup.service")
        if not os.path.exists(service_path):
            self.skipTest("Service file not found")

        with open(service_path, "r") as f:
            content = f.read()

        self.assertIn(
            "mados-ventoy-setup.sh",
            content,
            "Service does not reference mados-ventoy-setup.sh",
        )


class TestPersistenceServiceTypes(unittest.TestCase):
    """Test that services use correct Type= values."""

    def _read_service(self, name):
        path = os.path.join(SYSTEMD_DIR, name)
        if not os.path.exists(path):
            self.skipTest(f"{name} not found")
        with open(path, "r") as f:
            return f.read()

    def test_sync_service_is_simple(self):
        """persist-sync runs a blocking loop, must be Type=simple, not forking."""
        content = self._read_service("mados-persist-sync.service")
        self.assertIn("Type=simple", content)
        self.assertNotIn("Type=forking", content)

    def test_detect_service_is_oneshot(self):
        content = self._read_service("mados-persistence-detect.service")
        self.assertIn("Type=oneshot", content)

    def test_ventoy_setup_service_is_oneshot(self):
        content = self._read_service("mados-ventoy-setup.service")
        self.assertIn("Type=oneshot", content)


class TestPersistenceServiceChain(unittest.TestCase):
    """Test that services are properly chained in execution order."""

    def _read_service(self, name):
        path = os.path.join(SYSTEMD_DIR, name)
        if not os.path.exists(path):
            self.skipTest(f"{name} not found")
        with open(path, "r") as f:
            return f.read()

    def test_detect_runs_after_ventoy_setup(self):
        content = self._read_service("mados-persistence-detect.service")
        self.assertIn("After=mados-ventoy-setup.service", content)

    def test_sync_runs_after_detect(self):
        content = self._read_service("mados-persist-sync.service")
        self.assertIn("After=mados-persistence-detect.service", content)

    def test_detect_requires_ventoy_setup(self):
        content = self._read_service("mados-persistence-detect.service")
        self.assertIn("Requires=mados-ventoy-setup.service", content)

    def test_sync_requires_detect(self):
        content = self._read_service("mados-persist-sync.service")
        self.assertIn("Requires=mados-persistence-detect.service", content)


class TestPersistenceServicesEnabled(unittest.TestCase):
    """Test that all persistence services are enabled (have symlinks)."""

    WANTS_DIR = os.path.join(SYSTEMD_DIR, "multi-user.target.wants")

    def test_ventoy_setup_enabled(self):
        link = os.path.join(self.WANTS_DIR, "mados-ventoy-setup.service")
        self.assertTrue(
            os.path.islink(link) or os.path.exists(link),
            "mados-ventoy-setup.service not enabled in multi-user.target.wants",
        )

    def test_persistence_detect_enabled(self):
        link = os.path.join(self.WANTS_DIR, "mados-persistence-detect.service")
        self.assertTrue(
            os.path.islink(link) or os.path.exists(link),
            "mados-persistence-detect.service not enabled in multi-user.target.wants",
        )

    def test_persist_sync_enabled(self):
        link = os.path.join(self.WANTS_DIR, "mados-persist-sync.service")
        self.assertTrue(
            os.path.islink(link) or os.path.exists(link),
            "mados-persist-sync.service not enabled in multi-user.target.wants",
        )


class TestPersistenceCLICommands(unittest.TestCase):
    """Test that mados-persistence CLI has expected commands."""

    def setUp(self):
        self.path = os.path.join(BIN_DIR, "mados-persistence")
        if not os.path.exists(self.path):
            self.skipTest("CLI not found")
        with open(self.path, "r") as f:
            self.content = f.read()

    def test_has_status_command(self):
        self.assertIn("status", self.content, "CLI missing 'status' command")

    def test_has_info_command(self):
        self.assertIn("info", self.content, "CLI missing 'info' command")

    def test_has_sync_command(self):
        self.assertIn("sync", self.content, "CLI missing 'sync' command")

    def test_has_ventoy_docs(self):
        self.assertIn("Ventoy", self.content, "CLI missing Ventoy documentation")

    def test_reads_state_file(self):
        self.assertIn(
            "/run/mados-persist.env",
            self.content,
            "CLI should read state from /run/mados-persist.env",
        )

    def test_no_broken_enable_disable(self):
        """CLI should not have enable/disable commands that export useless vars."""
        # These were removed because export in a script doesn't affect parent shell
        self.assertNotIn(
            "cmd_enable",
            self.content,
            "CLI should not have broken enable command",
        )
        self.assertNotIn(
            "cmd_disable",
            self.content,
            "CLI should not have broken disable command",
        )


class TestPersistenceStateFileConsistency(unittest.TestCase):
    """Test that all scripts use the same state file path."""

    STATE_FILE_PATH = "/run/mados-persist.env"

    def test_ventoy_setup_writes_state_file(self):
        path = os.path.join(BIN_DIR, "mados-ventoy-setup.sh")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn(self.STATE_FILE_PATH, content)

    def test_persist_detect_reads_state_file(self):
        path = os.path.join(BIN_DIR, "mados-persist-detect.sh")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn(self.STATE_FILE_PATH, content)

    def test_persist_sync_reads_state_file(self):
        path = os.path.join(BIN_DIR, "mados-persist-sync.sh")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn(self.STATE_FILE_PATH, content)

    def test_cli_reads_state_file(self):
        path = os.path.join(BIN_DIR, "mados-persistence")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn(self.STATE_FILE_PATH, content)


class TestPersistenceVentoySetupNoCreation(unittest.TestCase):
    """Test that ventoy-setup.sh does NOT attempt to create persistence during boot."""

    def setUp(self):
        path = os.path.join(BIN_DIR, "mados-ventoy-setup.sh")
        with open(path, "r") as f:
            self.content = f.read()

    def test_no_dd_command(self):
        """Should not use dd to create files on the USB during boot."""
        self.assertNotIn(
            "dd if=/dev/zero",
            self.content,
            "ventoy-setup.sh should NOT create files with dd during boot",
        )

    def test_no_mkfs(self):
        """Should not format anything during boot."""
        self.assertNotIn(
            "mkfs.ext4",
            self.content,
            "ventoy-setup.sh should NOT format filesystems during boot",
        )

    def test_no_parted(self):
        """Should not try to partition the USB during boot."""
        self.assertNotIn(
            "parted",
            self.content,
            "ventoy-setup.sh should NOT partition disks during boot",
        )

    def test_writes_state_file(self):
        """Should write detection results to state file."""
        self.assertIn("write_state", self.content)


class TestGrubPersistenceEntries(unittest.TestCase):
    """Test that GRUB entries use cow_label for real persistence."""

    def setUp(self):
        grub_path = os.path.join(GRUB_DIR, "grub.cfg")
        with open(grub_path, "r") as f:
            self.grub_content = f.read()

    def test_persistence_entry_uses_cow_label(self):
        """Persistence entries should use cow_label=mados-persist, not just cow_spacesize."""
        self.assertIn(
            "cow_label=mados-persist",
            self.grub_content,
            "GRUB persistence entries must use cow_label=mados-persist for real persistence",
        )

    def test_no_persistence_entry_with_only_cow_spacesize(self):
        """Persistence entries should NOT rely only on cow_spacesize (which is just RAM)."""
        # Find lines with "Persistence" in menuentry that also have cow_spacesize but no cow_label
        lines = self.grub_content.split("\n")
        for i, line in enumerate(lines):
            if "Persistence" in line and "menuentry" in line:
                # Check the linux line (next few lines)
                block = "\n".join(lines[i : i + 5])
                if "cow_spacesize" in block:
                    self.assertIn(
                        "cow_label",
                        block,
                        f"Persistence entry at line {i+1} uses cow_spacesize without cow_label",
                    )


class TestLoopbackPersistenceEntry(unittest.TestCase):
    """Test that loopback.cfg (used by Ventoy) has persistence option."""

    def setUp(self):
        path = os.path.join(GRUB_DIR, "loopback.cfg")
        with open(path, "r") as f:
            self.content = f.read()

    def test_has_persistence_entry(self):
        self.assertIn(
            "Persistence",
            self.content,
            "loopback.cfg should have a persistence menu entry for Ventoy users",
        )

    def test_persistence_uses_cow_label(self):
        self.assertIn(
            "cow_label=mados-persist",
            self.content,
            "loopback.cfg persistence entry should use cow_label=mados-persist",
        )


class TestSyslinuxPersistenceEntries(unittest.TestCase):
    """Test that syslinux entries use cow_label for persistence."""

    def setUp(self):
        path = os.path.join(SYSLINUX_DIR, "archiso_sys-linux.cfg")
        with open(path, "r") as f:
            self.content = f.read()

    def test_persistence_entry_uses_cow_label(self):
        self.assertIn(
            "cow_label=mados-persist",
            self.content,
            "Syslinux persistence entry must use cow_label=mados-persist",
        )


class TestVentoyPersistConfig(unittest.TestCase):
    """Test that the ventoy-persist.conf is valid."""

    def test_config_exists(self):
        path = os.path.join(AIROOTFS, "etc", "mados", "ventoy-persist.conf")
        self.assertTrue(os.path.exists(path))

    def test_config_has_size(self):
        path = os.path.join(AIROOTFS, "etc", "mados", "ventoy-persist.conf")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn("VENTOY_PERSIST_SIZE_MB", content)

    def test_config_has_min_free_space(self):
        path = os.path.join(AIROOTFS, "etc", "mados", "ventoy-persist.conf")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn("MIN_FREE_SPACE_MB", content)


if __name__ == "__main__":
    unittest.main()
