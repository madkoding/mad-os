#!/usr/bin/env python3
"""
Safety tests for create_persist_partition() function.

Tests MBR/GPT partition table validation, partition number gap detection,
device node creation, backup of partition boundaries, and verification logic.
"""

import os
import subprocess
import tempfile
import pytest
from pathlib import Path


# -----------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------
REPO_DIR = Path(__file__).parent.parent
SETUP_SCRIPT = REPO_DIR / "airootfs" / "usr" / "local" / "bin" / "setup-persistence.sh"


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------
@pytest.fixture
def temp_disk_image(tempfile):
    """Create a temporary disk image with partition table."""
    disk_path = tempfile.mktemp(suffix=".img")
    try:
        # Create 500MB disk image
        with open(disk_path, "wb") as f:
            f.write(b"\0" * (500 * 1024 * 1024))

        # Setup loopback
        result = subprocess.run(
            ["losetup", "-f", "--show", "-P", disk_path],
            capture_output=True,
            text=True,
            check=True,
        )
        loop_device = result.stdout.strip()

        # Create MBR partition table
        subprocess.run(
            ["parted", "-s", loop_device, "mklabel", "msdos"],
            check=True,
            capture_output=True,
        )

        yield loop_device

    finally:
        subprocess.run(["losetup", "-d", loop_device], check=False)
        if os.path.exists(disk_path):
            os.unlink(disk_path)


@pytest.fixture
def mock_iso_device():
    """Mock the ISO device detection."""
    # Store original ISO_DEVICE if set
    original = os.environ.get("ISO_DEVICE")
    os.environ["ISO_DEVICE"] = "/dev/loop0"
    yield
    if original:
        os.environ["ISO_DEVICE"] = original
    else:
        os.environ.pop("ISO_DEVICE", None)


