"""madOS Bluetooth Configuration - Abstract interfaces.

Defines contracts for backend operations to enable dependency injection
and testing without requiring real hardware or GTK.
"""

from abc import ABC, abstractmethod
from typing import List, Callable
from dataclasses import dataclass


@dataclass
class BluetoothDevice:
    """Represents a Bluetooth device."""

    address: str
    name: str = ""
    paired: bool = False
    connected: bool = False
    trusted: bool = False
    icon: str = ""

    @property
    def display_name(self) -> str:
        """Return user-friendly display name."""
        return self.name if self.name else self.address


class BackendInterface(ABC):
    """Abstract interface for Bluetooth backend operations."""

    @abstractmethod
    def check_available(self) -> bool:
        """Check if Bluetooth adapter is available."""

    @abstractmethod
    def is_powered(self) -> bool:
        """Check if adapter is powered on."""

    @abstractmethod
    def set_power(self, on: bool) -> bool:
        """Power adapter on or off."""

    @abstractmethod
    def start_scan(self) -> bool:
        """Start scanning for devices."""

    @abstractmethod
    def stop_scan(self) -> bool:
        """Stop scanning for devices."""

    @abstractmethod
    def get_devices(self) -> List[BluetoothDevice]:
        """Get all known devices (paired + discovered)."""

    @abstractmethod
    def pair_device(self, address: str) -> str:
        """Pair with a device."""

    @abstractmethod
    def connect_device(self, address: str) -> str:
        """Connect to a paired device."""

    @abstractmethod
    def disconnect_device(self, address: str) -> bool:
        """Disconnect from a device."""

    @abstractmethod
    def remove_device(self, address: str) -> bool:
        """Remove (unpair) a device."""

    @abstractmethod
    def trust_device(self, address: str, trusted: bool = True) -> bool:
        """Set or unset trust for a device."""

    def clear_devices(self) -> None:
        """Optional: clear all tracked devices (mock-only, no-op for real)."""
        pass


class AsyncBackendInterface(ABC):
    """Abstract interface for async wrapper operations."""

    @abstractmethod
    def async_scan(
        self, callback: Callable[[List[BluetoothDevice]], None], scan_duration: int = 5
    ):
        """Scan for devices asynchronously."""

    @abstractmethod
    def async_pair(self, address: str, callback: Callable[[str], None]):
        """Pair with a device asynchronously."""

    @abstractmethod
    def async_connect(self, address: str, callback: Callable[[str], None]):
        """Connect to a device asynchronously."""

    @abstractmethod
    def async_disconnect(self, address: str, callback: Callable[[bool], None]):
        """Disconnect from a device asynchronously."""

    @abstractmethod
    def async_remove(self, address: str, callback: Callable[[bool], None]):
        """Remove a device asynchronously."""

    @abstractmethod
    def async_set_power(self, on: bool, callback: Callable[[bool], None]):
        """Toggle adapter power asynchronously."""

    @abstractmethod
    def async_get_adapter_state(self, callback: Callable[[bool, bool], None]):
        """Fetch adapter availability and power state asynchronously."""
