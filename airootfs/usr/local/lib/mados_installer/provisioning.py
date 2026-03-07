"""
madOS Installer - YAML Configuration Parser

Parses mados-config.yaml for automated provisioning.
"""

import os
from typing import Any, Optional


try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ProvisioningConfig:
    """Represents a parsed provisioning configuration."""
    
    def __init__(self):
        # Disk configuration
        self.disk_device: str = "auto"
        self.partitioning: str = "auto"
        self.filesystem: str = "ext4"
        
        # User configuration
        self.username: str = ""
        self.fullname: str = ""
        self.password: str = ""
        self.password_hash: Optional[str] = None
        self.groups: list = ["wheel", "audio", "video", "storage"]
        self.shell: str = "/usr/bin/zsh"
        
        # System configuration
        self.hostname: str = "mados-system"
        self.timezone: str = "UTC"
        self.locale: str = "en_US.UTF-8"
        self.keyboard_layout: str = "us"
        self.enable_ssh: bool = False
        self.ssh_port: int = 22
        
        # Package selection
        self.dev_tools: bool = False
        self.ai_ml: bool = False
        self.multimedia: bool = False
        self.extra_packages: list = []
        
        # Post-install scripts
        self.post_install_commands: list = []
        
        # Advanced options
        self.encryption_enabled: bool = False
        self.encryption_password: Optional[str] = None
        self.bootloader: str = "grub"
        self.kernel: str = "linux"
        self.enable_microcode: bool = True
        self.enable_plymouth: bool = True
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the configuration.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Required fields
        if not self.username:
            errors.append("Username is required")
        elif not self.username.replace("_", "").replace("-", "").isalnum():
            errors.append("Username must contain only alphanumeric characters, underscores, or hyphens")
        
        if not self.hostname:
            errors.append("Hostname is required")
        
        if not self.timezone:
            errors.append("Timezone is required")
        
        if not self.locale:
            errors.append("Locale is required")
        
        # Password or password_hash required
        if not self.password and not self.password_hash:
            errors.append("Password or password_hash is required")
        
        # Validate disk
        if self.disk_device and self.disk_device != "auto":
            if not self.disk_device.startswith("/dev/"):
                errors.append("Disk device must be a path like /dev/sda")
        
        # Validate filesystem
        valid_filesystems = ["ext4", "btrfs", "xfs"]
        if self.filesystem not in valid_filesystems:
            errors.append(f"Filesystem must be one of: {', '.join(valid_filesystems)}")
        
        # Validate partitioning
        valid_partitioning = ["auto", "separate_home"]
        if self.partitioning not in valid_partitioning:
            errors.append(f"Partitioning must be one of: {', '.join(valid_partitioning)}")
        
        # Validate bootloader
        valid_bootloaders = ["grub", "systemd-boot"]
        if self.bootloader not in valid_bootloaders:
            errors.append(f"Bootloader must be one of: {', '.join(valid_bootloaders)}")
        
        # Validate kernel
        valid_kernels = ["linux", "linux-lts", "linux-zen"]
        if self.kernel not in valid_kernels:
            errors.append(f"Kernel must be one of: {', '.join(valid_kernels)}")
        
        return (len(errors) == 0, errors)
    
    def to_install_data(self) -> dict:
        """
        Convert to installer's install_data format.
        
        Returns:
            Dictionary compatible with installer's install_data
        """
        return {
            "disk": self.disk_device if self.disk_device != "auto" else None,
            "separate_home": self.partitioning == "separate_home",
            "filesystem": self.filesystem,
            "username": self.username,
            "fullname": self.fullname or self.username,
            "password": self.password,
            "password_hash": self.password_hash,
            "groups": self.groups,
            "shell": self.shell,
            "hostname": self.hostname,
            "timezone": self.timezone,
            "locale": self.locale,
            "keyboard_layout": self.keyboard_layout,
            "enable_ssh": self.enable_ssh,
            "ssh_port": self.ssh_port,
            "package_selection": self._get_package_list(),
            "post_install_commands": self.post_install_commands,
            "encryption_enabled": self.encryption_enabled,
            "encryption_password": self.encryption_password,
            "bootloader": self.bootloader,
            "kernel": self.kernel,
            "enable_microcode": self.enable_microcode,
            "enable_plymouth": self.enable_plymouth,
        }
    
    def _get_package_list(self) -> list[str]:
        """Get list of selected packages based on groups."""
        selected = []
        
        # Map package groups to individual packages
        from .pages.packages import PACKAGE_GROUPS
        
        if self.dev_tools:
            for pkg in PACKAGE_GROUPS.get("dev_tools", {}).get("packages", []):
                if pkg.get("default", False):
                    selected.append(pkg["id"])
        
        if self.ai_ml:
            for pkg in PACKAGE_GROUPS.get("ai_ml", {}).get("packages", []):
                if pkg.get("default", False):
                    selected.append(pkg["id"])
        
        if self.multimedia:
            for pkg in PACKAGE_GROUPS.get("multimedia", {}).get("packages", []):
                if pkg.get("default", False):
                    selected.append(pkg["id"])
        
        # Add extra packages
        selected.extend(self.extra_packages)
        
        return selected


