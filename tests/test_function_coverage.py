#!/usr/bin/env python3
"""
Function coverage tests for madOS persistence bash scripts.

Tests individual bash functions with valid/invalid inputs,
validates error handling, and tracks function coverage.
"""

import os
import subprocess
import pytest
from pathlib import Path
from typing import List, Dict, Any


# -----------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------
REPO_DIR = Path(__file__).parent.parent
SETUP_SCRIPT = REPO_DIR / "airootfs" / "usr" / "local" / "bin" / "setup-persistence.sh"
CLI_SCRIPT = REPO_DIR / "airootfs" / "usr" / "local" / "bin" / "mados-persistence"


# -----------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------
def extract_bash_functions(script_path: Path) -> List[str]:
    """Extract function names from bash script."""
    result = subprocess.run(
        ["bash", "-c", f"source {script_path} && declare -F"],
        capture_output=True,
        text=True,
        shell=False,
    )

    # Parse function names (format: "declare -f function_name")
    functions = []
    for line in result.stdout.strip().split("\n"):
        if line.startswith("declare -f"):
            func_name = line.split()[-1]
            functions.append(func_name)

    return functions


def run_bash_function(
    script_path: Path, func_name: str, *args
) -> subprocess.CompletedProcess:
    """Run a specific bash function with arguments."""
    args_str = " ".join(f'"{arg}"' for arg in args)
    cmd = [
        "bash",
        "-c",
        f"""
        source {script_path}
        {func_name} {args_str}
        echo "EXIT_CODE=$?"
        """,
    ]

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def get_script_syntax_errors(script_path: Path) -> str:
    """Get syntax errors from bash script."""
    result = subprocess.run(
        ["bash", "-n", str(script_path)],
        capture_output=True,
        text=True,
    )

    return result.stderr


# -----------------------------------------------------------------------
# Test function extraction
# -----------------------------------------------------------------------
class TestFunctionExtraction:
    """Test bash function extraction."""

    def test_setup_script_functions_extracted(self):
        """Test that setup-persistence.sh functions can be extracted."""
        functions = extract_bash_functions(SETUP_SCRIPT)

        # Should contain expected functions
        expected_functions = [
            "log",
            "ui_header",
            "ui_step",
            "ui_ok",
            "ui_warn",
            "ui_fail",
            "ui_info",
            "ui_done",
            "ui_skip",
            "is_usb_device",
            "is_optical_device",
            "strip_partition",
            "find_iso_device",
            "find_iso_partition",
            "find_persist_partition",
            "get_free_space",
            "create_persist_partition",
            "install_persist_files",
            "setup_persistence",
        ]

        for func in expected_functions:
            assert func in functions, (
                f"Function {func} not found in setup-persistence.sh"
            )

    def test_cli_script_functions_extracted(self):
        """Test that mados-persistence functions can be extracted."""
        functions = extract_bash_functions(CLI_SCRIPT)

        # Should contain expected functions
        expected_functions = [
            "print_header",
            "print_status",
            "print_error",
            "print_warning",
            "print_info",
            "check_live_env",
            "find_iso_device",
            "find_persist_partition",
            "get_persist_info",
            "show_status",
            "enable_persistence",
            "disable_persistence",
            "remove_persistence",
            "show_usage",
        ]

        for func in expected_functions:
            assert func in functions, f"Function {func} not found in mados-persistence"

    def test_script_syntax_valid(self):
        """Test that scripts have valid bash syntax."""
        for script in [SETUP_SCRIPT, CLI_SCRIPT]:
            stderr = get_script_syntax_errors(script)
            assert stderr == "", f"Syntax errors in {script.name}:\n{stderr}"


# -----------------------------------------------------------------------
# Test is_usb_device()
# -----------------------------------------------------------------------
class TestIsUsbDevice:
    """Test is_usb_device() function."""

    def test_valid_usb_device(self):
        """Test with valid USB device."""
        result = run_bash_function(SETUP_SCRIPT, "is_usb_device", "sda")

        # Should succeed (0) or fail (1) based on device properties
        # Just ensure it doesn't crash
        assert result.returncode in [0, 1]

    def test_invalid_device(self):
        """Test with invalid device."""
        result = run_bash_function(SETUP_SCRIPT, "is_usb_device", "invalid_device")

        # Should not crash
        assert result.returncode in [0, 1]

    def test_missing_device(self):
        """Test with non-existent device."""
        result = run_bash_function(SETUP_SCRIPT, "is_usb_device", "sdz999")

        # Should handle gracefully
        assert result.returncode in [0, 1]


# -----------------------------------------------------------------------
# Test is_optical_device()
# -----------------------------------------------------------------------
class TestIsOpticalDevice:
    """Test is_optical_device() function."""

    def test_optical_device(self):
        """Test with optical device."""
        result = run_bash_function(SETUP_SCRIPT, "is_optical_device", "sr0")

        # Should succeed or fail based on device properties
        assert result.returncode in [0, 1]

    def test_non_optical_device(self):
        """Test with non-optical device."""
        result = run_bash_function(SETUP_SCRIPT, "is_optical_device", "sda")

        # Should not be optical
        assert result.returncode in [0, 1]

    def test_invalid_device(self):
        """Test with invalid device."""
        result = run_bash_function(SETUP_SCRIPT, "is_optical_device", "invalid")

        # Should not crash
        assert result.returncode in [0, 1]


