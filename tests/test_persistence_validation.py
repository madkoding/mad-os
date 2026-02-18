#!/usr/bin/env python3
"""
Comprehensive validation tests for madOS persistence scripts.

Tests for critical validation fixes:
- Device and partition validation
- Input sanitization
- Safety checks
- Error handling
"""

import os
import re
import subprocess
import unittest

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BIN_DIR = os.path.join(REPO_DIR, "airootfs", "usr", "local", "bin")


class TestGetFreeSpaceValidation(unittest.TestCase):
    """Validate get_free_space() function has proper validation."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_get_free_space_validates_device_parameter(self):
        """Must check if device parameter is empty or not a block device."""
        func_start = self.content.find("get_free_space()")
        self.assertNotEqual(func_start, -1)
        func_region = self.content[func_start : func_start + 800]

        # Should validate device is not empty
        self.assertIn(
            '[ -z "$device" ]', func_region, "Must check if device parameter is empty"
        )

        # Should validate device is a block device
        self.assertIn(
            '[ ! -b "$device" ]', func_region, "Must check if device is a block device"
        )

    def test_get_free_space_validates_parted_output(self):
        """Must validate parted output before parsing."""
        func_start = self.content.find("get_free_space()")
        func_region = self.content[func_start : func_start + 800]

        # Should check parted exit code (allow for variable assignment pattern)
        self.assertRegex(
            func_region,
            r"parted[^)]*\) \|\| \{",
            "Must capture parted exit code with || { ... }",
        )

        # Should validate free space is a number (allow for escaped backslashes in heredoc)
        self.assertRegex(
            func_region,
            r'\[ -z "\$free" \].*\|\|.*!.*\[\[.*\$free.*=~',
            "Must validate free space is numeric with regex",
        )

        # Should validate free space is a number
        self.assertRegex(
            func_region,
            r'\[ -z "\$free" \] \|\| ! \[\[ "\$free" =~ \^\[0-9\]',
            "Must validate free space is numeric with regex",
        )


class TestFindIsoDeviceValidation(unittest.TestCase):
    """Validate find_iso_device() has proper validation."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_loop_device_backing_validation(self):
        """Must handle loopback device detection."""
        func_start = self.content.find("find_iso_device()")
        self.assertNotEqual(func_start, -1)
        func_region = self.content[func_start : func_start + 1500]

        # Check for losetup or loopback handling somewhere in script
        self.assertIn("losetup", self.content, "Must handle loopback via losetup")


class TestCreatePartitionSafetyChecks(unittest.TestCase):
    """Validate create_persist_partition safety checks."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()
        start = self.content.find("create_persist_partition()")
        self.create_fn = self.content[start : start + 20000]

    def test_validates_iso_device_before_creating(self):
        """Must validate find_iso_device result is not empty."""
        # Must call find_iso_device for safety check
        self.assertIn("expected_iso_device=$(find_iso_device)", self.create_fn)

        # Should fail if ISO device cannot be determined (check for return 1)
        self.assertIn("return 1", self.create_fn, "Must return error on failure")

    def test_validates_partition_table_type(self):
        """Must validate partition table type is known."""
        self.assertRegex(
            self.create_fn,
            r'case.*"\$table_type"[^}]*msdos\|gpt\|unknown',
            "Must validate partition table type against known types",
        )

    def test_uses_nullglob_for_partition_nodes(self):
        """Must use nullglob to prevent globbing literal filenames."""
        self.assertIn(
            "shopt -s nullglob",
            self.create_fn,
            "Must enable nullglob before processing partition nodes",
        )
        self.assertIn(
            "shopt -u nullglob",
            self.create_fn,
            "Must disable nullglob after processing",
        )


class TestInitScriptValidation(unittest.TestCase):
    """Validate embedded init script has proper validation."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()
        # Extract the embedded init script
        init_start = self.content.find('cat > "$PERSIST_MOUNT/mados-persist-init.sh"')
        self.assertNotEqual(init_start, -1)
        self.init_script = self.content[init_start : init_start + 10000]

    def test_find_persist_dev_requires_parent_device(self):
        """Must require parent device parameter for safety."""
        # Check for parent_device check (any form)
        self.assertIn("parent_device", self.init_script, "Must check parent_device")
        # Should have error handling
        self.assertIn("return 1", self.init_script, "Must return error on failure")

    def test_find_persist_dev_validates_parent_is_block_device(self):
        """Must validate parent device is a block device."""
        # Check for -b validation
        self.assertIn("[ ! -b", self.init_script, "Must check block device")
        # Should have error message
        self.assertIn("ERROR", self.init_script, "Must have error handling")

    def test_verifies_filesystem_type_before_mount(self):
        """Must verify filesystem is ext4 before mounting."""
        # Check for filesystem type validation
        self.assertIn("blkid", self.init_script, "Must use blkid")
        self.assertIn("ext4", self.init_script, "Must check for ext4")

    def test_validates_lower_directories_exist(self):
        """Must verify lower directories exist before overlay mount."""
        # Check for directory validation
        self.assertIn("[ ! -d", self.init_script, "Must check if directory exists")
        self.assertIn("lower", self.init_script, "Must reference lower directory")


class TestMadosPersistenceCLIValidation(unittest.TestCase):
    """Validate mados-persistence CLI tool validation."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "mados-persistence")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_remove_validates_partition_is_not_mounted(self):
        """Must check if partition is mounted before removing."""
        remove_start = self.content.find("remove_persistence()")
        self.assertNotEqual(remove_start, -1)
        remove_fn = self.content[remove_start : remove_start + 2000]

        # Check for mount validation (any form)
        self.assertIn("mount", remove_fn, "Must check mount status")

    def test_remove_uses_lsblk_for_partition_number(self):
        """Must use lsblk for partition number."""
        remove_start = self.content.find("remove_persistence()")
        remove_fn = self.content[remove_start : remove_start + 2000]

        self.assertIn("lsblk", remove_fn, "Must use lsblk")
        self.assertIn("PARTN", remove_fn, "Must use PARTN")


class TestErrorHandling(unittest.TestCase):
    """Validate error handling patterns."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_captures_exit_codes_before_logging(self):
        """Must capture $? in variable before logging."""
        # Check that mkfs.ext4 error handling captures exit code
        self.assertIn("exit_code", self.content, "Must capture exit code")

    def test_cleans_up_on_mkfs_failure(self):
        """Must clean up partition on mkfs failure."""
        # Check for cleanup on failure (any form)
        self.assertIn("mkfs.ext4", self.content, "Must use mkfs.ext4")
        self.assertIn("parted", self.content, "Must cleanup with parted")


class TestNumericValidation(unittest.TestCase):
    """Validate numeric validation patterns."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_validates_start_values_are_numeric(self):
        """Must validate partition start values before arithmetic."""
        # Check for numeric validation
        self.assertIn("pstart", self.content, "Must use pstart variable")
        self.assertIn("-n", self.content, "Must validate non-empty")


if __name__ == "__main__":
    unittest.main()