def parse_yaml_config(filepath: str) -> ProvisioningConfig:
    """
    Parse a YAML configuration file.
    
    Args:
        filepath: Path to the YAML file
        
    Returns:
        ProvisioningConfig object
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML is invalid
        ImportError: If PyYAML is not installed
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")
    
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Config file not found: {filepath}")
    
    with open(filepath) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
    
    if not data or not isinstance(data, dict):
        raise ValueError("YAML must be a valid dictionary")
    
    config = ProvisioningConfig()
    
    # Parse disk section
    if "disk" in data:
        disk = data["disk"]
        config.disk_device = disk.get("device", config.disk_device)
        config.partitioning = disk.get("partitioning", config.partitioning)
        config.filesystem = disk.get("filesystem", config.filesystem)
    
    # Parse user section
    if "user" in data:
        user = data["user"]
        config.username = user.get("username", config.username)
        config.fullname = user.get("fullname", config.fullname)
        config.password = user.get("password", config.password)
        config.password_hash = user.get("password_hash", config.password_hash)
        config.groups = user.get("groups", config.groups)
        config.shell = user.get("shell", config.shell)
    
    # Parse system section
    if "system" in data:
        system = data["system"]
        config.hostname = system.get("hostname", config.hostname)
        config.timezone = system.get("timezone", config.timezone)
        config.locale = system.get("locale", config.locale)
        config.keyboard_layout = system.get("keyboard_layout", config.keyboard_layout)
        config.enable_ssh = system.get("enable_ssh", config.enable_ssh)
        config.ssh_port = system.get("ssh_port", config.ssh_port)
    
    # Parse packages section
    if "packages" in data:
        packages = data["packages"]
        config.dev_tools = packages.get("dev_tools", config.dev_tools)
        config.ai_ml = packages.get("ai_ml", config.ai_ml)
        config.multimedia = packages.get("multimedia", config.multimedia)
        config.extra_packages = packages.get("extra", config.extra_packages)
    
    # Parse post_install section
    if "post_install" in data:
        post_install = data["post_install"]
        config.post_install_commands = post_install.get("commands", config.post_install_commands)
    
    # Parse advanced section
    if "advanced" in data:
        advanced = data["advanced"]
        
        if "encryption" in advanced:
            encryption = advanced["encryption"]
            config.encryption_enabled = encryption.get("enabled", config.encryption_enabled)
            config.encryption_password = encryption.get("password", config.encryption_password)
            config.encryption_password_hash = encryption.get("password_hash")
        
        config.bootloader = advanced.get("bootloader", config.bootloader)
        config.kernel = advanced.get("kernel", config.kernel)
        config.enable_microcode = advanced.get("enable_microcode", config.enable_microcode)
        config.enable_plymouth = advanced.get("enable_plymouth", config.enable_plymouth)
    
    return config


def load_config_from_file(filepath: str) -> tuple[Optional[ProvisioningConfig], list[str]]:
    """
    Load and validate a configuration file.
    
    Args:
        filepath: Path to the YAML file
        
    Returns:
        Tuple of (config object or None, list of error messages)
    """
    try:
        config = parse_yaml_config(filepath)
        is_valid, errors = config.validate()
        
        if not is_valid:
            return (None, errors)
        
        return (config, [])
        
    except FileNotFoundError as e:
        return (None, [str(e)])
    except ValueError as e:
        return (None, [str(e)])
    except ImportError as e:
        return (None, [str(e)])
    except Exception as e:
        return (None, [f"Unexpected error: {e}"])
