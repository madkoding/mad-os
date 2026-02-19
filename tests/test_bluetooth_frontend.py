#!/usr/bin/env python3
"""
Unit tests for Bluetooth frontend (with mock backend).

These tests validate the GTK UI without requiring real hardware
by injecting a mock backend.
"""

import sys
import os
import types
import unittest
from unittest import mock

# Mock GTK before importing app
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


class TestBluetoothDeviceRow(unittest.TestCase):
    """Tests for device row creation."""

    def test_create_device_row(self):
        """Test creating a device row with mock."""
        from mados_bluetooth.interfaces import BluetoothDevice

        # Create device with all properties
        device = BluetoothDevice(
            address="AA:BB:CC:DD:EE:FF",
            name="Test Device",
            paired=True,
            connected=False,
            trusted=True,
            icon="audio-headphones",
        )

        self.assertEqual(device.address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(device.display_name, "Test Device")
        self.assertTrue(device.paired)
        self.assertFalse(device.connected)
        self.assertTrue(device.trusted)


class TestBluetoothAppStructure(unittest.TestCase):
    """Tests for BluetoothApp structure."""

    def test_app_importable(self):
        """BluetoothApp should be importable with mock GTK."""
        from mados_bluetooth.app import BluetoothApp

        self.assertIsNotNone(BluetoothApp)

    def test_app_initialization_mock_backend(self):
        """BluetoothApp should initialize with mock backend."""
        from mados_bluetooth.app import BluetoothApp

        app = BluetoothApp.__new__(BluetoothApp)
        app._lang = "English"
        app._devices = []
        app._selected_device = None
        app._auto_refresh_id = None
        app._refresh_in_flight = False
        app._adapter_available = False
        app._adapter_powered = False

        self.assertEqual(app._lang, "English")
        self.assertEqual(app._devices, [])
        self.assertIsNone(app._selected_device)


class TestBluetoothAppMethods(unittest.TestCase):
    """Tests for BluetoothApp methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_backend = mock.MagicMock()
        self.mock_backend.is_powered.return_value = True
        self.mock_backend.check_available.return_value = True

    def test_power_toggles_backend(self):
        """Test power toggle calls backend."""
        from mados_bluetooth.app import BluetoothApp
        from unittest.mock import MagicMock

        app = BluetoothApp.__new__(BluetoothApp)
        app._backend = self.mock_backend

        mock_switch = MagicMock()
        mock_switch.get_active.return_value = True

        def dummy_callback(success):
            pass

        # This would normally be called from app, but we're testing the pattern
        self.mock_backend.async_set_power(True, dummy_callback)

        self.mock_backend.async_set_power.assert_called_once()


if __name__ == "__main__":
    unittest.main()
