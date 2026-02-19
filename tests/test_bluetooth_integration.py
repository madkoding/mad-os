#!/usr/bin/env python3
"""
Integration tests for Bluetooth workflow.

These tests validate the complete workflow using mock backends
to simulate real operations.
"""

import sys
import os
import types
import unittest
import threading

# Set test mode BEFORE any imports
os.environ["MADOS_BT_CONFIG_MODE"] = "test"

# Mock GTK
gi_mock = types.ModuleType("gi")
gi_mock.require_version = lambda *a, **kw: None
repo_mock = types.ModuleType("gi.repository")


class _StubMeta(type):
    def __getattr__(cls, name):
        return lambda *a, **kw: None


class _StubModule:
    def __getattr__(self, name):
        return _StubMeta(name, (), {})


for name in ("Gtk", "GLib", "Gdk", "Pango"):
    setattr(repo_mock, name, _StubModule())

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "airootfs", "usr", "local", "lib")
)


class TestBluetoothWorkflow(unittest.TestCase):
    """Tests for complete Bluetooth workflow."""

    def test_factory_create_backend(self):
        """Test factory creates backend instance."""
        from mados_bluetooth.factory import create_backend
        from mados_bluetooth.interfaces import BackendInterface

        backend = create_backend()

        self.assertIsNotNone(backend)
        self.assertIsInstance(backend, BackendInterface)

    def test_factory_test_mode(self):
        """Test factory creates mock backend in test mode."""
        from mados_bluetooth.factory import create_backend
        from mados_bluetooth.interfaces import BackendInterface

        backend = create_backend()

        self.assertIsInstance(backend, BackendInterface)

        # Mock backend should have specific test methods
        self.assertTrue(hasattr(backend, "add_device"))
        self.assertTrue(hasattr(backend, "clear_devices"))

    def test_backend_check_available(self):
        """Test backend reports availability."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()
        result = backend.check_available()

        self.assertIn(result, [True, False])

    def test_backend_power_operations(self):
        """Test backend power on/off operations."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()

        # Must be powered to scan
        result = backend.set_power(True)
        self.assertTrue(result)
        self.assertTrue(backend.is_powered())

        result = backend.set_power(False)
        self.assertTrue(result)
        self.assertFalse(backend.is_powered())

    def test_backend_scan_operations(self):
        """Test backend scan start/stop operations."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()
        backend.set_power(True)

        result = backend.start_scan()
        self.assertTrue(result)

        result = backend.stop_scan()
        self.assertTrue(result)


class TestDeviceDiscovery(unittest.TestCase):
    """Tests for device discovery."""

    def test_backend_get_devices_empty(self):
        """Test backend returns empty list when no devices."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()
        backend.set_power(True)
        backend.clear_devices()

        devices = backend.get_devices()

        self.assertIsInstance(devices, list)
        self.assertEqual(len(devices), 0)

    def test_backend_add_and_retrieve_devices(self):
        """Test adding and retrieving devices."""
        from mados_bluetooth.factory import create_backend
        from mados_bluetooth.interfaces import BluetoothDevice

        backend = create_backend()
        backend.set_power(True)
        backend.clear_devices()

        device = BluetoothDevice(
            address="AA:BB:CC:DD:EE:FF",
            name="Test Device",
            paired=False,
            connected=False,
            trusted=False,
        )
        backend.add_device(device)

        devices = backend.get_devices()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(devices[0].name, "Test Device")


class TestPairingConnection(unittest.TestCase):
    """Tests for pairing and connection."""

    def test_pair_device(self):
        """Test pairing a device."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()
        backend.set_power(True)
        backend.clear_devices()

        result = backend.pair_device("AA:BB:CC:DD:EE:FF")

        self.assertEqual(result, "paired")

        devices = backend.get_devices()
        self.assertEqual(len(devices), 1)
        self.assertTrue(devices[0].paired)

    def test_connect_device(self):
        """Test connecting to a paired device."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()
        backend.set_power(True)
        backend.clear_devices()

        backend.pair_device("AA:BB:CC:DD:EE:FF")
        result = backend.connect_device("AA:BB:CC:DD:EE:FF")

        self.assertEqual(result, "connected")

        devices = backend.get_devices()
        self.assertTrue(devices[0].connected)

    def test_disconnect_device(self):
        """Test disconnecting a device."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()
        backend.set_power(True)
        backend.clear_devices()

        backend.pair_device("AA:BB:CC:DD:EE:FF")
        backend.connect_device("AA:BB:CC:DD:EE:FF")
        result = backend.disconnect_device("AA:BB:CC:DD:EE:FF")

        self.assertTrue(result)

        devices = backend.get_devices()
        self.assertFalse(devices[0].connected)

    def test_remove_device(self):
        """Test removing a device."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()
        backend.set_power(True)
        backend.clear_devices()

        backend.pair_device("AA:BB:CC:DD:EE:FF")
        result = backend.remove_device("AA:BB:CC:DD:EE:FF")

        self.assertTrue(result)

        devices = backend.get_devices()
        self.assertEqual(len(devices), 0)

    def test_trust_device(self):
        """Test trusting a device."""
        from mados_bluetooth.factory import create_backend

        backend = create_backend()
        backend.set_power(True)
        backend.clear_devices()

        backend.pair_device("AA:BB:CC:DD:EE:FF")
        backend.trust_device("AA:BB:CC:DD:EE:FF", True)

        devices = backend.get_devices()
        self.assertTrue(devices[0].trusted)

        backend.trust_device("AA:BB:CC:DD:EE:FF", False)
        devices = backend.get_devices()
        self.assertFalse(devices[0].trusted)


if __name__ == "__main__":
    unittest.main()
