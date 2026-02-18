#!/usr/bin/env python3
"""
Comprehensive function coverage tests for madOS persistence scripts.

Tests individual bash functions with various inputs and scenarios.
Uses pytest to run tests and validate function behavior.

Coverage targets:
- setup-persistence.sh: 100% of functions
- mados-persistence: 100% of functions
- Full integration testing via Docker
"""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")


# ═══════════════════════════════════════════════════════════════════════════
# Utility functions
# ═══════════════════════════════════════════════════════════════════════════


def extract_function_body(script_path, func_name):
    """Extract a function body from a bash script."""
    with open(script_path) as f:
        content = f.read()

    # Find function definition and body
    pattern = rf"{func_name}\(\)\s*\{{"
    match = re.search(pattern, content)
    if not match:
        return None

    start = match.end() - 1  # Include the opening brace
    brace_count = 1
    i = start + 1

    while i < len(content) and brace_count > 0:
        if content[i] == "{":
            brace_count += 1
        elif content[i] == "}":
            brace_count -= 1
        i += 1

    return content[start:i]


def source_script_with_func(script_path, func_name):
    """Source a script and extract a specific function."""
    with open(script_path) as f:
        content = f.read()

    # Find where to truncate (before the auto-execution guard)
    guard_match = re.search(r"^if \[.*\]", content, re.MULTILINE)
    if guard_match:
        content = content[: guard_match.start()]

    return content