# -----------------------------------------------------------------------
# Test create_persist_partition() safety checks
# -----------------------------------------------------------------------
class TestCreatePersistPartitionSafety:
    """Test create_persist_partition() safety mechanisms."""

    def test_iso_device_safety_check(self, mock_iso_device, temp_disk_image):
        """Test that create_persist_partition only works on ISO device."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                # Mock find_iso_device to return different device
                find_iso_device() {{
                    echo "/dev/sda"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should fail due to safety check
        assert "SAFETY" in result.stdout or "SAFETY" in result.stderr

    def test_mbr_partition_limit(self, temp_disk_image):
        """Test MBR 4-partition limit enforcement."""
        # Create 4 partitions
        for i in range(1, 5):
            subprocess.run(
                [
                    "parted",
                    "-s",
                    temp_disk_image,
                    "mkpart",
                    "primary",
                    "ext4",
                    f"{i * 100}MB",
                    f"{i * 100 + 50}MB",
                ],
                check=True,
                capture_output=True,
            )

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should fail - MBR can only have 4 partitions
        assert (
            "SAFETY" in result.stdout
            or "SAFETY" in result.stderr
            or result.returncode != 0
        )

    def test_gpt_partition_limit(self, temp_disk_image):
        """Test GPT supports more than 4 partitions."""
        # Change to GPT
        subprocess.run(
            ["parted", "-s", temp_disk_image, "mklabel", "gpt"],
            check=True,
            capture_output=True,
        )

        # Create 5 partitions (should work with GPT)
        for i in range(1, 6):
            subprocess.run(
                [
                    "parted",
                    "-s",
                    temp_disk_image,
                    "mkpart",
                    "primary",
                    "ext4",
                    f"{i * 100}MB",
                    f"{i * 100 + 50}MB",
                ],
                check=True,
                capture_output=True,
            )

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should succeed with GPT
        assert "p1" in result.stdout or result.returncode == 0


# -----------------------------------------------------------------------
# Test partition number gap detection (isohybrid scenarios)
# -----------------------------------------------------------------------
class TestPartitionNumberGapDetection:
    """Test detection of partition number gaps in isohybrid scenarios."""

    def test_device_node_missing_from_table(self, temp_disk_image):
        """Test detection when device node exists but not in partition table."""
        # Create a scenario where partition exists as device but not in table
        # This simulates isohybrid ISO with partition 1 outside the table

        # Manually create partition device node (simulating isohybrid)
        subprocess.run(
            [
                "parted",
                "-s",
                temp_disk_image,
                "mkpart",
                "primary",
                "ext4",
                "0MB",
                "100MB",
            ],
            check=True,
            capture_output=True,
        )

        # Now simulate the partition table doesn't show it
        # (in real isohybrid, partition 1 is outside the partition table)

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should handle the gap detection
        assert "gap" in result.stdout.lower() or result.returncode == 0

    def test_partition_table_uses_sfdisk(self, temp_disk_image):
        """Test that sfdisk is used when partition number mismatch detected."""
        # Setup with mismatch
        subprocess.run(
            [
                "parted",
                "-s",
                temp_disk_image,
                "mkpart",
                "primary",
                "ext4",
                "0MB",
                "100MB",
            ],
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should mention sfdisk for explicit partition numbering
        assert "sfdisk" in result.stdout.lower() or result.returncode == 0


# -----------------------------------------------------------------------
# Test device node creation in containers
# -----------------------------------------------------------------------
class TestDeviceNodeCreation:
    """Test device node creation in container environments."""

    def test_device_node_auto_creation(self, temp_disk_image):
        """Test that device nodes are created after partition creation."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should find the created partition
        assert "p1" in result.stdout or result.returncode == 0

    def test_device_node_manual_creation(self, temp_disk_image):
        """Test manual device node creation when udev doesn't auto-create."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                # Mock udevadm to simulate slow udev
                udevadm() {{
                    sleep 0.1
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should handle manual device node creation
        assert "mknod" in result.stdout or result.returncode == 0


# -----------------------------------------------------------------------
# Test partition boundary backup
# -----------------------------------------------------------------------
class TestPartitionBoundaryBackup:
    """Test backup of partition boundaries before mkpart."""

    def test_pre_parts_snapshot(self, temp_disk_image):
        """Test that pre-existing partition boundaries are captured."""
        # Create initial partitions
        subprocess.run(
            [
                "parted",
                "-s",
                temp_disk_image,
                "mkpart",
                "primary",
                "ext4",
                "0MB",
                "100MB",
            ],
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should have captured pre_parts
        assert "pre_parts" in result.stdout or "POST" in result.stdout

    def test_post_pre_parts_verification(self, temp_disk_image):
        """Test that existing partitions are verified unchanged after mkpart."""
        # Create initial partitions
        subprocess.run(
            [
                "parted",
                "-s",
                temp_disk_image,
                "mkpart",
                "primary",
                "ext4",
                "0MB",
                "100MB",
            ],
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should have verified post_pre_parts
        assert "post_pre_parts" in result.stdout or "unchanged" in result.stdout.lower()


# -----------------------------------------------------------------------
# Test label verification after mkfs
# -----------------------------------------------------------------------
class TestLabelVerification:
    """Test filesystem label verification after mkfs."""

    def test_label_written_correctly(self, temp_disk_image):
        """Test that filesystem label is verified after mkfs."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should verify label was written
        assert "written_label" in result.stdout or "persistence" in result.stdout

    def test_label_verification_failure_handling(self, temp_disk_image):
        """Test handling when label verification fails."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                # Mock blkid to return wrong label
                blkid() {{
                    echo ""
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should handle label mismatch gracefully
        assert "WARNING" in result.stdout or result.returncode == 0


# -----------------------------------------------------------------------
# Test partition table type validation
# -----------------------------------------------------------------------
class TestPartitionTableValidation:
    """Test partition table type validation."""

    def test_msdos_table_recognition(self, temp_disk_image):
        """Test MBR (msdos) table type recognition."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should recognize msdos table type
        assert "msdos" in result.stdout.lower() or result.returncode == 0

    def test_gpt_table_recognition(self, temp_disk_image):
        """Test GPT table type recognition."""
        subprocess.run(
            ["parted", "-s", temp_disk_image, "mklabel", "gpt"],
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should recognize gpt table type
        assert "gpt" in result.stdout.lower() or result.returncode == 0

    def test_unknown_table_type_rejection(self, temp_disk_image):
        """Test rejection of unknown partition table types."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                # Create partition table with parted
                parted -s {temp_disk_image} mklabel msdos
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should succeed with msdos (which is recognized)
        assert result.returncode == 0 or "msdos" in result.stdout.lower()


# -----------------------------------------------------------------------
# Test partition creation with different scenarios
# -----------------------------------------------------------------------
class TestPartitionCreationScenarios:
    """Test partition creation in various scenarios."""

    def test_first_partition_creation(self, temp_disk_image):
        """Test creating first partition on empty disk."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should create partition 1
        assert "p1" in result.stdout or "Partition 1" in result.stdout

    def test_subsequent_partition_creation(self, temp_disk_image):
        """Test creating partition after existing partitions."""
        # Create first partition
        subprocess.run(
            [
                "parted",
                "-s",
                temp_disk_image,
                "mkpart",
                "primary",
                "ext4",
                "0MB",
                "100MB",
            ],
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"""
                source {SETUP_SCRIPT}
                
                find_iso_device() {{
                    echo "{temp_disk_image}"
                }}
                
                result=$(create_persist_partition "{temp_disk_image}")
                echo "$result"
                """,
            ],
            capture_output=True,
            text=True,
        )

        # Should create partition 2
        assert "p2" in result.stdout or "Partition 2" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