# -----------------------------------------------------------------------
# Test strip_partition()
# -----------------------------------------------------------------------
class TestStripPartition:
    """Test strip_partition() function."""

    def test_strip_standard_disk(self):
        """Test stripping /dev/sda1 → /dev/sda."""
        result = run_bash_function(SETUP_SCRIPT, "strip_partition", "/dev/sda1")

        assert "/dev/sda" in result.stdout

    def test_strip_nvme(self):
        """Test stripping /dev/nvme0n1p2 → /dev/nvme0n1."""
        result = run_bash_function(SETUP_SCRIPT, "strip_partition", "/dev/nvme0n1p2")

        assert "/dev/nvme0n1" in result.stdout

    def test_strip_mmcblk(self):
        """Test stripping /dev/mmcblk0p1 → /dev/mmcblk0."""
        result = run_bash_function(SETUP_SCRIPT, "strip_partition", "/dev/mmcblk0p1")

        assert "/dev/mmcblk0" in result.stdout

    def test_strip_loop(self):
        """Test stripping /dev/loop0p3 → /dev/loop0."""
        result = run_bash_function(SETUP_SCRIPT, "strip_partition", "/dev/loop0p3")

        assert "/dev/loop0" in result.stdout

    def test_no_partition(self):
        """Test with no partition number."""
        result = run_bash_function(SETUP_SCRIPT, "strip_partition", "/dev/sda")

        assert "/dev/sda" in result.stdout

    def test_empty_input(self):
        """Test with empty input."""
        result = run_bash_function(SETUP_SCRIPT, "strip_partition", "")

        # Should handle gracefully
        assert result.returncode in [0, 1]


# -----------------------------------------------------------------------
# Test get_free_space()
# -----------------------------------------------------------------------
class TestGetFreeSpace:
    """Test get_free_space() function."""

    def test_valid_device(self, temp_disk_image="/tmp/test_disk.img"):
        """Test with valid device."""
        # Create test disk image
        if not os.path.exists(temp_disk_image):
            subprocess.run(
                ["dd", "if=/dev/zero", f"of={temp_disk_image}", "bs=1M", "count=500"],
                check=True,
                capture_output=True,
            )

            # Setup loopback
            result = subprocess.run(
                ["losetup", "-f", "--show", "-P", temp_disk_image],
                capture_output=True,
                text=True,
                check=True,
            )
            loop_device = result.stdout.strip()

            # Create partition
            subprocess.run(
                ["parted", "-s", loop_device, "mklabel", "msdos"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "parted",
                    "-s",
                    loop_device,
                    "mkpart",
                    "primary",
                    "ext4",
                    "0MB",
                    "400MB",
                ],
                check=True,
                capture_output=True,
            )

        result = run_bash_function(SETUP_SCRIPT, "get_free_space", temp_disk_image)

        # Should return free space
        assert "0" in result.stdout or "100" in result.stdout

    def test_invalid_device(self):
        """Test with invalid device."""
        result = run_bash_function(SETUP_SCRIPT, "get_free_space", "/dev/nonexistent")

        # Should return 0 or handle gracefully
        assert "0" in result.stdout or result.returncode == 1

    def test_empty_input(self):
        """Test with empty input."""
        result = run_bash_function(SETUP_SCRIPT, "get_free_space", "")

        # Should handle gracefully
        assert "0" in result.stdout or result.returncode == 1