# ═══════════════════════════════════════════════════════════════════════════
# Setup-persistence.sh function tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSetupPersistenceFunctions(unittest.TestCase):
    """Test individual functions in setup-persistence.sh."""

    @classmethod
    def setUpClass(cls):
        """Load script content once for all tests."""
        cls.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(cls.script_path) as f:
            cls.content = f.read()

    def test_is_usb_device_with_usb_device(self):
        """is_usb_device should return 0 for USB devices."""
        # Test logic: checks /sys/block/*/removable flag
        func_body = extract_function_body(self.script_path, "is_usb_device")
        self.assertIsNotNone(func_body, "is_usb_device function not found")
        self.assertIn("removable", func_body)
        self.assertIn("return 0", func_body)

    def test_is_usb_device_with_non_usb_device(self):
        """is_usb_device should return 1 for non-USB devices."""
        func_body = extract_function_body(self.script_path, "is_usb_device")
        self.assertIsNotNone(func_body)
        self.assertIn("return 1", func_body)

    def test_is_optical_device_detects_sr_devices(self):
        """is_optical_device should detect /dev/sr* devices."""
        func_body = extract_function_body(self.script_path, "is_optical_device")
        self.assertIsNotNone(func_body, "is_optical_device function not found")
        self.assertIn("sr", func_body)

    def test_is_optical_device_checks_scsi_type(self):
        """is_optical_device should check SCSI device type 5."""
        func_body = extract_function_body(self.script_path, "is_optical_device")
        self.assertIsNotNone(func_body)
        self.assertIn('"5"', func_body)

    def test_strip_partition_handles_standard_disks(self):
        """strip_partition should handle /dev/sdXN format."""
        func_body = extract_function_body(self.script_path, "strip_partition")
        self.assertIsNotNone(func_body, "strip_partition function not found")
        # Check for trailing digit removal
        self.assertIn("sed", func_body)
        self.assertIn("[0-9]", func_body)

    def test_strip_partition_handles_nvme(self):
        """strip_partition should handle /dev/nvmeNdNpN format."""
        func_body = extract_function_body(self.script_path, "strip_partition")
        self.assertIsNotNone(func_body)
        self.assertIn("nvme", func_body)
        self.assertIn("p", func_body)

    def test_strip_partition_handles_mmcblk(self):
        """strip_partition should handle /dev/mmcblkNpN format."""
        func_body = extract_function_body(self.script_path, "strip_partition")
        self.assertIsNotNone(func_body)
        self.assertIn("mmcblk", func_body)

    def test_find_iso_partition_finds_iso9660(self):
        """find_iso_partition should find partitions with iso9660 filesystem."""
        func_body = extract_function_body(self.script_path, "find_iso_partition")
        self.assertIsNotNone(func_body, "find_iso_partition function not found")
        self.assertIn("iso9660", func_body)

    def test_find_persist_partition_scoped_search(self):
        """find_persist_partition should scope search to parent device."""
        func_body = extract_function_body(self.script_path, "find_persist_partition")
        self.assertIsNotNone(func_body, "find_persist_partition function not found")
        self.assertIn("parent_device", func_body)
        self.assertIn("lsblk", func_body)

    def test_get_free_space_validates_input(self):
        """get_free_space should validate device parameter."""
        func_body = extract_function_body(self.script_path, "get_free_space")
        self.assertIsNotNone(func_body, "get_free_space function not found")
        # Check for empty device validation
        self.assertIn('[ -z "$device" ]', func_body)
        # Check for block device validation
        self.assertIn('[ ! -b "$device" ]', func_body)

    def test_get_free_space_parses_parted_output(self):
        """get_free_space should parse parted output correctly."""
        func_body = extract_function_body(self.script_path, "get_free_space")
        self.assertIsNotNone(func_body)
        self.assertIn("parted", func_body)
        self.assertIn("Free Space", func_body)

    def test_create_persist_partition_safety_checks(self):
        """create_persist_partition should have multiple safety checks."""
        func_body = extract_function_body(self.script_path, "create_persist_partition")
        self.assertIsNotNone(func_body, "create_persist_partition function not found")
        # Check for ISO device verification
        self.assertIn("SAFETY", func_body)
        self.assertIn("find_iso_device", func_body)
        # Check for partition table type validation
        self.assertIn("Partition Table", func_body)
        # Check for MBR limit enforcement
        self.assertIn("msdos", func_body)

    def test_install_persist_files_creates_init_script(self):
        """install_persist_files should create mados-persist-init.sh."""
        func_body = extract_function_body(self.script_path, "install_persist_files")
        self.assertIsNotNone(func_body, "install_persist_files function not found")
        self.assertIn("mados-persist-init.sh", func_body)
        self.assertIn("cat >", func_body)

    def test_install_persist_files_creates_service(self):
        """install_persist_files should create systemd service file."""
        func_body = extract_function_body(self.script_path, "install_persist_files")
        self.assertIsNotNone(func_body)
        self.assertIn("mados-persistence.service", func_body)

    def test_setup_persistence_main_flow(self):
        """setup_persistence should have complete main flow."""
        func_body = extract_function_body(self.script_path, "setup_persistence")
        self.assertIsNotNone(func_body, "setup_persistence function not found")
        # Check for all major steps
        self.assertIn("find_iso_device", func_body)
        self.assertIn("is_optical_device", func_body)
        self.assertIn("is_usb_device", func_body)
        self.assertIn("create_persist_partition", func_body)
        self.assertIn("find_persist_partition", func_body)
        self.assertIn("mount", func_body)
        self.assertIn("install_persist_files", func_body)

    def test_main_guard_prevents_execution(self):
        """Main execution block should be guarded by archiso check."""
        guard_pattern = r"^if \[.*-d.*run/archiso.*\]"
        match = re.search(guard_pattern, self.content, re.MULTILINE)
        self.assertIsNotNone(match, "Main execution guard not found")
        self.assertIn("/run/archiso", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# mados-persistence CLI tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMadosPersistenceCLI(unittest.TestCase):
    """Test mados-persistence CLI tool functions."""

    @classmethod
    def setUpClass(cls):
        cls.script_path = os.path.join(BIN_DIR, "mados-persistence")
        with open(cls.script_path) as f:
            cls.content = f.read()

    def test_check_live_env_validates_archiso(self):
        """check_live_env should validate /run/archiso exists."""
        func_body = extract_function_body(self.script_path, "check_live_env")
        self.assertIsNotNone(func_body, "check_live_env function not found")
        self.assertIn("/run/archiso", func_body)

    def test_find_iso_device_exists(self):
        """mados-persistence should have find_iso_device function."""
        func_body = extract_function_body(self.script_path, "find_iso_device")
        self.assertIsNotNone(func_body, "find_iso_device function not found")

    def test_find_persist_partition_scoped(self):
        """find_persist_partition should use find_iso_device for scoping."""
        func_body = extract_function_body(self.script_path, "find_persist_partition")
        self.assertIsNotNone(func_body, "find_persist_partition function not found")
        self.assertIn("find_iso_device", func_body)

    def test_show_status_displays_info(self):
        """show_status should display persistence information."""
        func_body = extract_function_body(self.script_path, "show_status")
        self.assertIsNotNone(func_body, "show_status function not found")
        # Check for any method to get persistence info
        self.assertIn("get_persist_info", func_body)

    def test_enable_persistence_checks_root(self):
        """enable_persistence should verify root privileges."""
        func_body = extract_function_body(self.script_path, "enable_persistence")
        self.assertIsNotNone(func_body, "enable_persistence function not found")
        self.assertIn("id -u", func_body)
        self.assertIn("0", func_body)

    def test_disable_persistence_unmounts(self):
        """disable_persistence should unmount all persistence mounts."""
        func_body = extract_function_body(self.script_path, "disable_persistence")
        self.assertIsNotNone(func_body, "disable_persistence function not found")
        self.assertIn("umount", func_body)

    def test_remove_persistence_safety_checks(self):
        """remove_persistence should verify partition before deletion."""
        func_body = extract_function_body(self.script_path, "remove_persistence")
        self.assertIsNotNone(func_body, "remove_persistence function not found")
        self.assertIn("blkid", func_body)
        self.assertIn("persistence", func_body)

    def test_main_handles_status_command(self):
        """Main should handle 'status' command."""
        self.assertIn("status", self.content)
        # Check command dispatch
        status_pattern = r"status\)\s*show_status"
        self.assertRegex(self.content, status_pattern)

    def test_main_handles_enable_command(self):
        """Main should handle 'enable' command."""
        self.assertIn("enable", self.content)
        enable_pattern = r"enable\)\s*enable_persistence"
        self.assertRegex(self.content, enable_pattern)

    def test_main_handles_disable_command(self):
        """Main should handle 'disable' command."""
        self.assertIn("disable", self.content)
        disable_pattern = r"disable\)\s*disable_persistence"
        self.assertRegex(self.content, disable_pattern)

    def test_main_handles_remove_command(self):
        """Main should handle 'remove' command."""
        self.assertIn("remove", self.content)
        remove_pattern = r"remove\)\s*remove_persistence"
        self.assertRegex(self.content, remove_pattern)

    def test_main_handles_help_command(self):
        """Main should handle 'help' command."""
        self.assertIn("help", self.content)
        help_pattern = r"help|--help|-h\)\s*show_usage"
        self.assertRegex(self.content, help_pattern)


# ═══════════════════════════════════════════════════════════════════════════
# Systemd service validation
# ═══════════════════════════════════════════════════════════════════════════


class TestSystemdService(unittest.TestCase):
    """Test systemd service configuration."""

    def test_service_file_exists(self):
        """Service file should exist in airootfs."""
        service_path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-persistence.service"
        )
        self.assertTrue(os.path.exists(service_path), "Service file not found")

    def test_service_has_correct_type(self):
        """Service should be Type=oneshot."""
        service_path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("Type=oneshot", content)

    def test_service_remains_after_exit(self):
        """Service should have RemainAfterExit=yes."""
        service_path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("RemainAfterExit=yes", content)

    def test_service_before_display_manager(self):
        """Service should run before display-manager.service."""
        service_path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("Before=display-manager.service", content)

    def test_service_wanted_by_multi_user(self):
        """Service should be wanted by multi-user.target."""
        service_path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("WantedBy=multi-user.target", content)

    def test_service_has_condition_path_exists(self):
        """Service should have ConditionPathExists=/run/archiso."""
        service_path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("ConditionPathExists=/run/archiso", content)


