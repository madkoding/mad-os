#!/usr/bin/env python3
"""
Tests for madOS persistence and system shell scripts.

Validates syntax, structure, and configuration of bash scripts used for
persistent storage, system setup, and user-facing tools.

These tests run in CI without requiring actual hardware or a live USB
environment.
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
ETC_DIR = os.path.join(AIROOTFS, "etc")


# ═══════════════════════════════════════════════════════════════════════════
# Shell script syntax validation
# ═══════════════════════════════════════════════════════════════════════════
class TestShellScriptSyntax(unittest.TestCase):
    """Verify all shell scripts have valid bash syntax."""

    SHELL_SCRIPTS = [
        os.path.join(BIN_DIR, "setup-persistence.sh"),
        os.path.join(BIN_DIR, "mados-persistence"),
        os.path.join(BIN_DIR, "setup-ohmyzsh.sh"),
        os.path.join(BIN_DIR, "setup-opencode.sh"),
        os.path.join(BIN_DIR, "mados-audio-init.sh"),
        os.path.join(BIN_DIR, "toggle-demo-mode.sh"),
        os.path.join(AIROOTFS, "usr", "local", "lib", "mados-media-helper.sh"),
    ]

    def test_all_scripts_compile(self):
        """Every shell script should pass bash -n syntax check."""
        for script in self.SHELL_SCRIPTS:
            if not os.path.exists(script):
                continue
            with self.subTest(script=os.path.basename(script)):
                result = subprocess.run(
                    ["bash", "-n", script],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Syntax error in {os.path.basename(script)}:\n{result.stderr}",
                )


class TestShellScriptShebangs(unittest.TestCase):
    """Verify shell scripts have proper shebangs."""

    def _get_shell_scripts(self):
        scripts = []
        for fname in os.listdir(BIN_DIR):
            fpath = os.path.join(BIN_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, "rb") as f:
                first_bytes = f.read(4)
            if first_bytes[:2] == b"#!":
                with open(fpath) as f:
                    first_line = f.readline().strip()
                if "bash" in first_line or "sh" in first_line:
                    scripts.append(fpath)
        return scripts

    def test_shebangs_valid(self):
        for script in self._get_shell_scripts():
            with self.subTest(script=os.path.basename(script)):
                with open(script) as f:
                    shebang = f.readline().strip()
                self.assertTrue(
                    shebang.startswith("#!"),
                    f"{os.path.basename(script)}: Missing shebang",
                )
                self.assertTrue(
                    "bash" in shebang or "sh" in shebang,
                    f"{os.path.basename(script)}: Shebang doesn't reference bash/sh: {shebang}",
                )


# ═══════════════════════════════════════════════════════════════════════════
# setup-persistence.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupPersistenceScript(unittest.TestCase):
    """Validate structure and content of setup-persistence.sh."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_uses_strict_mode(self):
        """Should use set -euo pipefail for safety."""
        self.assertIn("set -euo pipefail", self.content)

    def test_defines_persist_label(self):
        self.assertIn("PERSIST_LABEL=", self.content)

    def test_defines_persist_mount(self):
        self.assertIn("PERSIST_MOUNT=", self.content)

    def test_defines_log_file(self):
        self.assertIn("LOG_FILE=", self.content)

    def test_has_log_function(self):
        self.assertRegex(self.content, r"log\(\)\s*\{")

    def test_has_ui_helper_functions(self):
        """Script must have UI helper functions for professional console output."""
        ui_funcs = (
            "ui_header",
            "ui_step",
            "ui_ok",
            "ui_warn",
            "ui_fail",
            "ui_info",
            "ui_done",
            "ui_skip",
        )
        for func in ui_funcs:
            with self.subTest(func=func):
                self.assertRegex(
                    self.content,
                    rf"{func}\(\)\s*\{{",
                    f"Must have {func}() for styled console output",
                )

    def test_has_is_usb_device_function(self):
        self.assertRegex(self.content, r"is_usb_device\(\)\s*\{")

    def test_has_find_iso_device_function(self):
        self.assertRegex(self.content, r"find_iso_device\(\)\s*\{")

    def test_has_setup_persistence_function(self):
        self.assertRegex(self.content, r"setup_persistence\(\)\s*\{")

    def test_overlay_dirs_defined(self):
        self.assertIn("OVERLAY_DIRS=", self.content)

    def test_references_archiso(self):
        """Should check for archiso boot mount point."""
        self.assertIn("/run/archiso", self.content)

    def test_has_is_optical_device_function(self):
        """Should have is_optical_device() to detect DVD/CD media."""
        self.assertRegex(self.content, r"is_optical_device\(\)\s*\{")

    def test_optical_device_checks_sr_pattern(self):
        """is_optical_device should check for /dev/sr* device names."""
        self.assertIn("sr*", self.content)

    def test_optical_device_checks_scsi_type(self):
        """is_optical_device should check SCSI device type 5 (CD-ROM)."""
        self.assertIn('"5"', self.content)

    def test_optical_detection_before_usb_check(self):
        """Optical media detection should happen before USB check in setup_persistence."""
        optical_pos = self.content.find("is_optical_device")
        usb_pos = self.content.find('is_usb_device "$iso_device"')
        self.assertNotEqual(optical_pos, -1, "Must have is_optical_device check")
        self.assertNotEqual(usb_pos, -1, "Must have is_usb_device check")
        self.assertLess(
            optical_pos,
            usb_pos,
            "Optical media detection must occur before USB check in setup_persistence",
        )

    def test_has_strip_partition_function(self):
        """Should have strip_partition() to handle nvme/mmcblk/standard devices."""
        self.assertRegex(self.content, r"strip_partition\(\)\s*\{")

    def test_strip_partition_handles_nvme(self):
        """strip_partition must handle nvme and mmcblk device names correctly.

        Expected behavior:
          /dev/nvme0n1p2  → /dev/nvme0n1  (strips pN suffix)
          /dev/mmcblk0p1  → /dev/mmcblk0  (strips pN suffix)
          /dev/sda1       → /dev/sda      (strips trailing digits)
        """
        # Verify strip_partition uses the correct sed patterns for nvme/mmcblk
        self.assertIn("nvme", self.content)
        self.assertIn("mmcblk", self.content)
        # The function must strip 'p' + digits for nvme/mmcblk
        self.assertRegex(
            self.content,
            r"sed\s+'s/p\[0-9\]\*\$//'",
            "strip_partition must use sed to remove pN suffix for nvme/mmcblk",
        )

    def test_is_usb_device_checks_removable_flag(self):
        """is_usb_device should check sysfs removable flag as fallback."""
        self.assertIn(
            "/removable", self.content, "is_usb_device must check sysfs removable flag"
        )

    def test_find_iso_device_handles_loop_devices(self):
        """find_iso_device should resolve loop devices to backing device."""
        self.assertIn(
            "losetup",
            self.content,
            "find_iso_device must handle loop device resolution",
        )

    def test_find_iso_device_validates_block_device(self):
        """find_iso_device should check that source is a block device."""
        # The -b check ensures we don't process non-block sources
        self.assertIn(
            '-b "$raw_source"',
            self.content,
            "find_iso_device must validate block device with -b",
        )

    def test_setup_persistence_validates_block_device(self):
        """setup_persistence should validate iso_device is a block device."""
        self.assertIn(
            '-b "$iso_device"',
            self.content,
            "setup_persistence must validate device is a block device",
        )

    def test_setup_persistence_waits_for_udev(self):
        """setup_persistence should wait for udev to settle before device detection."""
        udev_pos = self.content.find("udevadm settle")
        self.assertNotEqual(udev_pos, -1, "Must call udevadm settle")
        # The first udevadm settle should come before find_iso_device in setup_persistence
        # Find udevadm settle within the setup_persistence function
        setup_start = self.content.find("setup_persistence()")
        if setup_start != -1:
            setup_content = self.content[setup_start:]
            udev_in_setup = setup_content.find("udevadm settle")
            find_in_setup = setup_content.find("find_iso_device")
            self.assertNotEqual(
                udev_in_setup, -1, "setup_persistence must call udevadm settle"
            )
            self.assertLess(
                udev_in_setup,
                find_in_setup,
                "udevadm settle must run before find_iso_device in setup_persistence",
            )

    def test_setup_persistence_has_debug_logging(self):
        """setup_persistence should log diagnostic info when device detection fails."""
        self.assertIn(
            "Debug:",
            self.content,
            "setup_persistence must include debug logging for diagnostics",
        )

    def test_setup_persistence_has_removable_fallback(self):
        """setup_persistence should proceed if device is removable but not detected as USB."""
        self.assertIn(
            "removable_flag",
            self.content,
            "setup_persistence must check removable flag as USB fallback",
        )

    # ── Device-scoped persistence safety tests ──────────────────────────

    def _get_init_script_content(self):
        """Extract the embedded init script heredoc content."""
        init_start = self.content.find('cat > "$PERSIST_MOUNT/mados-persist-init.sh"')
        self.assertNotEqual(init_start, -1, "Must have embedded init script")
        return self.content[init_start:]

    def test_find_persist_partition_accepts_parent_device(self):
        """find_persist_partition must accept a parent device to scope the search."""
        # Check that the function body uses parent_device
        func_start = self.content.find("find_persist_partition()")
        self.assertNotEqual(func_start, -1, "Must have find_persist_partition function")
        # Search for parent_device within a reasonable range after the function def
        func_region = self.content[func_start : func_start + 1000]
        self.assertIn(
            "parent_device",
            func_region,
            "find_persist_partition must use a parent_device parameter",
        )

    def test_find_persist_partition_uses_lsblk_with_device(self):
        """When given a parent device, find_persist_partition must pass it to lsblk."""
        self.assertIn(
            'lsblk -nlo NAME,LABEL "$parent_device"',
            self.content,
            "find_persist_partition must scope lsblk search to parent device",
        )

    def test_setup_persistence_passes_iso_device_to_find(self):
        """setup_persistence must pass iso_device to find_persist_partition."""
        self.assertIn(
            'find_persist_partition "$iso_device"',
            self.content,
            "setup_persistence must scope partition search to ISO device",
        )

    def test_create_partition_has_safety_check(self):
        """create_persist_partition must verify target matches ISO device."""
        self.assertIn(
            "SAFETY",
            self.content,
            "create_persist_partition must have a SAFETY check",
        )
        # Verify find_iso_device is called within create_persist_partition
        create_start = self.content.find("create_persist_partition()")
        self.assertNotEqual(
            create_start, -1, "Must have create_persist_partition function"
        )
        # Search within a reasonable range for the safety check
        create_region = self.content[create_start : create_start + 500]
        self.assertIn(
            "find_iso_device",
            create_region,
            "create_persist_partition must call find_iso_device for safety check",
        )

    def test_records_boot_device(self):
        """setup_persistence must record boot device in .mados-boot-device."""
        self.assertIn(
            ".mados-boot-device",
            self.content,
            "Must record boot device in .mados-boot-device file",
        )

    def test_init_script_reads_boot_device(self):
        """Embedded init script must read .mados-boot-device for scoped search."""
        init_content = self._get_init_script_content()
        self.assertIn(
            ".mados-boot-device",
            init_content,
            "Init script must read .mados-boot-device for scoped partition search",
        )

    def test_init_script_has_parent_device_scoped_search(self):
        """Embedded init script's find_persist_dev must accept parent device."""
        init_content = self._get_init_script_content()
        self.assertIn(
            "parent_device",
            init_content,
            "Init script's find_persist_dev must use parent_device parameter",
        )

    def test_init_script_has_safety_verification(self):
        """Embedded init script must verify partition belongs to boot device."""
        init_content = self._get_init_script_content()
        self.assertIn(
            "SAFETY",
            init_content,
            "Init script must have SAFETY check verifying partition parent",
        )

    def test_copies_home_contents_on_first_boot(self):
        """setup_persistence must copy /home contents to persistence on first boot."""
        self.assertIn(
            "cp -a /home/.",
            self.content,
            "Must copy current /home contents to persistence partition on first boot",
        )

    def test_checks_directory_structure_before_init(self):
        """setup_persistence must check overlay directory structure to decide
        if initialisation is needed, not just init script existence.

        This handles the case where the partition was created but the
        initialisation was interrupted before directories were set up.
        """
        # Extract setup_persistence function body
        start = self.content.find("setup_persistence()")
        self.assertNotEqual(start, -1, "Must have setup_persistence function")
        setup_fn = self.content[start : start + 8000]

        # Must check for overlay directory existence
        self.assertIn(
            "needs_init",
            setup_fn,
            "Must use needs_init flag based on directory structure check",
        )
        self.assertIn(
            "overlays/$dir/upper",
            setup_fn,
            "Must check for overlay upper directory existence",
        )
        self.assertIn(
            "overlays/$dir/work",
            setup_fn,
            "Must check for overlay work directory existence",
        )

    def test_init_script_seeds_empty_home(self):
        """Embedded init script must seed persistent /home if it's empty."""
        init_content = self._get_init_script_content()
        self.assertIn(
            "cp -a /home/.",
            init_content,
            "Init script must seed persistent /home with current contents if empty",
        )

    def test_embedded_service_blocks_getty(self):
        """Embedded systemd unit must include Before=getty@tty1.service."""
        init_content = self._get_init_script_content()
        self.assertIn(
            "getty@tty1.service",
            init_content,
            "Embedded service unit must block before getty@tty1.service",
        )

    def test_init_script_restarts_iwd_service(self):
        """Embedded init script must restart iwd.service after mounting overlays.

        When the /etc overlay is mounted, network services like iwd that were
        already running need to be restarted to pick up any persistent configuration
        changes.
        """
        init_content = self._get_init_script_content()
        self.assertIn(
            "systemctl restart iwd.service",
            init_content,
            "Init script must restart iwd.service after mounting /etc overlay",
        )
        self.assertIn(
            "systemctl is-active --quiet iwd.service",
            init_content,
            "Init script must check if iwd is active before restarting",
        )

    def test_iwd_restart_has_error_handling(self):
        """iwd restart must have proper error handling and logging."""
        init_content = self._get_init_script_content()
        # Check that restart failure is logged but doesn't fail the script.
        # Matches shell pattern: systemctl restart iwd.service || log WARNING
        self.assertRegex(
            init_content,
            r"systemctl restart iwd\.service.*\|\|.*log.*WARNING",
            "iwd restart must log warning on failure without stopping script",
        )

    def test_get_free_space_has_fallback_blockdev(self):
        """get_free_space() must have blockdev --getsize64 as fallback method."""
        self.assertIn(
            "blockdev --getsize64",
            self.content,
            "get_free_space must use blockdev --getsize64 as fallback",
        )

    def test_get_free_space_has_fallback_isosize(self):
        """get_free_space() must have isosize as fallback method."""
        self.assertIn(
            "isosize",
            self.content,
            "get_free_space must use isosize as fallback",
        )

    def test_get_free_space_proper_default(self):
        """get_free_space() must use ${free:-0} for proper default handling.

        Previously used broken syntax ${free%.*:-0} which doesn't work.
        Now uses ${free%%.*} to strip decimals and ${free:-0} for default.
        """
        # The function should use ${free:-0} for default value handling
        self.assertIn(
            "${free:-0}",
            self.content,
            "get_free_space must use ${free:-0} for proper default value handling",
        )

    def test_setup_checks_ext4_partitions(self):
        """setup_persistence() must scan for ext4 partitions as fallback.

        After checking for labeled persistence partition, script should scan
        for any unlabeled ext4 partitions that could be used.
        """
        # Look for blkid checking TYPE and comparing to ext4
        self.assertIn(
            "blkid -s TYPE",
            self.content,
            "setup_persistence must scan for ext4 partitions using blkid -s TYPE",
        )
        # Verify it checks for ext4 filesystem type
        self.assertIn(
            '"ext4"',
            self.content,
            "setup_persistence must check for ext4 filesystem type",
        )

    def test_ext4_scan_excludes_iso_partition(self):
        """ext4 scan must use find_iso_partition to exclude ISO partition.

        The script should call find_iso_partition and compare against it
        to avoid using the ISO partition as persistence.
        """
        # Check for find_iso_partition call in context of ext4 scanning
        # Find the ext4 scanning section and verify find_iso_partition is used
        ext4_scan_start = self.content.find("scanning for ext4 partitions")
        self.assertNotEqual(ext4_scan_start, -1, "Must have ext4 scanning code")

        # Get the ext4 scanning region (next 500 chars)
        ext4_region = self.content[ext4_scan_start : ext4_scan_start + 500]
        self.assertIn(
            "find_iso_partition",
            ext4_region,
            "ext4 scan must call find_iso_partition to exclude ISO partition",
        )

    def test_ext4_scan_labels_found_partition(self):
        """ext4 scan must use e2label to add persistence label to found partitions.

        When an unlabeled ext4 partition is found, the script should use
        e2label to add the persistence label to it.
        """
        self.assertIn(
            "e2label",
            self.content,
            "ext4 scan must use e2label to label found ext4 partitions",
        )
        # Verify e2label is used with PERSIST_LABEL
        self.assertRegex(
            self.content,
            r"e2label.*\$PERSIST_LABEL",
            "e2label must add the persistence label to found ext4 partitions",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Partition protection safety checks
# ═══════════════════════════════════════════════════════════════════════════
class TestPartitionProtection(unittest.TestCase):
    """Verify create_persist_partition has guards to avoid damaging other partitions."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(self.script_path) as f:
            self.content = f.read()
        # Extract create_persist_partition function body
        start = self.content.find("create_persist_partition()")
        self.assertNotEqual(start, -1)
        # Increased to 24000 to accommodate full function including sfdisk fallback and label verification
        self.create_fn = self.content[start : start + 24000]

    def test_checks_partition_table_type(self):
        """Must detect MBR partition table to enforce 4-partition limit."""
        self.assertIn(
            "Partition Table:",
            self.create_fn,
            "Must read partition table type (MBR/GPT) from parted output",
        )

    def test_enforces_mbr_partition_limit(self):
        """Must refuse to create partition 5+ on MBR (msdos) disks."""
        self.assertIn(
            "msdos",
            self.create_fn,
            "Must check for 'msdos' (MBR) partition table type",
        )
        self.assertRegex(
            self.create_fn,
            r"new_part_num.*-gt\s*4",
            "Must check new_part_num > 4 for MBR",
        )

    def test_partition_number_detection_uses_numeric_sort(self):
        """Must use 'sort -n' to find highest partition number, not rely on parted output order."""
        # This prevents bugs when parted lists partitions out of order (e.g., "2" then "1")
        # Find the section that determines last_part_num - look for the complete assignment
        last_part_pattern = r"last_part_num=\$\(parted[^)]+\)"
        match = re.search(last_part_pattern, self.create_fn, re.MULTILINE)

        self.assertIsNotNone(
            match,
            "Must have a command that sets last_part_num from parted output",
        )
        last_part_cmd = match.group(0)
        self.assertIn(
            "sort -n",
            last_part_cmd,
            "Must use 'sort -n' to numerically sort partition numbers before taking the last one",
        )

    def test_snapshots_partition_boundaries_before_create(self):
        """Must record existing partition boundaries before calling mkpart."""
        self.assertIn(
            "pre_parts",
            self.create_fn,
            "Must snapshot existing partitions before mkpart",
        )
        # Verify that pre_parts uses sort -n to handle out-of-order partition numbers
        pre_parts_pattern = r"pre_parts=\$\(parted[^)]+\)"
        match = re.search(pre_parts_pattern, self.create_fn, re.MULTILINE)
        self.assertIsNotNone(
            match,
            "Must have a command that sets pre_parts from parted output",
        )
        pre_parts_cmd = match.group(0)
        self.assertIn(
            "sort -n",
            pre_parts_cmd,
            "Must use 'sort -n' to ensure consistent partition order in pre_parts snapshot",
        )

    def test_verifies_partition_count_after_create(self):
        """Must verify partition count increased after mkpart."""
        self.assertIn(
            "post_part_count",
            self.create_fn,
            "Must check partition count after mkpart",
        )

    def test_verifies_existing_partitions_unchanged(self):
        """Must verify pre-existing partition boundaries are unchanged after mkpart."""
        self.assertIn(
            "post_pre_parts",
            self.create_fn,
            "Must compare existing partitions after mkpart",
        )
        self.assertIn(
            "Existing partition boundaries changed",
            self.create_fn,
            "Must log error if existing partitions changed",
        )
        # Verify that post_pre_parts uses sort -n to match pre_parts ordering
        post_pre_parts_pattern = r"post_pre_parts=\$\(parted[^)]+\)"
        match = re.search(post_pre_parts_pattern, self.create_fn, re.MULTILINE)
        self.assertIsNotNone(
            match,
            "Must have a command that sets post_pre_parts from parted output",
        )
        post_pre_parts_cmd = match.group(0)
        self.assertIn(
            "sort -n",
            post_pre_parts_cmd,
            "Must use 'sort -n' to ensure consistent partition order matches pre_parts",
        )

    def test_verifies_label_after_format(self):
        """Must verify the ext4 label was written correctly after mkfs."""
        self.assertIn(
            "written_label",
            self.create_fn,
            "Must read back label after mkfs.ext4",
        )
        self.assertIn(
            "Label verification failed",
            self.create_fn,
            "Must log error if label doesn't match",
        )

    def test_mkfs_output_captured_in_variable(self):
        """mkfs.ext4 output must be captured in a variable to prevent stdout leak.

        When create_persist_partition is called via command substitution
        (persist_dev=$(create_persist_partition ...)), any stdout from mkfs.ext4
        would contaminate the return value. The mkfs output must be captured in
        a local variable so only the final echo with the device path goes to stdout.
        """
        self.assertIn(
            "mkfs_output",
            self.create_fn,
            "mkfs.ext4 output must be captured in mkfs_output variable",
        )
        self.assertRegex(
            self.create_fn,
            r"mkfs_output=\$\(mkfs\.ext4",
            "mkfs.ext4 must be called via command substitution into mkfs_output",
        )

    def test_has_sfdisk_fallback(self):
        """create_persist_partition() must have sfdisk --append as partition creation method.

        The function should try sfdisk --append before falling back to the
        complex parted-based approach. This provides a simpler method for
        partition creation on many systems.
        """
        self.assertIn(
            "sfdisk --append",
            self.create_fn,
            "create_persist_partition must use sfdisk --append as primary method",
        )

    def test_sfdisk_checks_mbr_limit(self):
        """sfdisk approach must also check for MBR 4-partition limit.

        Even though sfdisk is used, we must still verify we don't exceed
        the MBR partition limit before attempting to create a partition.
        The check uses device node numbering (not just table entries) to
        account for isohybrid gaps.
        """
        # Find the sfdisk section
        sfdisk_section_start = self.create_fn.find("sfdisk --append")
        self.assertNotEqual(sfdisk_section_start, -1, "Must have sfdisk --append")

        # Look backwards from sfdisk to find MBR check
        # The check should happen before the sfdisk call
        before_sfdisk = self.create_fn[:sfdisk_section_start]

        # Should check new partition number > 4 for msdos tables
        self.assertRegex(
            before_sfdisk,
            r"(existing_count.*-ge\s*4|sfdisk_new_part_num.*-gt\s*4)",
            "sfdisk approach must check partition number limit for MBR",
        )

    def test_sfdisk_aligns_partition(self):
        """sfdisk approach must align partition to 1MB boundary.

        Proper partition alignment is critical for USB performance.
        1MB alignment = 2048 sectors (at 512 bytes/sector).
        """
        # The sfdisk approach should include 2048 for 1MB alignment
        # Look for it in the entire create_persist_partition function
        self.assertIn(
            "2048",
            self.create_fn,
            "sfdisk approach must align to 1MB boundary (2048 sectors)",
        )

    def test_sfdisk_scans_device_nodes_for_gaps(self):
        """create_persist_partition must scan device nodes to detect isohybrid gaps.

        On isohybrid ISOs, device nodes (e.g., /dev/sda1) may exist but not
        be in the partition table. The function must detect these to
        avoid filling gaps and overwriting existing data.
        """
        # Must scan device nodes for highest partition number
        self.assertIn(
            "highest_dev_num",
            self.create_fn,
            "create_persist_partition must scan device nodes for highest partition number",
        )
        # Must compute safe partition number from device nodes
        self.assertIn(
            "sfdisk_new_part_num",
            self.create_fn,
            "create_persist_partition must determine safe new partition number",
        )

    def test_sfdisk_specifies_explicit_partition_number(self):
        """sfdisk must use explicit partition number, not auto-numbering.

        Using 'start=X, type=linux' without a partition number lets sfdisk
        auto-fill gaps. We must use 'N : start=X, type=83' format to
        explicitly set the partition number.
        """
        # Find the first sfdisk --append call (simple approach)
        first_sfdisk = self.create_fn.find("sfdisk --append")
        self.assertNotEqual(first_sfdisk, -1)

        # The sfdisk input should include the partition number variable
        # Look backwards for the sfdisk_input definition
        before_first_sfdisk = self.create_fn[:first_sfdisk]
        self.assertRegex(
            before_first_sfdisk,
            r"sfdisk_input.*sfdisk_new_part_num.*start=",
            "sfdisk must specify explicit partition number in input",
        )


class TestRemovePartitionSafety(unittest.TestCase):
    """Verify remove_persistence verifies label before deleting a partition."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "mados-persistence")
        with open(self.script_path) as f:
            self.content = f.read()
        # Extract remove_persistence function body
        start = self.content.find("remove_persistence()")
        self.assertNotEqual(start, -1)
        self.remove_fn = self.content[start : start + 2000]

    def test_verifies_label_before_remove(self):
        """Must verify partition has the persistence label before deleting."""
        self.assertIn(
            "blkid -s LABEL",
            self.remove_fn,
            "Must check partition label via blkid before removing",
        )

    def test_refuses_wrong_label(self):
        """Must refuse to delete partition if label doesn't match."""
        self.assertIn(
            "Safety check failed",
            self.remove_fn,
            "Must log safety check failure if label mismatches",
        )

    def test_label_check_before_confirmation(self):
        """Label verification must happen before asking user to confirm."""
        label_pos = self.remove_fn.find("blkid -s LABEL")
        confirm_pos = self.remove_fn.find("Type 'yes' to confirm")
        self.assertNotEqual(label_pos, -1, "Must have label check")
        self.assertNotEqual(confirm_pos, -1, "Must have confirmation prompt")
        self.assertLess(
            label_pos,
            confirm_pos,
            "Label verification must happen BEFORE user confirmation prompt",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Persistence service configuration validation
# ═══════════════════════════════════════════════════════════════════════════
class TestPersistenceServiceConfig(unittest.TestCase):
    """Validate mados-persistence.service is correctly configured for boot."""

    def setUp(self):
        self.service_path = os.path.join(
            ETC_DIR, "systemd", "system", "mados-persistence.service"
        )
        if os.path.exists(self.service_path):
            with open(self.service_path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_service_exists(self):
        self.assertTrue(os.path.exists(self.service_path))

    def test_service_has_timeout(self):
        """Service must have TimeoutStartSec to allow partition creation on slow USB."""
        self.assertIn(
            "TimeoutStartSec=",
            self.content,
            "Service needs TimeoutStartSec for slow USB devices",
        )

    def test_service_timeout_sufficient(self):
        """TimeoutStartSec must be at least 120s for partition creation on slow USB."""
        match = re.search(r"TimeoutStartSec=(\d+)", self.content)
        if match is None:
            self.fail("TimeoutStartSec must have a numeric value")
        timeout = int(match.group(1))
        self.assertGreaterEqual(
            timeout,
            120,
            "TimeoutStartSec must be >= 120s to allow "
            "partition creation and formatting on slow USB sticks",
        )

    def test_service_after_udev(self):
        """Service should start after udev to ensure device nodes exist."""
        self.assertIn(
            "systemd-udevd.service",
            self.content,
            "Service must start after systemd-udevd.service",
        )

    def test_service_condition_matches_script_guard(self):
        """Service ConditionPathExists must match script's execution guard.

        The service has ConditionPathExists=/run/archiso and the script
        checks 'if [ -d /run/archiso ]'. These must be consistent.
        """
        self.assertIn("ConditionPathExists=/run/archiso", self.content)
        # Also verify the script uses the same path
        script_path = os.path.join(BIN_DIR, "setup-persistence.sh")
        with open(script_path) as f:
            script = f.read()
        self.assertIn(
            "/run/archiso", script, "Script guard must reference /run/archiso"
        )

    def test_service_quits_plymouth(self):
        """Service must quit Plymouth before running so console output is visible."""
        self.assertIn(
            "plymouth quit",
            self.content,
            "Service must run 'plymouth quit' via ExecStartPre "
            "to exit boot splash before showing progress",
        )

    def test_service_outputs_to_console(self):
        """Service should output to console+journal for visible boot progress."""
        self.assertIn(
            "journal+console",
            self.content,
            "Service must use StandardOutput=journal+console "
            "to show progress on screen after Plymouth exits",
        )

    def test_service_wanted_by_multi_user(self):
        """Service must be wanted by multi-user.target for reliable device detection."""
        self.assertIn("WantedBy=multi-user.target", self.content)

    def test_service_is_enabled(self):
        """Service must have an enable symlink in multi-user.target.wants."""
        symlink = os.path.join(
            ETC_DIR,
            "systemd",
            "system",
            "multi-user.target.wants",
            "mados-persistence.service",
        )
        self.assertTrue(
            os.path.islink(symlink),
            "mados-persistence.service must be enabled in multi-user.target.wants",
        )

    def test_service_after_udev_settle(self):
        """Service should wait for udev to fully settle."""
        self.assertIn(
            "systemd-udev-settle.service",
            self.content,
            "Service must start after systemd-udev-settle.service",
        )

    def test_service_before_getty(self):
        """Service must complete before getty@tty1 to block graphical session."""
        self.assertIn(
            "getty@tty1.service",
            self.content,
            "Service must be Before=getty@tty1.service to block "
            "autologin until persistence is ready",
        )


# ═══════════════════════════════════════════════════════════════════════════
# mados-persistence tool validation
# ═══════════════════════════════════════════════════════════════════════════
class TestMadosPersistenceTool(unittest.TestCase):
    """Validate structure and content of mados-persistence CLI tool."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "mados-persistence")
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_has_check_live_env(self):
        self.assertRegex(self.content, r"check_live_env\(\)\s*\{")

    def test_has_find_persist_partition(self):
        self.assertRegex(self.content, r"find_persist_partition\(\)\s*\{")

    def test_has_show_status(self):
        self.assertRegex(self.content, r"show_status\(\)\s*\{")

    def test_has_enable_persistence(self):
        self.assertRegex(self.content, r"enable_persistence\(\)\s*\{")

    def test_has_disable_persistence(self):
        self.assertRegex(self.content, r"disable_persistence\(\)\s*\{")

    def test_has_remove_persistence(self):
        self.assertRegex(self.content, r"remove_persistence\(\)\s*\{")

    def test_defines_color_codes(self):
        for color in ("RED", "GREEN", "YELLOW", "BLUE", "NC"):
            with self.subTest(color=color):
                self.assertIn(f"{color}=", self.content)

    def test_has_print_helpers(self):
        for func in (
            "print_header",
            "print_status",
            "print_error",
            "print_warning",
            "print_info",
        ):
            with self.subTest(func=func):
                self.assertRegex(self.content, rf"{func}\(\)\s*\{{")

    def test_supports_status_command(self):
        self.assertIn("status", self.content)

    def test_supports_enable_command(self):
        self.assertIn("enable", self.content)

    def test_supports_disable_command(self):
        self.assertIn("disable", self.content)

    def test_supports_remove_command(self):
        self.assertIn("remove", self.content)

    def test_has_find_iso_device_function(self):
        """mados-persistence CLI must have find_iso_device to scope searches."""
        self.assertRegex(
            self.content,
            r"find_iso_device\(\)\s*\{",
            "CLI tool must have find_iso_device() function",
        )

    def test_find_persist_scoped_to_iso_device(self):
        """find_persist_partition must search only the ISO boot device."""
        self.assertIn(
            "find_iso_device",
            self.content,
            "find_persist_partition must use find_iso_device for scoping",
        )
        # Verify it passes iso device to lsblk
        self.assertIn(
            'lsblk -nlo NAME,LABEL "$iso_dev"',
            self.content,
            "find_persist_partition must scope lsblk to the ISO device",
        )

    def test_reads_boot_device_file(self):
        """CLI tool should read .mados-boot-device for boot device fallback."""
        self.assertIn(
            ".mados-boot-device",
            self.content,
            "CLI tool must read .mados-boot-device file",
        )


# ═══════════════════════════════════════════════════════════════════════════
# setup-opencode.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupOpencodeScript(unittest.TestCase):
    """Validate structure of setup-opencode.sh."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-opencode.sh")
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_references_npm(self):
        """Should install opencode via npm."""
        self.assertIn("npm", self.content)

    def test_references_opencode(self):
        self.assertIn("opencode", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# setup-ohmyzsh.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupOhMyZshScript(unittest.TestCase):
    """Validate structure of setup-ohmyzsh.sh."""

    def setUp(self):
        self.script_path = os.path.join(BIN_DIR, "setup-ohmyzsh.sh")
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_references_ohmyzsh(self):
        """Should reference oh-my-zsh repository or install."""
        content_lower = self.content.lower()
        self.assertTrue(
            "oh-my-zsh" in content_lower or "ohmyzsh" in content_lower,
            "setup-ohmyzsh.sh should reference oh-my-zsh",
        )

    def test_references_skel(self):
        """Should install to /etc/skel for new users."""
        self.assertIn("/etc/skel", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# Systemd service files validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSystemdServiceFiles(unittest.TestCase):
    """Validate systemd service files are properly structured."""

    def _get_service_files(self):
        service_dir = os.path.join(ETC_DIR, "systemd", "system")
        if not os.path.isdir(service_dir):
            return []
        services = []
        for fname in os.listdir(service_dir):
            fpath = os.path.join(service_dir, fname)
            # Skip symlinks (they point to system paths not in the repo)
            if (
                fname.endswith(".service")
                and os.path.isfile(fpath)
                and not os.path.islink(fpath)
            ):
                services.append(fpath)
        return services

    def test_service_files_exist(self):
        """At least one systemd service should be defined."""
        services = self._get_service_files()
        self.assertGreater(len(services), 0)

    def test_service_files_have_unit_section(self):
        for svc in self._get_service_files():
            with self.subTest(service=os.path.basename(svc)):
                with open(svc) as f:
                    content = f.read()
                self.assertIn(
                    "[Unit]", content, f"{os.path.basename(svc)} missing [Unit] section"
                )

    def test_service_files_have_service_section(self):
        for svc in self._get_service_files():
            with self.subTest(service=os.path.basename(svc)):
                with open(svc) as f:
                    content = f.read()
                # Timer units won't have [Service], but .service files should
                if svc.endswith(".service"):
                    self.assertIn(
                        "[Service]",
                        content,
                        f"{os.path.basename(svc)} missing [Service] section",
                    )

    def test_service_files_have_description(self):
        for svc in self._get_service_files():
            with self.subTest(service=os.path.basename(svc)):
                with open(svc) as f:
                    content = f.read()
                self.assertRegex(
                    content,
                    r"Description=.+",
                    f"{os.path.basename(svc)} missing Description",
                )


# ═══════════════════════════════════════════════════════════════════════════
# iwd service drop-in configuration
# ═══════════════════════════════════════════════════════════════════════════
class TestIwdServiceDropIn(unittest.TestCase):
    """Validate iwd.service drop-in configuration for persistence."""

    def setUp(self):
        self.dropin_dir = os.path.join(ETC_DIR, "systemd", "system", "iwd.service.d")
        self.dropin_file = os.path.join(self.dropin_dir, "99-after-persistence.conf")
        if os.path.exists(self.dropin_file):
            with open(self.dropin_file) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_dropin_directory_exists(self):
        """iwd.service.d directory must exist for drop-in configurations."""
        self.assertTrue(
            os.path.isdir(self.dropin_dir), "iwd.service.d directory must exist"
        )

    def test_dropin_file_exists(self):
        """Drop-in configuration file must exist."""
        self.assertTrue(
            os.path.exists(self.dropin_file), "99-after-persistence.conf must exist"
        )

    def test_dropin_has_unit_section(self):
        """Drop-in must have [Unit] section."""
        self.assertIn("[Unit]", self.content)

    def test_dropin_waits_for_persistence(self):
        """Drop-in must ensure iwd starts after persistence service."""
        self.assertIn(
            "After=mados-persistence.service",
            self.content,
            "iwd must start after persistence overlays are mounted",
        )

    def test_dropin_only_applies_in_live_environment(self):
        """Drop-in must only apply in live archiso environment."""
        self.assertIn(
            "ConditionPathExists=/run/archiso",
            self.content,
            "Drop-in should only apply in live environment",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Welcome script validation
# ═══════════════════════════════════════════════════════════════════════════
class TestWelcomeScript(unittest.TestCase):
    """Validate mados-welcome.sh profile script."""

    def setUp(self):
        self.script_path = os.path.join(ETC_DIR, "profile.d", "mados-welcome.sh")
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_has_shebang_or_comment(self):
        first_line = self.content.split("\n")[0] if self.content else ""
        self.assertTrue(
            first_line.startswith("#"),
            "Welcome script should start with a comment or shebang",
        )

    def test_valid_bash_syntax(self):
        if not os.path.exists(self.script_path):
            self.skipTest("Script not found")
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error:\n{result.stderr}")


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestProfileDef(unittest.TestCase):
    """Validate profiledef.sh archiso configuration."""

    def setUp(self):
        self.script_path = os.path.join(REPO_DIR, "profiledef.sh")
        with open(self.script_path) as f:
            self.content = f.read()

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_valid_bash_syntax(self):
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error:\n{result.stderr}")

    def test_defines_iso_name(self):
        self.assertRegex(self.content, r"iso_name=")

    def test_defines_iso_publisher(self):
        self.assertRegex(self.content, r"iso_publisher=")

    def test_defines_file_permissions(self):
        self.assertIn("file_permissions", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# packages.x86_64 validation
# ═══════════════════════════════════════════════════════════════════════════
class TestPackagesFile(unittest.TestCase):
    """Validate packages.x86_64 ISO package list."""

    def setUp(self):
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            self.lines = f.readlines()
        self.packages = [
            line.strip()
            for line in self.lines
            if line.strip() and not line.strip().startswith("#")
        ]

    def test_not_empty(self):
        self.assertGreater(len(self.packages), 0)

    def test_no_duplicate_packages(self):
        seen = set()
        for pkg in self.packages:
            self.assertNotIn(pkg, seen, f"Duplicate package: {pkg}")
            seen.add(pkg)

    def test_essential_packages(self):
        """Live ISO should include core packages."""
        essential = [
            "base",
            "linux",
            "linux-firmware",
            "grub",
            "networkmanager",
            "python",
        ]
        for pkg in essential:
            with self.subTest(package=pkg):
                self.assertIn(pkg, self.packages)

    def test_valid_package_names(self):
        pattern = re.compile(r"^[a-z0-9][a-z0-9._+-]*$")
        for pkg in self.packages:
            with self.subTest(package=pkg):
                self.assertRegex(pkg, pattern)

    def test_no_trailing_whitespace(self):
        for i, line in enumerate(self.lines, 1):
            if line.strip():
                with self.subTest(line=i):
                    self.assertEqual(
                        line.rstrip("\n"),
                        line.rstrip(),
                        f"Line {i} has trailing whitespace",
                    )


# ═══════════════════════════════════════════════════════════════════════════
# mados-media-helper.sh validation
# ═══════════════════════════════════════════════════════════════════════════
class TestMediaHelperScript(unittest.TestCase):
    """Validate structure and content of mados-media-helper.sh."""

    def setUp(self):
        self.script_path = os.path.join(
            AIROOTFS, "usr", "local", "lib", "mados-media-helper.sh"
        )
        if os.path.exists(self.script_path):
            with open(self.script_path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.script_path))

    def test_valid_bash_syntax(self):
        """Should pass bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", self.script_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Syntax error in mados-media-helper.sh:\n{result.stderr}",
        )

    def test_has_is_optical_media_function(self):
        """Should have is_optical_media() function."""
        self.assertRegex(self.content, r"is_optical_media\(\)\s*\{")

    def test_has_has_persistence_function(self):
        """Should have has_persistence() function."""
        self.assertRegex(self.content, r"has_persistence\(\)\s*\{")

    def test_has_can_install_software_function(self):
        """Should have can_install_software() function."""
        self.assertRegex(self.content, r"can_install_software\(\)\s*\{")

    def test_optical_media_checks_sr_devices(self):
        """is_optical_media should detect /dev/sr* devices."""
        self.assertIn("/dev/sr", self.content)

    def test_optical_media_checks_scsi_type(self):
        """is_optical_media should check SCSI type 5 (CD-ROM)."""
        self.assertIn('"5"', self.content)

    def test_optical_media_checks_udevadm(self):
        """is_optical_media should check ID_CDROM via udevadm."""
        self.assertIn("ID_CDROM", self.content)

    def test_can_install_checks_persistence(self):
        """can_install_software should check has_persistence."""
        self.assertIn("has_persistence", self.content)

    def test_can_install_checks_optical(self):
        """can_install_software should check is_optical_media."""
        self.assertIn("is_optical_media", self.content)

    def test_allows_install_outside_live_env(self):
        """can_install_software should allow installs outside live environment."""
        self.assertIn("/run/archiso", self.content)


# ═══════════════════════════════════════════════════════════════════════════
# Setup scripts DVD/CD detection validation
# ═══════════════════════════════════════════════════════════════════════════
class TestSetupScriptsDvdDetection(unittest.TestCase):
    """Validate that setup scripts check for optical media before installing."""

    SETUP_SCRIPTS = [
        "setup-opencode.sh",
        "setup-ollama.sh",
        "setup-ohmyzsh.sh",
    ]

    def _read_script(self, name):
        path = os.path.join(BIN_DIR, name)
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ""

    def test_scripts_source_media_helper(self):
        """Setup scripts should source mados-media-helper.sh."""
        for script in self.SETUP_SCRIPTS:
            with self.subTest(script=script):
                content = self._read_script(script)
                self.assertIn(
                    "mados-media-helper.sh",
                    content,
                    f"{script} must reference mados-media-helper.sh",
                )

    def test_scripts_check_can_install_software(self):
        """Setup scripts should call can_install_software before installing."""
        for script in self.SETUP_SCRIPTS:
            with self.subTest(script=script):
                content = self._read_script(script)
                self.assertIn(
                    "can_install_software",
                    content,
                    f"{script} must check can_install_software",
                )

    def test_scripts_exit_zero_on_dvd(self):
        """Setup scripts should exit 0 (not fail) when on DVD."""
        for script in self.SETUP_SCRIPTS:
            with self.subTest(script=script):
                content = self._read_script(script)
                # The DVD check block should end with exit 0
                self.assertIn(
                    "exit 0",
                    content,
                    f"{script} must exit 0 when skipping DVD install",
                )

    def test_dvd_check_before_install(self):
        """DVD media check must happen before any install attempt."""
        for script in self.SETUP_SCRIPTS:
            with self.subTest(script=script):
                content = self._read_script(script)
                dvd_pos = content.find("can_install_software")
                install_pos = content.find("curl")
                if install_pos == -1:
                    install_pos = content.find("git clone")
                self.assertNotEqual(
                    dvd_pos, -1, f"{script} must check can_install_software"
                )
                self.assertNotEqual(
                    install_pos, -1, f"{script} must have install logic"
                )
                self.assertLess(
                    dvd_pos,
                    install_pos,
                    f"{script}: DVD check must come before install attempt",
                )


# ═══════════════════════════════════════════════════════════════════════════
# profiledef.sh media helper permissions
# ═══════════════════════════════════════════════════════════════════════════
class TestProfiledefMediaHelperPermissions(unittest.TestCase):
    """Validate profiledef.sh includes permissions for mados-media-helper.sh."""

    def setUp(self):
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            self.content = f.read()

    def test_media_helper_has_permissions(self):
        """profiledef.sh should set permissions for mados-media-helper.sh."""
        self.assertIn(
            "mados-media-helper.sh",
            self.content,
            "profiledef.sh must include permissions for mados-media-helper.sh",
        )

    def test_media_helper_executable(self):
        """mados-media-helper.sh should have executable permissions."""
        pattern = re.compile(r'\["/usr/local/lib/mados-media-helper\.sh"\]="0:0:755"')
        self.assertRegex(
            self.content,
            pattern,
            "mados-media-helper.sh must have 0:0:755 permissions",
        )


if __name__ == "__main__":
    unittest.main()
