#!/usr/bin/env python3
"""
Unit tests for find_iso_device() function.

Tests the logic of ISO device detection without running the full script.
This approach provides better test isolation and reliability.
"""

import os
import unittest
from pathlib import Path


# Paths
REPO_DIR = Path(__file__).parent.parent
SETUP_SCRIPT = REPO_DIR / "airootfs" / "usr" / "local" / "bin" / "setup-persistence.sh"


class TestFindIsoDeviceLogic(unittest.TestCase):
    """Test find_iso_device() implementation logic."""

    @classmethod
    def setUpClass(cls):
        """Load script content once."""
        with open(SETUP_SCRIPT) as f:
            cls.content = f.read()

    def test_script_exists(self):
        """setup-persistence.sh should exist."""
        self.assertTrue(SETUP_SCRIPT.exists())

    def test_has_find_iso_device_function(self):
        """Script should define find_iso_device function."""
        self.assertIn("find_iso_device()", self.content)

    def test_find_iso_device_checks_proc_cmdline(self):
        """find_iso_device should check /proc/cmdline."""
        self.assertIn("/proc/cmdline", self.content)

    def test_find_iso_device_handles_img_dev_uuid(self):
        """find_iso_device should handle img_dev=UUID=xxxx."""
        self.assertIn("img_dev", self.content)
        self.assertIn("UUID=", self.content)

    def test_find_iso_device_handles_img_dev_partuuid(self):
        """find_iso_device should handle img_dev=PARTUUID=xxxx."""
        self.assertIn("PARTUUID=", self.content)

    def test_find_iso_device_handles_img_dev_path(self):
        """find_iso_device should handle img_dev=/dev/xxx."""
        self.assertIn("img_dev", self.content)
        self.assertIn("/dev/", self.content)

    def test_find_iso_device_checks_archisolabel(self):
        """find_iso_device should check archisolabel parameter."""
        self.assertIn("archisolabel", self.content)

    def test_find_iso_device_searches_bootmnt(self):
        """find_iso_device should check /run/archiso/bootmnt."""
        self.assertIn("/run/archiso/bootmnt", self.content)

    def test_find_iso_device_handles_loop_devices(self):
        """find_iso_device should resolve loopback devices."""
        self.assertIn("losetup", self.content)
        self.assertIn("BACK-FILE", self.content)

    def test_find_iso_device_searches_boot_files(self):
        """find_iso_device should search for boot files."""
        self.assertIn("vmlinuz", self.content)
        self.assertIn("arch/boot", self.content)

    def test_find_iso_device_checks_iso9660(self):
        """find_iso_device should check for iso9660 filesystem."""
        self.assertIn("iso9660", self.content)

    def test_find_iso_device_checks_label(self):
        """find_iso_device should search by label."""
        self.assertIn("ARCHISO", self.content)

    def test_find_iso_device_strips_partition(self):
        """find_iso_device should strip partition numbers."""
        self.assertIn("strip_partition", self.content)

    def test_find_iso_device_has_error_handling(self):
        """find_iso_device should handle errors gracefully."""
        self.assertIn("2>/dev/null", self.content)

    def test_find_iso_device_returns_empty_on_failure(self):
        """find_iso_device should return empty string if not found."""
        self.assertIn('iso_device=""', self.content)

    def test_find_iso_device_has_debug_logging(self):
        """find_iso_device should log debug information."""
        self.assertIn("Debug:", self.content)


class TestSetupPersistenceFunctions(unittest.TestCase):
    """Test setup-persistence.sh function implementations."""

    @classmethod
    def setUpClass(cls):
        with open(SETUP_SCRIPT) as f:
            cls.content = f.read()

    def test_has_is_optical_device_function(self):
        """Script should have is_optical_device function."""
        self.assertIn("is_optical_device()", self.content)

    def test_has_is_usb_device_function(self):
        """Script should have is_usb_device function."""
        self.assertIn("is_usb_device()", self.content)

    def test_has_strip_partition_function(self):
        """Script should have strip_partition function."""
        self.assertIn("strip_partition()", self.content)

    def test_has_find_persist_partition_function(self):
        """Script should have find_persist_partition function."""
        self.assertIn("find_persist_partition()", self.content)

    def test_has_get_free_space_function(self):
        """Script should have get_free_space function."""
        self.assertIn("get_free_space()", self.content)

    def test_has_create_persist_partition_function(self):
        """Script should have create_persist_partition function."""
        self.assertIn("create_persist_partition()", self.content)

    def test_has_install_persist_files_function(self):
        """Script should have install_persist_files function."""
        self.assertIn("install_persist_files()", self.content)

    def test_has_setup_persistence_function(self):
        """Script should have setup_persistence function."""
        self.assertIn("setup_persistence()", self.content)

    def test_is_optical_checks_sr_devices(self):
        """is_optical_device should check /dev/sr*."""
        self.assertIn("sr*", self.content)

    def test_is_optical_checks_scsi_type(self):
        """is_optical_device should check SCSI type 5."""
        self.assertIn('"5"', self.content)

    def test_is_usb_checks_removable(self):
        """is_usb_device should check removable flag."""
        self.assertIn("removable", self.content)

    def test_strip_handles_nvme(self):
        """strip_partition should handle nvme devices."""
        self.assertIn("nvme", self.content)

    def test_strip_handles_mmcblk(self):
        """strip_partition should handle mmcblk devices."""
        self.assertIn("mmcblk", self.content)

    def test_create_partition_checks_safety(self):
        """create_persist_partition should have safety checks."""
        self.assertIn("SAFETY", self.content)

    def test_create_partition_validates_table_type(self):
        """create_persist_partition should validate partition table."""
        self.assertIn("Partition Table", self.content)
        self.assertIn("msdos", self.content)
        self.assertIn("gpt", self.content)

    def test_install_creates_init_script(self):
        """install_persist_files should create init script."""
        self.assertIn("mados-persist-init.sh", self.content)

    def test_install_creates_service(self):
        """install_persist_files should create systemd service."""
        self.assertIn("mados-persistence.service", self.content)

    def test_has_main_guard(self):
        """Main execution should be guarded."""
        self.assertIn("if [ -d /run/archiso ]", self.content)

    def test_uses_udevadm_settle(self):
        """Should wait for udev to settle."""
        self.assertIn("udevadm settle", self.content)


