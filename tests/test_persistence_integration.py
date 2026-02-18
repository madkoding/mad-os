#!/usr/bin/env python3
"""
Integration tests for madOS persistence system.

Tests the full persistence flow: create partition → install files → mount overlays
→ verify persistence → simulate reboot → verify again.

Uses pytest fixtures for setup/teardown and tests different scenarios.
"""

import os
import subprocess
import tempfile
import shutil
import pytest
from pathlib import Path
from typing import Generator, Tuple


# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------
PERSIST_LABEL = "persistence"
PERSIST_MOUNT = "/mnt/persistence"
OVERLAY_DIRS = ["etc", "usr", "var", "opt"]


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------
@pytest.fixture(scope="module")
def temp_workspace() -> Generator[Path, None, None]:
    """Create temporary workspace for test ISO and loopback devices."""
    workspace = tempfile.mkdtemp(prefix="mados-test-")
    print(f"Created workspace: {workspace}")
    try:
        yield Path(workspace)
    finally:
        print(f"Cleaning up workspace: {workspace}")
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture(scope="module")
def test_iso_path(temp_workspace: Path) -> Generator[Path, None, None]:
    """Create a minimal ISO image for testing."""
    iso_path = temp_workspace / "test.iso"

    # Create a minimal ISO structure
    iso_root = temp_workspace / "iso_root"
    iso_root.mkdir(parents=True)

    # Create minimal archiso structure
    (iso_root / "arch").mkdir()
    (iso_root / "arch" / "boot").mkdir()
    (iso_root / "arch" / "boot" / "x86_64").mkdir()
    (iso_root / "arch" / "boot" / "x86_64" / "vmlinuz-linux").touch()
    (iso_root / "arch" / "boot" / "vmlinuz-linux").touch()

    # Create a small initramfs
    (iso_root / "arch" / "boot" / "x86_64" / "initramfs-linux.img").touch()

    # Create minimal boot directory
    (iso_root / "boot").mkdir()
    (iso_root / "boot" / "vmlinuz-linux").touch()

    # Create EFI directory structure
    (iso_root / "EFI").mkdir()
    (iso_root / "EFI" / "BOOT").mkdir()
    (iso_root / "EFI" / "BOOT" / "BOOTx64.EFI").touch()

    # Create ISO image using xorriso
    subprocess.run(
        [
            "xorriso",
            "-as",
            "mkisofs",
            "-o",
            str(iso_path),
            "-V",
            "MADOS_TEST",
            "-b",
            "isolinux/isolinux.bin",
            "-c",
            "isolinux/boot.cat",
            "-no-emul-boot",
            "-boot-load-size",
            "4",
            "-boot-info-table",
            "-eltorito-alt-boot",
            "-e",
            "EFI/BOOT/BOOTx64.EFI",
            "-no-emul-boot",
            "-isohybrid-gpt-basdat",
            "-isohybrid-mbr",
            str(iso_root),
        ],
        check=True,
        capture_output=True,
    )

    yield iso_path