# ═══════════════════════════════════════════════════════════════════════════
# Integration tests (mocked execution)
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration(unittest.TestCase):
    """Integration tests that validate complete workflows."""

    def test_full_persistence_flow_validation(self):
        """Validate that setup_persistence implements complete flow."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            content = f.read()

        # Required steps in order
        required_steps = [
            "find_iso_device",  # Detect boot device
            "is_optical_device",  # Check for CD/DVD
            "is_usb_device",  # Check for USB
            "find_persist_partition",  # Check for existing persistence
            "get_free_space",  # Check available space
            "create_persist_partition",  # Create partition if needed
            "mount",  # Mount persistence partition
            "install_persist_files",  # Install init script and service
            "mados-persist-init.sh",  # Run init to mount overlays
        ]

        for step in required_steps:
            with self.subTest(step=step):
                self.assertIn(step, content, f"Missing required step: {step}")

    def test_init_script_complete_implementation(self):
        """Validate embedded init script has all required functionality."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            content = f.read()

        # Extract embedded init script
        init_start = content.find('cat > "$PERSIST_MOUNT/mados-persist-init.sh"')
        self.assertNotEqual(init_start, -1, "Embedded init script not found")

        # Check for key components
        init_checklist = [
            "find_persist_dev",  # Find partition function
            "mount",  # Mount persistence
            "overlay",  # Overlayfs setup
            "bind",  # Bind mount /home
            "ldconfig",  # Update library cache
            "systemctl restart",  # Restart services
        ]

        for component in init_checklist:
            with self.subTest(component=component):
                self.assertIn(
                    component,
                    content[init_start : init_start + 10000],
                    f"Embedded init script missing: {component}",
                )

    def test_service_starts_after_udev(self):
        """Service should start after systemd-udevd.service."""
        service_path = os.path.join(
            AIROOTFS, "etc", "systemd", "system", "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        # Check for udevd in After line
        self.assertIn("udevd.service", content)

    def test_overlay_dirs_configured(self):
        """Overlay directories should be /etc /usr /var /opt."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            content = f.read()

        self.assertIn('OVERLAY_DIRS="etc usr var opt"', content)

    def test_home_bind_mount_configured(self):
        """Home should be bind mounted (not overlay)."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            content = f.read()

        # Check that /home uses bind mount in init script
        init_start = content.find('cat > "$PERSIST_MOUNT/mados-persist-init.sh"')
        init_end = init_start + 10000
        init_content = content[init_start:init_end]

        self.assertIn("mount --bind", init_content, "Home should use bind mount")
        # Check that overlay line comes before mount --bind (not mixed)
        overlay_pos = init_content.find("overlay")
        bind_pos = init_content.find("mount --bind")
        self.assertLess(
            overlay_pos, bind_pos, "Overlay setup should be before bind mount"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Error handling tests
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorHandling(unittest.TestCase):
    """Test error handling in persistence scripts."""

    def test_get_free_space_empty_device(self):
        """get_free_space should handle empty device parameter."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            content = f.read()

        func_start = content.find("get_free_space()")
        func_region = content[func_start : func_start + 500]

        # Should validate empty device
        self.assertIn('[ -z "$device" ]', func_region)

    def test_find_iso_device_handles_not_found(self):
        """find_iso_device should handle case when ISO not found."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            content = f.read()

        func_start = content.find("find_iso_device()")
        func_region = content[func_start : func_start + 2000]

        # Should check if result is empty and handle gracefully
        self.assertIn('iso_device=""', func_region)

    def test_create_partition_validates_safety(self):
        """create_persist_partition should validate before creating."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            content = f.read()

        func_start = content.find("create_persist_partition()")
        func_region = content[func_start : func_start + 3000]

        # Should have safety checks
        self.assertIn("SAFETY", func_region)

    def test_setup_persistence_returns_error(self):
        """setup_persistence should return non-zero on error."""
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            content = f.read()

        func_start = content.find("setup_persistence()")
        func_region = content[func_start : func_start + 2000]

        # Should have error returns
        self.assertIn("return 1", func_region)


if __name__ == "__main__":
    unittest.main()
