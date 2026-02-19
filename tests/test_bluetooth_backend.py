#!/usr/bin/env python3
"""
Unit tests for Bluetooth backend (no GTK required).

These tests validate the backend implementation without requiring
real Bluetooth hardware or calling bluetoothctl subprocess.
"""

import sys
import os
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "airootfs", "usr", "local", "lib")
)

from mados_bluetooth.interfaces import BluetoothDevice


class TestBluetoothDevice(unittest.TestCase):
    """Tests for BluetoothDevice dataclass."""

    def test_display_name_with_name(self):
        """display_name should return name when present."""
        device = BluetoothDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device")
        self.assertEqual(device.display_name, "Test Device")

    def test_display_name_fallback(self):
        """display_name should fall back to address when name is empty."""
        device = BluetoothDevice(address="AA:BB:CC:DD:EE:FF", name="")
        self.assertEqual(device.display_name, "AA:BB:CC:DD:EE:FF")

    def test_all_fields(self):
        """BluetoothDevice should accept all fields."""
        device = BluetoothDevice(
            address="AA:BB:CC:DD:EE:FF",
            name="Test Device",
            paired=True,
            connected=False,
            trusted=True,
            icon="audio-headphones",
        )
        self.assertEqual(device.address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(device.name, "Test Device")
        self.assertTrue(device.paired)
        self.assertFalse(device.connected)
        self.assertTrue(device.trusted)
        self.assertEqual(device.icon, "audio-headphones")


if __name__ == "__main__":
    unittest.main()
