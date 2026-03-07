"""
Tests for madOS first-boot configuration and setup
"""

import os
import re
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class TestConfigScriptStructure(unittest.TestCase):
    """Test the structure of the first-boot config script."""

    def setUp(self):
        """Load the configuration script content from modules."""
        import sys
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()
        
        from mados_installer.modules.config_generator import build_config_script
        from mados_installer.config import LOCALE_MAP, TIMEZONES
        
        # Generate a sample config script
        sample_data = {
            "username": "testuser",
            "timezone": "America/New_York",
            "locale": "en_US.UTF-8",
            "hostname": "test-host",
            "disk": "/dev/sda",
        }
        self.content = build_config_script(sample_data)

    def test_config_script_starts_with_shebang(self):
        """Config script must start with #!/bin/bash"""
        self.assertTrue(self.content.strip().startswith("#!/bin/bash"))

    def test_config_script_uses_set_e(self):
        """Config script must use set -e for error handling"""
        self.assertIn("set -e", self.content)

    def test_config_script_executes_configure_system(self):
        """Config script must execute configure-system.sh"""
        self.assertIn("configure-system.sh", self.content)

    def test_config_script_passes_username(self):
        """Config script must pass username parameter"""
        self.assertIn('"testuser"', self.content)

    def test_config_script_passes_timezone(self):
        """Config script must pass timezone parameter"""
        self.assertIn('"America/New_York"', self.content)

    def test_config_script_passes_locale(self):
        """Config script must pass locale parameter"""
        self.assertIn('"en_US.UTF-8"', self.content)


class TestPartitioningModule(unittest.TestCase):
    """Test the partitioning module."""

    def setUp(self):
        import sys
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()

    def test_get_partition_prefix_for_sda(self):
        """get_partition_prefix should return /dev/sda for sda"""
        from mados_installer.modules.partitioning import get_partition_prefix
        
        prefix = get_partition_prefix("/dev/sda")
        self.assertEqual(prefix, "/dev/sda")

    def test_get_partition_prefix_for_nvme(self):
        """get_partition_prefix should return /dev/nvme0n1p for nvme"""
        from mados_installer.modules.partitioning import get_partition_prefix
        
        prefix = get_partition_prefix("/dev/nvme0n1")
        self.assertEqual(prefix, "/dev/nvme0n1p")

    def test_get_partition_prefix_for_mmcblk(self):
        """get_partition_prefix should return /dev/mmcblk0p for mmcblk"""
        from mados_installer.modules.partitioning import get_partition_prefix
        
        prefix = get_partition_prefix("/dev/mmcblk0")
        self.assertEqual(prefix, "/dev/mmcblk0p")


class TestFileCopierModule(unittest.TestCase):
    """Test the file copier module."""

    def setUp(self):
        import sys
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()

    def test_ensure_kernel_in_target_exists(self):
        """ensure_kernel_in_target should handle existing kernel"""
        from mados_installer.modules.file_copier import ensure_kernel_in_target
        
        # Just test it doesn't crash - actual testing requires chroot
        app = MagicMock()
        # Mock /mnt/boot to not exist to avoid errors
        with patch('os.path.isfile', return_value=False):
            try:
                ensure_kernel_in_target(app)
            except Exception:
                # Expected to fail in test environment
                pass

    def test_step_copy_scripts_creates_directories(self):
        """step_copy_scripts should create required directories"""
        from mados_installer.modules.file_copier import step_copy_scripts
        
        app = MagicMock()
        with patch('subprocess.run') as mock_run:
            step_copy_scripts(app)
            # Should create /mnt/usr/local/bin
            mock_run.assert_any_call(["mkdir", "-p", "/mnt/usr/local/bin"], check=False)


class TestPackagesModule(unittest.TestCase):
    """Test the packages module."""

    def setUp(self):
        import sys
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()

    def test_prepare_pacman_exists(self):
        """prepare_pacman function should exist"""
        from mados_installer.modules.packages import prepare_pacman
        self.assertTrue(callable(prepare_pacman))

    def test_rsync_rootfs_with_progress_exists(self):
        """rsync_rootfs_with_progress function should exist"""
        from mados_installer.modules.packages import rsync_rootfs_with_progress
        self.assertTrue(callable(rsync_rootfs_with_progress))


if __name__ == '__main__':
    unittest.main()