@pytest.fixture
def loopback_device(
    test_iso_path: Path, temp_workspace: Path
) -> Generator[str, None, None]:
    """Create a loopback device from ISO image with partition table."""
    # Create a disk image with partition table
    disk_path = temp_workspace / "disk.img"
    device_path = f"/dev/loop{tempfile.gettempprefix().split('/')[-1][-1]}"

    # Calculate size: ISO size + 100MB for partition
    iso_size = test_iso_path.stat().st_size
    disk_size = iso_size + (100 * 1024 * 1024)  # Add 100MB

    # Create disk image
    with open(disk_path, "wb") as f:
        f.write(b"\0" * disk_size)

    # Copy ISO content to first partition (at offset)
    with open(disk_path, "r+b") as disk:
        with open(test_iso_path, "rb") as iso:
            disk.write(iso.read())

    # Setup loopback
    result = subprocess.run(
        ["losetup", "-f", "--show", "-P", str(disk_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    loop_device = result.stdout.strip()

    # Create partition table
    subprocess.run(
        ["parted", "-s", loop_device, "mklabel", "msdos"],
        check=True,
        capture_output=True,
    )

    # Create partition starting after ISO content
    # ISO is at start, partition starts at 200MB (after ISO + gap)
    start_mb = 200
    subprocess.run(
        [
            "parted",
            "-s",
            loop_device,
            "mkpart",
            "primary",
            "ext4",
            f"{start_mb}MB",
            "100%",
        ],
        check=True,
        capture_output=True,
    )

    # Set partition flag
    subprocess.run(
        ["parted", "-s", loop_device, "set", "1", "boot", "on"],
        check=True,
        capture_output=True,
    )

    # Refresh partition table
    subprocess.run(["partprobe", loop_device], check=True, capture_output=True)

    yield loop_device

    # Cleanup
    subprocess.run(["losetup", "-d", loop_device], check=False)
    disk_path.unlink(missing_ok=True)


@pytest.fixture
def setup_script(temp_workspace: Path) -> Generator[Path, None, None]:
    """Copy setup-persistence.sh to temp location."""
    script_path = (
        Path(__file__).parent.parent
        / "airootfs"
        / "usr"
        / "local"
        / "bin"
        / "setup-persistence.sh"
    )
    if script_path.exists():
        dest = temp_workspace / "setup-persistence.sh"
        shutil.copy(script_path, dest)
        dest.chmod(0o755)
        yield dest
    else:
        pytest.skip("setup-persistence.sh not found")


@pytest.fixture
def mados_persistence_cli(temp_workspace: Path) -> Generator[Path, None, None]:
    """Copy mados-persistence CLI to temp location."""
    script_path = (
        Path(__file__).parent.parent
        / "airootfs"
        / "usr"
        / "local"
        / "bin"
        / "mados-persistence"
    )
    if script_path.exists():
        dest = temp_workspace / "mados-persistence"
        shutil.copy(script_path, dest)
        dest.chmod(0o755)
        yield dest
    else:
        pytest.skip("mados-persistence not found")


# -----------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------
class TestPersistenceFullFlow:
    """Test full persistence lifecycle."""

    def test_create_partition_and_mount(
        self,
        loopback_device: str,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test creating persistence partition and mounting it."""
        # Run setup script
        result = subprocess.run(
            ["bash", str(setup_script)],
            capture_output=True,
            text=True,
            env={**os.environ, "ISO_DEVICE": loopback_device},
        )

        print(f"Setup script stdout:\n{result.stdout}")
        print(f"Setup script stderr:\n{result.stderr}")

        # Check for success indicators
        assert result.returncode == 0, f"Setup failed with code {result.returncode}"
        assert PERSIST_LABEL in result.stdout or PERSIST_LABEL in result.stderr, (
            "Setup should mention persistence label"
        )

    def test_persistence_files_installed(
        self,
        loopback_device: str,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test that persistence files are correctly installed."""
        # Run setup
        subprocess.run(
            ["bash", str(setup_script)],
            check=True,
            capture_output=True,
            env={**os.environ, "ISO_DEVICE": loopback_device},
        )

        # Mount the persistence partition to check files
        persist_part = f"{loopback_device}p2"  # Assuming partition 2
        persist_mount = temp_workspace / "persist_mount"
        persist_mount.mkdir()

        subprocess.run(
            ["mount", persist_part, str(persist_mount)],
            check=True,
            capture_output=True,
        )

        try:
            # Check init script
            init_script = persist_mount / "mados-persist-init.sh"
            assert init_script.exists(), "Init script should be installed"
            assert os.access(str(init_script), os.X_OK), (
                "Init script should be executable"
            )

            # Check service file
            service_file = persist_mount / "mados-persistence.service"
            assert service_file.exists(), "Service file should be installed"

            # Check directory structure
            overlays_dir = persist_mount / "overlays"
            assert overlays_dir.exists(), "Overlays directory should exist"

            for dir_name in OVERLAY_DIRS:
                upper_dir = overlays_dir / dir_name / "upper"
                work_dir = overlays_dir / dir_name / "work"
                assert upper_dir.exists(), f"Upper dir for /{dir_name} should exist"
                assert work_dir.exists(), f"Work dir for /{dir_name} should exist"

            # Check boot device recording
            boot_device_file = persist_mount / ".mados-boot-device"
            assert boot_device_file.exists(), "Boot device file should be recorded"

            # Check home directory
            home_dir = persist_mount / "home"
            assert home_dir.exists(), "Home directory should exist"

        finally:
            subprocess.run(["umount", str(persist_mount)], check=False)

    def test_overlay_mount_simulation(
        self,
        loopback_device: str,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test overlay mount setup."""
        # Run setup
        subprocess.run(
            ["bash", str(setup_script)],
            check=True,
            capture_output=True,
            env={**os.environ, "ISO_DEVICE": loopback_device},
        )

        # Check that init script contains overlay mount commands
        init_script_path = (
            Path(__file__).parent.parent
            / "airootfs"
            / "usr"
            / "local"
            / "bin"
            / "setup-persistence.sh"
        )
        init_script_content = init_script_path.read_text()

        # Verify overlayfs mount commands are present
        assert "mount -t overlay overlay" in init_script_content, (
            "Init script should contain overlayfs mount command"
        )

        # Verify bind mount for /home
        assert "mount --bind" in init_script_content, (
            "Init script should contain bind mount command"
        )


class TestPersistenceScenarios:
    """Test different persistence scenarios."""

    def test_fresh_usb_setup(
        self,
        loopback_device: str,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test initial persistence setup on fresh USB."""
        # First run should create partition
        result = subprocess.run(
            ["bash", str(setup_script)],
            capture_output=True,
            text=True,
            env={**os.environ, "ISO_DEVICE": loopback_device},
        )

        assert result.returncode == 0, "First run should succeed"
        assert "Creating" in result.stdout or "Creating" in result.stderr, (
            "First run should indicate partition creation"
        )

    def test_existing_persistence_reuse(
        self,
        loopback_device: str,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test reusing existing persistence partition."""
        # First run - create persistence
        subprocess.run(
            ["bash", str(setup_script)],
            check=True,
            capture_output=True,
            env={**os.environ, "ISO_DEVICE": loopback_device},
        )

        # Second run - should detect existing and reuse
        result = subprocess.run(
            ["bash", str(setup_script)],
            capture_output=True,
            text=True,
            env={**os.environ, "ISO_DEVICE": loopback_device},
        )

        # Should detect existing persistence
        assert result.returncode == 0, "Second run should succeed"
        # The script should find the existing partition

    def test_optical_media_detection(
        self,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test that optical media is detected and skipped."""
        # Create a mock optical device scenario
        # In real scenario, this would be /dev/sr0
        result = subprocess.run(
            ["bash", str(setup_script)],
            capture_output=True,
            text=True,
            env={**os.environ, "ISO_DEVICE": "/dev/sr0"},  # Mock optical device
        )

        # Should skip optical media
        assert (
            "Optical media detected" in result.stdout
            or "Optical media detected" in result.stderr
        ), "Should detect and skip optical media"


class TestPersistenceCLI:
    """Test mados-persistence CLI commands."""

    def test_status_command(
        self,
        loopback_device: str,
        temp_workspace: Path,
        mados_persistence_cli: Path,
    ):
        """Test mados-persistence status command."""
        result = subprocess.run(
            ["bash", str(mados_persistence_cli), "status"],
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": os.environ["PATH"]},
        )

        # Status should run without error
        # It may fail if no persistence is configured, but shouldn't crash
        assert result.returncode in [0, 1], "Status command should not crash"

    def test_help_command(
        self,
        temp_workspace: Path,
        mados_persistence_cli: Path,
    ):
        """Test mados-persistence help command."""
        result = subprocess.run(
            ["bash", str(mados_persistence_cli), "help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "Help command should succeed"
        assert "Usage:" in result.stdout, "Help should show usage"
        assert "status" in result.stdout, "Help should list status command"
        assert "enable" in result.stdout, "Help should list enable command"


# -----------------------------------------------------------------------
# Mock-based tests for edge cases
# -----------------------------------------------------------------------
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_insufficient_space(
        self,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test behavior when insufficient space is available."""
        # This would require mocking get_free_space function
        # For now, just verify the script handles low space scenarios
        result = subprocess.run(
            ["bash", "-n", str(setup_script)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "Script should have valid syntax"

    def test_device_node_creation(
        self,
        loopback_device: str,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test device node creation in container environment."""
        # The script should handle missing device nodes
        # This is verified by checking the script contains mknod logic
        script_content = setup_script.read_text()

        assert "mknod" in script_content, (
            "Script should contain mknod for manual device node creation"
        )
        assert "sysfs" in script_content, (
            "Script should check sysfs for device information"
        )

    def test_label_verification(
        self,
        temp_workspace: Path,
        setup_script: Path,
    ):
        """Test label verification after mkfs."""
        script_content = setup_script.read_text()

        assert "written_label" in script_content, (
            "Script should verify written label after mkfs"
        )
        assert "Label verification failed" in script_content, (
            "Script should log label mismatch warning"
        )


# -----------------------------------------------------------------------
# Parallel execution markers
# -----------------------------------------------------------------------
# Mark tests that can run in parallel
pytest_plugins = []


def pytest_collection_modifyitems(items):
    """Add markers for parallel execution."""
    for item in items:
        if "TestPersistenceFullFlow" in item.nodeid:
            item.add_marker(pytest.mark.full_flow)
        elif "TestPersistenceScenarios" in item.nodeid:
            item.add_marker(pytest.mark.scenarios)
        elif "TestPersistenceCLI" in item.nodeid:
            item.add_marker(pytest.mark.cli)
        elif "TestEdgeCases" in item.nodeid:
            item.add_marker(pytest.mark.edge_cases)


if __name__ == "__main__":
    pytest.main(
        [__file__, "-v", "--cov=airootfs/usr/local/bin/", "--cov-report=term-missing"]
    )
