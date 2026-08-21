#!/usr/bin/env python3
"""Version manager for madOS OTA updates.

Handles reading and writing version information.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


VERSION_FILE = Path("/etc/mados/version.json")


class VersionManager:
    """Manages version information for madOS."""

    def __init__(self, version_file: Path = VERSION_FILE):
        self.version_file = version_file

    def get_version(self) -> dict:
        """Get current version information.

        Returns:
            Version dictionary
        """
        if not self.version_file.exists():
            return self._default_version()

        with open(self.version_file) as f:
            return json.load(f)

    def set_version(self, version_data: dict) -> bool:
        """Set version information.

        Args:
            version_data: Version dictionary to save

        Returns:
            True if successful, False otherwise
        """
        try:
            self.version_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.version_file, "w") as f:
                json.dump(version_data, f, indent=2)

            return True

        except Exception as e:
            print(f"Failed to save version: {e}")
            return False

    def update_last_check(self) -> bool:
        """Update the last_check timestamp.

        Returns:
            True if successful
        """
        version_data = self.get_version()
        version_data["last_check"] = datetime.now().isoformat()
        return self.set_version(version_data)

    def set_auto_update(self, enabled: bool) -> bool:
        """Set auto-update preference.

        Args:
            enabled: Whether auto-update is enabled

        Returns:
            True if successful
        """
        version_data = self.get_version()
        version_data["auto_update"] = enabled
        return self.set_version(version_data)

    def get_app_version(self, app_name: str) -> str:
        """Get version of a specific app.

        Args:
            app_name: Name of the application

        Returns:
            Version string or "unknown"
        """
        version_data = self.get_version()
        return version_data.get("apps", {}).get(app_name, "unknown")

    def compare_version(self, other_version: str) -> int:
        """Compare versions using semantic versioning.

        Args:
            other_version: Version string to compare

        Returns:
            -1 if other < current, 0 if equal, 1 if other > current
        """
        current = self.get_version().get("version", "0.0.0")
        
        # Use packaging library if available for proper semver comparison
        try:
            from packaging import version as pkg_version
            current_v = pkg_version.parse(current)
            other_v = pkg_version.parse(other_version.lstrip("v"))
            
            if current_v < other_v:
                return 1
            elif current_v > other_v:
                return -1
            else:
                return 0
        except ImportError:
            # Fallback to simple tuple comparison
            pass
        
        def parse_version(v: str) -> tuple:
            v = v.lstrip("v")
            parts = v.split("-")[0].split(".")
            return tuple(int(p) if p.isdigit() else 0 for p in parts)

        current_tuple = parse_version(current)
        other_tuple = parse_version(other_version)

        if current_tuple < other_tuple:
            return 1
        elif current_tuple > other_tuple:
            return -1
        else:
            return 0

    @staticmethod
    def _compare_versions_simple(v1: str, v2: str) -> int:
        """Simple version comparison fallback.
        
        Args:
            v1: First version string
            v2: Second version string
            
        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        def parse(v: str) -> tuple:
            v = v.lstrip("v")
            parts = v.split("-")[0].split(".")
            return tuple(int(p) if p.isdigit() else 0 for p in parts)
        
        t1 = parse(v1)
        t2 = parse(v2)
        
        if t1 < t2:
            return -1
        elif t1 > t2:
            return 1
        return 0
    
    @staticmethod
    def _versions_equal(v1: str, v2: str) -> bool:
        """Check if two versions are equal.
        
        Args:
            v1: First version string
            v2: Second version string
            
        Returns:
            True if versions are equal
        """
        return VersionManager._compare_versions_simple(v1, v2) == 0

    @staticmethod
    def _default_version() -> dict:
        """Get default version dictionary."""
        return {
            "version": "0.0.0",
            "release_date": "",
            "system": {"version": "0.0.0", "arch": "x86_64"},
            "apps": {
                "mados-installer": "0.0.0",
                "mados-audio-player": "0.0.0",
                "mados-video-player": "0.0.0",
                "mados-photo-viewer": "0.0.0",
                "mados-pdf-viewer": "0.0.0",
                "mados-launcher": "0.0.0",
                "mados-equalizer": "0.0.0",
            },
            "update_channel": "stable",
            "last_check": None,
            "auto_update": False,
        }

    def print_info(self) -> None:
        """Print version information to stdout."""
        version_data = self.get_version()

        print(f"madOS Version: {version_data.get('version', 'unknown')}")
        print(f"Release Date: {version_data.get('release_date', 'unknown')}")
        print(f"Update Channel: {version_data.get('update_channel', 'stable')}")
        print(f"Auto Update: {version_data.get('auto_update', False)}")

        if version_data.get("last_check"):
            print(f"Last Check: {version_data['last_check']}")

        print("\nSystem:")
        system = version_data.get("system", {})
        print(f"  Version: {system.get('version', 'unknown')}")
        print(f"  Arch: {system.get('arch', 'unknown')}")

        print("\nApps:")
        apps = version_data.get("apps", {})
        for app, ver in sorted(apps.items()):
            print(f"  {app}: {ver}")


def main():
    """CLI for version management."""
    import argparse

    parser = argparse.ArgumentParser(description="madOS Version Manager")
    parser.add_argument("--info", action="store_true", help="Show version info")
    parser.add_argument("--channel", type=str, help="Set update channel")
    parser.add_argument(
        "--auto-update",
        type=bool,
        nargs="?",
        const=True,
        default=None,
        help="Enable/disable auto-update",
    )

    args = parser.parse_args()

    manager = VersionManager()

    if args.info:
        manager.print_info()

    elif args.channel:
        version_data = manager.get_version()
        version_data["update_channel"] = args.channel
        manager.set_version(version_data)
        print(f"Update channel set to: {args.channel}")

    elif args.auto_update is not None:
        manager.set_auto_update(args.auto_update)
        status = "enabled" if args.auto_update else "disabled"
        print(f"Auto-update {status}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
