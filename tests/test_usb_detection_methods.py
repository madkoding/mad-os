#!/usr/bin/env python3
"""
Tests for USB device detection in persistence setup.

These tests validate that find_iso_device() can correctly identify
the boot USB device using multiple detection methods, even when
the ISO was written with dd and has no visible ARCHISO label.
"""

import os
import re
import subprocess
import unittest
from unittest.mock import patch, MagicMock, mock_open

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BIN_DIR = os.path.join(REPO_DIR, "airootfs", "usr", "local", "bin")


class TestFindIsoDeviceDetectionMethods(unittest.TestCase):
    """Test that find_iso_device uses multiple detection methods."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()
        # Extract the find_iso_device function
        start = self.content.find("find_iso_device() {")
        self.assertNotEqual(start, -1, "Must have find_iso_device function")
        # Find the end of the function (next function at same indentation level)
        end = self.content.find("\n}\n\n", start)
        if end == -1:
            end = len(self.content)
        else:
            end += 3  # Include the closing brace
        self.find_fn = self.content[start:end]

    def test_method_1_proc_cmdline_priority(self):
        """Method 1 (proc/cmdline) should come first."""
        proc_pos = self.find_fn.find("/proc/cmdline")
        archiso_pos = self.find_fn.find("/run/archiso/bootmnt")
        self.assertNotEqual(proc_pos, -1, "Must check /proc/cmdline")
        self.assertLess(
            proc_pos,
            archiso_pos,
            "/proc/cmdline check must come before /run/archiso/bootmnt",
        )

    def test_method_2_bootmnt_mount(self):
        """Method 2 should check /run/archiso/bootmnt mount point."""
        self.assertIn(
            "/run/archiso/bootmnt",
            self.find_fn,
            "Must check /run/archiso/bootmnt mount point",
        )

    def test_method_3_boot_files_search(self):
        """Method 3 should search for boot files on removable devices."""
        # Check for boot file locations
        boot_patterns = [
            r"arch/boot/x86_64/vmlinuz-linux",
            r"arch/boot/vmlinuz-linux",
            r"EFI/BOOT/BOOTx64.EFI",
        ]
        for pattern in boot_patterns:
            self.assertIn(
                pattern,
                self.find_fn,
                f"Must search for {pattern} to detect ISO",
            )

    def test_method_4_iso9660_filesystem(self):
        """Method 4 should check for iso9660 filesystem."""
        self.assertIn(
            'iso9660"',
            self.find_fn,
            "Must check for iso9660 filesystem",
        )

    def test_method_5_label_fallback(self):
        """Method 5 (legacy label search) should be last."""
        label_pos = self.find_fn.find("ARCHISO|MADOS")
        iso9660_pos = self.find_fn.find("iso9660")
        self.assertNotEqual(label_pos, -1, "Must have label fallback")
        self.assertGreater(
            label_pos,
            iso9660_pos,
            "Label search should be after iso9660 check (last method)",
        )

    def test_img_dev_parameter_handling(self):
        """Should handle img_dev= parameter from cmdline."""
        self.assertIn(
            "img_dev",
            self.find_fn,
            "Must search for img_dev parameter",
        )
        # Check UUID format
        self.assertIn(
            "UUID=",
            self.find_fn,
            "Must handle UUID= format",
        )
        # Check PARTUUID format
        self.assertIn(
            "PARTUUID=",
            self.find_fn,
            "Must handle PARTUUID= format",
        )

    def test_archisolabel_parameter_handling(self):
        """Should handle archisolabel= parameter from cmdline."""
        self.assertIn(
            "archisolabel",
            self.find_fn,
            "Must search for archisolabel parameter",
        )

    def test_removable_devices_filter(self):
        """Should filter for removable devices when searching."""
        # Look for RM column in lsblk when searching for removable devices
        self.assertRegex(
            self.find_fn,
            r"lsblk.*RM",
            "Must use RM column to filter removable devices",
        )

    def test_logging_for_debugging(self):
        """Should log debug information at each step."""
        # Should log the cmdline contents
        self.assertRegex(
            self.find_fn,
            r"log.*cmdline",
            "Must log cmdline for debugging",
        )
        # Should log which method found the device
        self.assertRegex(
            self.find_fn,
            r"log.*Found.*via",
            "Must log which detection method succeeded",
        )


class TestUsbDetectionEdgeCases(unittest.TestCase):
    """Test edge cases for USB detection."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_handles_loop_devices(self):
        """Should resolve loop devices to backing device."""
        # This is already tested elsewhere, but ensure it's still present
        self.assertIn(
            "losetup",
            self.content,
            "Must handle loop device resolution",
        )

    def test_error_handling_for_missing_device(self):
        """Should handle case when no device is found."""
        self.assertIn(
            "Could not find ISO boot device",
            self.content,
            "Must log error when device not found",
        )


class TestDetectionMethodOrder(unittest.TestCase):
    """Verify detection methods are ordered correctly."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()
        # Extract just the find_iso_device function
        start = self.content.find("find_iso_device() {")
        end = self.content.find("\n}\n\n#", start)
        if end == -1:
            end = self.content.find("\n}\n\nfind_", start)
        self.find_fn = self.content[start:end]

    def test_all_methods_present(self):
        """All detection methods should be implemented."""
        methods = [
            ("/proc/cmdline", "Method 1: cmdline"),
            ("/run/archiso/bootmnt", "Method 2: bootmnt"),
            ("arch/boot", "Method 3: boot files"),
            ("iso9660", "Method 4: iso9660"),
            ("ARCHISO|MADOS", "Method 5: labels"),
        ]
        for pattern, desc in methods:
            with self.subTest(method=desc):
                self.assertIn(pattern, self.find_fn, f"Missing {desc}")

    def test_early_exit_on_success(self):
        """Should return immediately when device is found."""
        # After finding a device, should echo and not continue to other methods
        # Check that iso_device is set and returned
        self.assertIn(
            'echo "$iso_device"',
            self.find_fn,
            "Must echo iso_device at end",
        )


class TestScriptSyntax(unittest.TestCase):
    """Verify the updated script has valid syntax."""

    def test_bash_syntax_valid(self):
        """Script should pass bash syntax check."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        result = subprocess.run(
            ["bash", "-n", script_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Syntax error in setup-persistence.sh:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