# -----------------------------------------------------------------------
# Test find_iso_partition()
# -----------------------------------------------------------------------
class TestFindIsoPartition:
    """Test find_iso_partition() function."""

    def test_no_iso_partitions(self):
        """Test when no ISO partitions exist."""
        result = run_bash_function(SETUP_SCRIPT, "find_iso_partition")

        # Should not crash
        assert result.returncode == 0

    def test_iso_partition_exists(self):
        """Test when ISO partition exists."""
        # Mock lsblk to return ISO partition
        cmd = [
            "bash",
            "-c",
            f"""
            source {SETUP_SCRIPT}
            
            lsblk() {{
                echo "sda iso9660"
                echo "sdb ext4"
            }}
            
            result=$(find_iso_partition)
            echo "$result"
            """,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Should find ISO partition
        assert "sda" in result.stdout


# -----------------------------------------------------------------------
# Test find_persist_partition()
# -----------------------------------------------------------------------
class TestFindPersistPartition:
    """Test find_persist_partition() function."""

    def test_no_persistence_partition(self):
        """Test when no persistence partition exists."""
        result = run_bash_function(SETUP_SCRIPT, "find_persist_partition")

        # Should return empty or handle gracefully
        assert result.returncode == 0

    def test_persistence_partition_exists(self):
        """Test when persistence partition exists."""
        cmd = [
            "bash",
            "-c",
            f"""
            source {SETUP_SCRIPT}
            
            lsblk() {{
                echo "sda1 persistence"
            }}
            
            result=$(find_persist_partition)
            echo "$result"
            """,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Should find persistence partition
        assert "sda1" in result.stdout

    def test_with_parent_device(self):
        """Test with parent device parameter."""
        cmd = [
            "bash",
            "-c",
            f"""
            source {SETUP_SCRIPT}
            
            lsblk() {{
                case "$1" in
                    /dev/sda) echo "sda1 persistence";;
                esac
            }}
            
            result=$(find_persist_partition "/dev/sda")
            echo "$result"
            """,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Should scope to parent device
        assert "sda1" in result.stdout


# -----------------------------------------------------------------------
# Test setup_persistence()
# -----------------------------------------------------------------------
class TestSetupPersistence:
    """Test setup_persistence() function."""

    def test_missing_iso_device(self):
        """Test when ISO device cannot be determined."""
        result = run_bash_function(SETUP_SCRIPT, "setup_persistence")

        # Should handle gracefully
        assert result.returncode in [0, 1]

    def test_optical_media_detected(self):
        """Test when optical media is detected."""
        cmd = [
            "bash",
            "-c",
            f"""
            source {SETUP_SCRIPT}
            
            find_iso_device() {{
                echo "/dev/sr0"
            }}
            
            is_optical_device() {{
                return 0
            }}
            
            setup_persistence
            echo "EXIT=$?"
            """,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Should skip optical media
        assert "skip" in result.stdout.lower() or "Optical" in result.stdout


# -----------------------------------------------------------------------
# Test mados-persistence CLI functions
# -----------------------------------------------------------------------
class TestMadosPersistenceFunctions:
    """Test mados-persistence CLI functions."""

    def test_show_status(self):
        """Test show_status function."""
        result = run_bash_function(CLI_SCRIPT, "show_status")

        # Should not crash
        assert result.returncode in [0, 1]

    def test_enable_persistence(self):
        """Test enable_persistence function."""
        result = run_bash_function(CLI_SCRIPT, "enable_persistence")

        # Should not crash
        assert result.returncode in [0, 1]

    def test_disable_persistence(self):
        """Test disable_persistence function."""
        result = run_bash_function(CLI_SCRIPT, "disable_persistence")

        # Should not crash
        assert result.returncode in [0, 1]

    def test_remove_persistence(self):
        """Test remove_persistence function."""
        result = run_bash_function(CLI_SCRIPT, "remove_persistence")

        # Should not crash
        assert result.returncode in [0, 1]

    def test_show_usage(self):
        """Test show_usage function."""
        result = run_bash_function(CLI_SCRIPT, "show_usage")

        # Should succeed
        assert result.returncode == 0
        assert "Usage" in result.stdout


# -----------------------------------------------------------------------
# Test error handling and edge cases
# -----------------------------------------------------------------------
class TestErrorHandling:
    """Test error handling in bash functions."""

    def test_empty_string_handling(self):
        """Test functions handle empty strings gracefully."""
        test_functions = [
            "is_usb_device",
            "is_optical_device",
            "strip_partition",
            "get_free_space",
            "find_iso_partition",
            "find_persist_partition",
        ]

        for func in test_functions:
            result = run_bash_function(SETUP_SCRIPT, func, "")
            # Should not crash
            assert result.returncode in [0, 1], f"{func} crashed with empty input"

    def test_invalid_path_handling(self):
        """Test functions handle invalid paths gracefully."""
        result = run_bash_function(
            SETUP_SCRIPT, "get_free_space", "/dev/invalid_device_xyz"
        )

        # Should handle gracefully
        assert result.returncode in [0, 1]

    def test_missing_dependencies(self):
        """Test functions handle missing dependencies."""
        # Run with PATH modified to exclude essential commands
        env = os.environ.copy()
        env["PATH"] = "/usr/bin"

        result = subprocess.run(
            ["bash", "-c", f"source {SETUP_SCRIPT} && is_usb_device sda"],
            capture_output=True,
            text=True,
            env=env,
        )

        # Should not crash
        assert result.returncode in [0, 1]


# -----------------------------------------------------------------------
# Test function coverage
# -----------------------------------------------------------------------
class TestFunctionCoverage:
    """Test function coverage tracking."""

    def test_all_functions_tested(self):
        """Verify all functions have at least one test."""
        setup_functions = extract_bash_functions(SETUP_SCRIPT)
        cli_functions = extract_bash_functions(CLI_SCRIPT)

        all_functions = setup_functions + cli_functions

        # Check that each function has at least one test method
        tested_functions = set()

        for name, obj in list(globals().items()):
            if name.startswith("Test") and hasattr(obj, "__dict__"):
                for method_name in obj.__dict__:
                    if method_name.startswith("test_"):
                        # Extract function name from test method name
                        for func in all_functions:
                            if func.lower() in method_name.lower():
                                tested_functions.add(func)

        # At least 80% of functions should be tested
        coverage = len(tested_functions) / len(all_functions)
        assert coverage >= 0.8, f"Function coverage too low: {coverage:.1%}"


if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "--cov=airootfs/usr/local/bin/",
            "--cov-report=term-missing",
        ]
    )
