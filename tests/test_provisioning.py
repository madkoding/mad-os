#!/usr/bin/env python3
"""
Tests for madOS Automated Provisioning YAML parser.

Validates that:
- YAML configuration is parsed correctly
- Validation catches missing required fields
- Configuration converts to install_data format
"""

import os
import sys
import tempfile
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")

sys.path.insert(0, LIB_DIR)


class TestProvisioningConfig(unittest.TestCase):
    """Test ProvisioningConfig class."""

    def test_default_values(self):
        """Config should have sensible defaults."""
        from mados_installer.provisioning import ProvisioningConfig
        
        config = ProvisioningConfig()
        
        # Disk defaults
        self.assertEqual(config.disk_device, "auto")
        self.assertEqual(config.partitioning, "auto")
        self.assertEqual(config.filesystem, "ext4")
        
        # System defaults
        self.assertEqual(config.hostname, "mados-system")
        self.assertEqual(config.timezone, "UTC")
        self.assertEqual(config.locale, "en_US.UTF-8")
        
        # User defaults (empty - required)
        self.assertEqual(config.username, "")
        self.assertEqual(config.password, "")
        
        # Package defaults
        self.assertFalse(config.dev_tools)
        self.assertFalse(config.ai_ml)
        self.assertFalse(config.multimedia)

    def test_validation_requires_username(self):
        """Validation should fail without username."""
        from mados_installer.provisioning import ProvisioningConfig
        
        config = ProvisioningConfig()
        is_valid, errors = config.validate()
        
        self.assertFalse(is_valid)
        self.assertIn("Username is required", errors)

    def test_validation_requires_password(self):
        """Validation should fail without password."""
        from mados_installer.provisioning import ProvisioningConfig
        
        config = ProvisioningConfig()
        config.username = "testuser"
        
        is_valid, errors = config.validate()
        
        self.assertFalse(is_valid)
        self.assertIn("Password or password_hash is required", errors)

    def test_validation_with_minimal_config(self):
        """Validation should pass with minimal required fields."""
        from mados_installer.provisioning import ProvisioningConfig
        
        config = ProvisioningConfig()
        config.username = "testuser"
        config.password = "testpass"
        config.hostname = "testhost"
        config.timezone = "UTC"
        config.locale = "en_US.UTF-8"
        
        is_valid, errors = config.validate()
        
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_validation_invalid_filesystem(self):
        """Validation should reject invalid filesystem."""
        from mados_installer.provisioning import ProvisioningConfig
        
        config = ProvisioningConfig()
        config.username = "testuser"
        config.password = "testpass"
        config.filesystem = "ntfs"  # Invalid
        
        is_valid, errors = config.validate()
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Filesystem" in e for e in errors))

    def test_to_install_data(self):
        """Config should convert to install_data format."""
        from mados_installer.provisioning import ProvisioningConfig
        
        config = ProvisioningConfig()
        config.username = "testuser"
        config.password = "testpass"
        config.hostname = "testhost"
        config.timezone = "America/New_York"
        config.locale = "en_US.UTF-8"
        config.dev_tools = True
        
        data = config.to_install_data()
        
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["password"], "testpass")
        self.assertEqual(data["hostname"], "testhost")
        self.assertEqual(data["timezone"], "America/New_York")
        self.assertEqual(data["locale"], "en_US.UTF-8")
        self.assertIn("package_selection", data)


