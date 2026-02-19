"""madOS Bluetooth Configuration - Backend factory.

Factory pattern to create backend instances.
Enables dependency injection for testing.
"""

import os


def create_backend():
    """Create backend instance based on environment mode.

    Environment:
        MADOS_BT_CONFIG_MODE: 'production' (default) or 'test'

    Returns:
        Backend instance implementing Bluetooth operations.
    """
    mode = os.environ.get("MADOS_BT_CONFIG_MODE", "production")

    if mode == "test":
        from .mock_backend import MockBluetoothBackend

        return MockBluetoothBackend()

    # Production mode: create a simple wrapper around backend functions
    from . import backend

    class RealBluetoothBackend:
        """Wrapper for real backend functions."""

        def __init__(self):
            # Ensure Bluetooth is ready once
            backend._ensure_bluetooth_ready()

        def check_available(self):
            return backend.check_bluetooth_available()

        def is_powered(self):
            return backend.is_adapter_powered()

        def set_power(self, on):
            return backend.set_adapter_power(on)

        def start_scan(self):
            return backend.start_scan()

        def stop_scan(self):
            return backend.stop_scan()

        def get_devices(self):
            return backend.get_devices()

        def pair_device(self, address):
            return backend.pair_device(address)

        def connect_device(self, address):
            return backend.connect_device(address)

        def disconnect_device(self, address):
            return backend.disconnect_device(address)

        def remove_device(self, address):
            return backend.remove_device(address)

        def trust_device(self, address, trusted=True):
            return backend.trust_device(address, trusted)

        def clear_devices(self):
            # Real backend doesn't track devices, no-op
            pass

    try:
        return RealBluetoothBackend()
    except Exception:
        # Fallback to mock if something fails
        from .mock_backend import MockBluetoothBackend

        return MockBluetoothBackend()
