"""madOS Bluetooth Configuration - Mock backend for testing.

Provides a mock implementation of the BluetoothBackendInterface
that simulates Bluetooth operations without requiring real hardware.
"""

import threading
import time
from typing import List, Callable
from copy import copy
from .interfaces import BackendInterface, BluetoothDevice


class MockBluetoothBackend(BackendInterface):
    """Mock implementation for unit testing.

    Simulates Bluetooth adapter and device operations without
    requiring real hardware or calling bluetoothctl subprocess.
    """

    def __init__(self):
        """Initialize mock backend state."""
        self._powered = False
        self._scanning = False
        self._devices: List[BluetoothDevice] = []
        self._paired: set = set()
        self._connected: set = set()
        self._trusted: set = set()
        self._lock = threading.Lock()

    def check_available(self) -> bool:
        """Check if Bluetooth adapter is available."""
        return True

    def is_powered(self) -> bool:
        """Check if adapter is powered on."""
        return self._powered

    def set_power(self, on: bool) -> bool:
        """Power adapter on or off."""
        self._powered = on
        if not on:
            self._scanning = False
            self._connected.clear()
        return True

    def start_scan(self) -> bool:
        """Start scanning for devices."""
        if not self._powered:
            return False
        self._scanning = True
        return True

    def stop_scan(self) -> bool:
        """Stop scanning for devices."""
        self._scanning = False
        return True

    def get_devices(self) -> List[BluetoothDevice]:
        """Get all known devices (paired + discovered)."""
        with self._lock:
            devices = []

            for dev in self._devices:
                new_dev = BluetoothDevice(
                    address=dev.address,
                    name=dev.name,
                    paired=dev.address in self._paired,
                    connected=dev.address in self._connected,
                    trusted=dev.address in self._trusted,
                    icon=dev.icon,
                )
                devices.append(new_dev)

            devices.sort(
                key=lambda d: (not d.connected, not d.paired, d.display_name.lower())
            )
            return devices

    def pair_device(self, address: str) -> str:
        """Pair with a device."""
        if not self._powered:
            return "adapter_off"

        with self._lock:
            if address not in [d.address for d in self._devices]:
                self._devices.append(
                    BluetoothDevice(address=address, name=f"Device {address}")
                )

            self._paired.add(address)
            return "paired"

    def connect_device(self, address: str) -> str:
        """Connect to a paired device."""
        if not self._powered:
            return "adapter_off"

        if address not in self._paired:
            return "not_paired"

        with self._lock:
            self._connected.add(address)
            return "connected"

    def disconnect_device(self, address: str) -> bool:
        """Disconnect from a device."""
        with self._lock:
            self._connected.discard(address)
            return True

    def remove_device(self, address: str) -> bool:
        """Remove (unpair) a device."""
        with self._lock:
            self._devices = [d for d in self._devices if d.address != address]
            self._paired.discard(address)
            self._connected.discard(address)
            self._trusted.discard(address)
            return True

    def trust_device(self, address: str, trusted: bool = True) -> bool:
        """Set or unset trust for a device."""
        with self._lock:
            if trusted:
                self._trusted.add(address)
            else:
                self._trusted.discard(address)
            return True

    def add_device(self, device: BluetoothDevice) -> None:
        """Manually add a device for testing."""
        with self._lock:
            if device.address not in [d.address for d in self._devices]:
                self._devices.append(device)
                if device.paired:
                    self._paired.add(device.address)
                if device.connected:
                    self._connected.add(device.address)
                if device.trusted:
                    self._trusted.add(device.address)

    def clear_devices(self) -> None:
        """Clear all devices for testing."""
        with self._lock:
            self._devices = []
            self._paired.clear()
            self._connected.clear()
            self._trusted.clear()