class TestYAMLParsing(unittest.TestCase):
    """Test YAML config file parsing."""

    def _write_temp_yaml(self, content):
        """Write content to temp file and return path."""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path

    def test_parse_minimal_config(self):
        """Should parse minimal valid config."""
        from mados_installer.provisioning import parse_yaml_config
        
        yaml_content = """
user:
  username: testuser
  password: testpass
system:
  hostname: testhost
  timezone: UTC
  locale: en_US.UTF-8
"""
        path = self._write_temp_yaml(yaml_content)
        try:
            config = parse_yaml_config(path)
            
            self.assertEqual(config.username, "testuser")
            self.assertEqual(config.password, "testpass")
            self.assertEqual(config.hostname, "testhost")
        finally:
            os.unlink(path)

    def test_parse_full_config(self):
        """Should parse full configuration."""
        from mados_installer.provisioning import parse_yaml_config
        
        yaml_content = """
disk:
  device: /dev/sda
  partitioning: separate_home
  filesystem: btrfs

user:
  username: maduser
  fullname: "MadOS User"
  password: securepass123
  groups:
    - wheel
    - docker

system:
  hostname: mados-workstation
  timezone: America/New_York
  locale: en_US.UTF-8
  enable_ssh: true
  ssh_port: 2222

packages:
  dev_tools: true
  ai_ml: true
  multimedia: false
  extra:
    - vim
    - htop

post_install:
  commands:
    - systemctl enable docker
    - echo "Done!"

advanced:
  bootloader: grub
  kernel: linux-zen
  enable_microcode: true
"""
        path = self._write_temp_yaml(yaml_content)
        try:
            config = parse_yaml_config(path)
            
            self.assertEqual(config.disk_device, "/dev/sda")
            self.assertEqual(config.partitioning, "separate_home")
            self.assertEqual(config.filesystem, "btrfs")
            self.assertEqual(config.username, "maduser")
            self.assertEqual(config.fullname, "MadOS User")
            self.assertEqual(config.hostname, "mados-workstation")
            self.assertTrue(config.dev_tools)
            self.assertTrue(config.ai_ml)
            self.assertFalse(config.multimedia)
            self.assertIn("vim", config.extra_packages)
            self.assertIn("systemctl enable docker", config.post_install_commands)
            self.assertEqual(config.bootloader, "grub")
            self.assertEqual(config.kernel, "linux-zen")
        finally:
            os.unlink(path)

    def test_parse_invalid_yaml(self):
        """Should raise error on invalid YAML."""
        from mados_installer.provisioning import parse_yaml_config
        
        yaml_content = """
user:
  username: test
  password: test
  invalid yaml here: [
"""
        path = self._write_temp_yaml(yaml_content)
        try:
            with self.assertRaises(ValueError):
                parse_yaml_config(path)
        finally:
            os.unlink(path)

    def test_load_config_with_errors(self):
        """load_config_from_file should return errors."""
        from mados_installer.provisioning import load_config_from_file
        
        yaml_content = """
user:
  username: test
  # Missing required fields
"""
        path = self._write_temp_yaml(yaml_content)
        try:
            config, errors = load_config_from_file(path)
            
            self.assertIsNone(config)
            self.assertGreater(len(errors), 0)
        finally:
            os.unlink(path)


class TestProvisioningIntegration(unittest.TestCase):
    """Test integration with installer."""

    def test_module_exists(self):
        """provisioning module should exist."""
        import mados_installer.provisioning
        self.assertTrue(hasattr(mados_installer.provisioning, 'ProvisioningConfig'))
        self.assertTrue(hasattr(mados_installer.provisioning, 'parse_yaml_config'))

    def test_example_config_exists(self):
        """Example config file should exist."""
        example_path = os.path.join(REPO_DIR, "mados-config-example.yaml")
        self.assertTrue(os.path.isfile(example_path))

    def test_example_config_valid(self):
        """Example config should be valid YAML (may have validation errors for required fields)."""
        from mados_installer.provisioning import load_config_from_file
        
        example_path = os.path.join(REPO_DIR, "mados-config-example.yaml")
        config, errors = load_config_from_file(example_path)
        
        # Example has placeholder values, so it may not validate
        # but YAML should be syntactically correct (not raise exceptions)
        
        # Either config loads successfully, or we get validation errors (not parse errors)
        if config is None:
            # Should have validation errors, not file/parse errors
            self.assertGreater(len(errors), 0)
            # Should not be file not found or YAML syntax error
            self.assertFalse(any("not found" in e.lower() for e in errors))
            self.assertFalse(any("Invalid YAML" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