class TestMadosPersistenceCLI(unittest.TestCase):
    """Test mados-persistence CLI tool."""

    def setUp(self):
        cli_path = REPO_DIR / "airootfs" / "usr" / "local" / "bin" / "mados-persistence"
        with open(cli_path) as f:
            self.content = f.read()

    def test_cli_exists(self):
        """mados-persistence should exist."""
        cli_path = REPO_DIR / "airootfs" / "usr" / "local" / "bin" / "mados-persistence"
        self.assertTrue(cli_path.exists())

    def test_has_check_live_env(self):
        """CLI should check live environment."""
        self.assertIn("check_live_env()", self.content)
        self.assertIn("/run/archiso", self.content)

    def test_has_find_iso_device(self):
        """CLI should have find_iso_device function."""
        self.assertIn("find_iso_device()", self.content)

    def test_has_find_persist_partition(self):
        """CLI should have find_persist_partition function."""
        self.assertIn("find_persist_partition()", self.content)

    def test_has_show_status(self):
        """CLI should have show_status function."""
        self.assertIn("show_status()", self.content)

    def test_has_enable_persistence(self):
        """CLI should have enable_persistence function."""
        self.assertIn("enable_persistence()", self.content)

    def test_has_disable_persistence(self):
        """CLI should have disable_persistence function."""
        self.assertIn("disable_persistence()", self.content)

    def test_has_remove_persistence(self):
        """CLI should have remove_persistence function."""
        self.assertIn("remove_persistence()", self.content)

    def test_has_help_command(self):
        """CLI should support help command."""
        self.assertIn("help", self.content)
        self.assertIn("--help", self.content)

    def test_main_handles_all_commands(self):
        """Main should dispatch all commands."""
        self.assertIn("status", self.content)
        self.assertIn("enable", self.content)
        self.assertIn("disable", self.content)
        self.assertIn("remove", self.content)

    def test_enable_requires_root(self):
        """enable should check root privileges."""
        self.assertIn("id -u", self.content)
        self.assertIn("0", self.content)

    def test_remove_verifies_label(self):
        """remove should verify partition label."""
        self.assertIn("blkid", self.content)
        self.assertIn("persistence", self.content)

    def test_cli_scopes_search(self):
        """CLI should scope partition search."""
        self.assertIn("find_iso_device", self.content)

    def test_cli_reads_boot_device(self):
        """CLI should read .mados-boot-device file."""
        self.assertIn(".mados-boot-device", self.content)


class TestSystemdService(unittest.TestCase):
    """Test systemd service configuration."""

    def test_service_exists(self):
        """Service file should exist."""
        service_path = (
            REPO_DIR
            / "airootfs"
            / "etc"
            / "systemd"
            / "system"
            / "mados-persistence.service"
        )
        self.assertTrue(service_path.exists())

    def test_service_type_oneshot(self):
        """Service should be Type=oneshot."""
        service_path = (
            REPO_DIR
            / "airootfs"
            / "etc"
            / "systemd"
            / "system"
            / "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("Type=oneshot", content)

    def test_service_remain_after_exit(self):
        """Service should have RemainAfterExit=yes."""
        service_path = (
            REPO_DIR
            / "airootfs"
            / "etc"
            / "systemd"
            / "system"
            / "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("RemainAfterExit=yes", content)

    def test_service_before_display_manager(self):
        """Service should run before display-manager.service."""
        service_path = (
            REPO_DIR
            / "airootfs"
            / "etc"
            / "systemd"
            / "system"
            / "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("Before=display-manager.service", content)

    def test_service_after_udev(self):
        """Service should start after systemd-udevd.service."""
        service_path = (
            REPO_DIR
            / "airootfs"
            / "etc"
            / "systemd"
            / "system"
            / "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("udevd.service", content)

    def test_service_wanted_by_multi_user(self):
        """Service should be wanted by multi-user.target."""
        service_path = (
            REPO_DIR
            / "airootfs"
            / "etc"
            / "systemd"
            / "system"
            / "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("WantedBy=multi-user.target", content)

    def test_service_has_condition(self):
        """Service should have ConditionPathExists."""
        service_path = (
            REPO_DIR
            / "airootfs"
            / "etc"
            / "systemd"
            / "system"
            / "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("ConditionPathExists=/run/archiso", content)

    def test_service_timeout_sufficient(self):
        """Service should have sufficient TimeoutStartSec."""
        service_path = (
            REPO_DIR
            / "airootfs"
            / "etc"
            / "systemd"
            / "system"
            / "mados-persistence.service"
        )
        with open(service_path) as f:
            content = f.read()
        self.assertIn("TimeoutStartSec=", content)
        # Should be at least 120 seconds for slow USB operations
        import re

        match = re.search(r"TimeoutStartSec=(\d+)", content)
        self.assertIsNotNone(match)
        timeout = int(match.group(1))
        self.assertGreaterEqual(timeout, 120)


if __name__ == "__main__":
    unittest.main()
