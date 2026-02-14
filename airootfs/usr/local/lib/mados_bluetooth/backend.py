"""madOS Bluetooth Configuration - Backend using bluetoothctl.

All Bluetooth operations are performed by invoking bluetoothctl as a
subprocess.  Long-running operations are executed in background threads
to keep the GTK main loop responsive.  UI updates are marshalled back
via GLib.idle_add.
"""

import subprocess
import threading
import re
from dataclasses import dataclass
from typing import List, Optional, Callable

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BluetoothDevice:
    """Represents a discovered or paired Bluetooth device."""
    address: str = ''
    name: str = ''
    paired: bool = False
    connected: bool = False
    trusted: bool = False
    icon: str = ''

    @property
    def display_name(self) -> str:
        """Return a user-friendly display name."""
        return self.name if self.name else self.address


# ---------------------------------------------------------------------------
# Helper: run bluetoothctl
# ---------------------------------------------------------------------------

def _run_btctl(args: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
    """Execute a bluetoothctl command and return the result.

    Args:
        args: Arguments to pass after 'bluetoothctl'.
        timeout: Maximum seconds to wait.

    Returns:
        A subprocess.CompletedProcess instance.
    """
    cmd = ['bluetoothctl'] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_btctl_check(args: List[str], timeout: int = 15) -> str:
    """Run bluetoothctl, raise on failure, and return stdout.

    Args:
        args: Arguments to pass after 'bluetoothctl'.
        timeout: Maximum seconds to wait.

    Returns:
        Stripped stdout string.
    """
    result = _run_btctl(args, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or
            f'bluetoothctl exited with code {result.returncode}'
        )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Helper: ensure Bluetooth hardware is ready
# ---------------------------------------------------------------------------

def _ensure_bluetooth_ready() -> None:
    """Ensure Bluetooth hardware is unblocked and modules are loaded.

    This handles common issues with MT7921 and other combo adapters
    where rfkill blocks Bluetooth on boot or modules don't auto-load.
    """
    try:
        subprocess.run(
            ['sudo', 'rfkill', 'unblock', 'bluetooth'],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Ensure btusb module is loaded (needed for MT7921 BT over USB)
    try:
        subprocess.run(
            ['sudo', 'modprobe', 'btusb'],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Ensure bluetooth service is started
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', '--quiet', 'bluetooth.service'],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            subprocess.run(
                ['sudo', 'systemctl', 'start', 'bluetooth.service'],
                capture_output=True, text=True, timeout=10,
            )
            import time
            time.sleep(3)  # Wait for service and adapter initialization
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


# ---------------------------------------------------------------------------
# Public API -- synchronous (call from threads)
# ---------------------------------------------------------------------------

def check_bluetooth_available() -> bool:
    """Return True if the Bluetooth controller is available."""
    _ensure_bluetooth_ready()
    
    # Try multiple times with delay to handle adapter initialization
    import time
    for attempt in range(3):
        try:
            output = _run_btctl_check(['show'])
            if 'Controller' in output:
                return True
        except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        if attempt < 2:  # Don't sleep on last attempt
            time.sleep(1)
    
    return False


def is_adapter_powered() -> bool:
    """Return True if the Bluetooth adapter is powered on."""
    try:
        output = _run_btctl_check(['show'])
        for line in output.splitlines():
            if 'Powered:' in line:
                return 'yes' in line.lower()
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def set_adapter_power(on: bool) -> bool:
    """Power the Bluetooth adapter on or off.

    Args:
        on: True to power on, False to power off.

    Returns:
        True on success.
    """
    try:
        _run_btctl_check(['power', 'on' if on else 'off'])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def start_scan() -> bool:
    """Start scanning for Bluetooth devices.

    Returns:
        True if scan started successfully.  TimeoutExpired is expected
        because ``bluetoothctl scan on`` keeps running; only a missing
        binary is treated as a real failure.
    """
    try:
        _run_btctl(['scan', 'on'], timeout=3)
        return True
    except subprocess.TimeoutExpired:
        return True  # Timeout is expected for scan
    except FileNotFoundError:
        return False


def stop_scan() -> bool:
    """Stop scanning for Bluetooth devices.

    Returns:
        True if scan stopped successfully.
    """
    try:
        _run_btctl(['scan', 'off'], timeout=3)
        return True
    except subprocess.TimeoutExpired:
        return True
    except FileNotFoundError:
        return False


def get_devices() -> List[BluetoothDevice]:
    """Get all known Bluetooth devices (paired + discovered).

    Returns:
        A list of BluetoothDevice objects sorted with connected first,
        then paired, then discovered.
    """
    devices: List[BluetoothDevice] = []
    seen_addresses = set()

    # Get paired devices
    try:
        output = _run_btctl_check(['devices', 'Paired'])
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        output = ''

    for dev in _parse_device_list(output):
        dev.paired = True
        _fill_device_info(dev)
        seen_addresses.add(dev.address)
        devices.append(dev)

    # Get all discovered devices
    try:
        output = _run_btctl_check(['devices'])
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        output = ''

    for dev in _parse_device_list(output):
        if dev.address not in seen_addresses:
            _fill_device_info(dev)
            devices.append(dev)

    # Sort: connected first, then paired, then by name
    devices.sort(key=lambda d: (not d.connected, not d.paired, d.display_name.lower()))
    return devices


def pair_device(address: str) -> str:
    """Pair with a Bluetooth device.

    Args:
        address: The MAC address of the device.

    Returns:
        A status string: 'paired', 'failed', or an error message.
    """
    try:
        result = _run_btctl(['pair', address], timeout=30)
        output = result.stdout + result.stderr
        if 'Pairing successful' in output or 'AlreadyExists' in output:
            # Also trust the device for auto-reconnect
            _run_btctl(['trust', address], timeout=10)
            return 'paired'
        if 'Failed' in output:
            return 'failed'
        return output.strip() or 'failed'
    except FileNotFoundError:
        return 'bluetoothctl not found'
    except subprocess.TimeoutExpired:
        return 'Pairing timed out'


def connect_device(address: str) -> str:
    """Connect to a paired Bluetooth device.

    Args:
        address: The MAC address of the device.

    Returns:
        A status string: 'connected', 'failed', or an error message.
    """
    try:
        result = _run_btctl(['connect', address], timeout=30)
        output = result.stdout + result.stderr
        if 'Connection successful' in output:
            return 'connected'
        if 'Failed' in output or result.returncode != 0:
            return 'failed'
        return output.strip() or 'failed'
    except FileNotFoundError:
        return 'bluetoothctl not found'
    except subprocess.TimeoutExpired:
        return 'Connection timed out'


def disconnect_device(address: str) -> bool:
    """Disconnect from a Bluetooth device.

    Args:
        address: The MAC address of the device.

    Returns:
        True on success.
    """
    try:
        result = _run_btctl(['disconnect', address], timeout=10)
        return 'Successful' in result.stdout or result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def remove_device(address: str) -> bool:
    """Remove (unpair) a Bluetooth device.

    Args:
        address: The MAC address of the device.

    Returns:
        True on success.
    """
    try:
        result = _run_btctl(['remove', address], timeout=10)
        return 'removed' in result.stdout.lower() or result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def trust_device(address: str, trusted: bool = True) -> bool:
    """Set or unset trust for a Bluetooth device.

    Args:
        address: The MAC address of the device.
        trusted: True to trust, False to untrust.

    Returns:
        True on success.
    """
    cmd = 'trust' if trusted else 'untrust'
    try:
        _run_btctl_check([cmd, address])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Async wrappers -- run in background thread, callback on main thread
# ---------------------------------------------------------------------------

def async_scan(callback: Callable[[List[BluetoothDevice]], None],
               scan_duration: int = 5) -> None:
    """Scan for Bluetooth devices asynchronously.

    Args:
        callback: Called on the GTK main thread with the device list.
        scan_duration: How many seconds to scan before reading results.
    """
    def _worker():
        start_scan()
        import time
        time.sleep(scan_duration)
        stop_scan()
        devices = get_devices()
        GLib.idle_add(callback, devices)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_pair(address: str, callback: Callable[[str], None]) -> None:
    """Pair with a device asynchronously.

    Args:
        address: The MAC address.
        callback: Called on the GTK main thread with the status string.
    """
    def _worker():
        status = pair_device(address)
        GLib.idle_add(callback, status)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_connect(address: str, callback: Callable[[str], None]) -> None:
    """Connect to a device asynchronously.

    Args:
        address: The MAC address.
        callback: Called on the GTK main thread with the status string.
    """
    def _worker():
        status = connect_device(address)
        GLib.idle_add(callback, status)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_disconnect(address: str, callback: Callable[[bool], None]) -> None:
    """Disconnect from a device asynchronously.

    Args:
        address: The MAC address.
        callback: Called on the GTK main thread with success boolean.
    """
    def _worker():
        result = disconnect_device(address)
        GLib.idle_add(callback, result)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_remove(address: str, callback: Callable[[bool], None]) -> None:
    """Remove a device asynchronously.

    Args:
        address: The MAC address.
        callback: Called on the GTK main thread with success boolean.
    """
    def _worker():
        result = remove_device(address)
        GLib.idle_add(callback, result)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_set_power(on: bool, callback: Callable[[bool], None]) -> None:
    """Toggle adapter power asynchronously.

    Args:
        on: True to power on, False to power off.
        callback: Called on the GTK main thread with success boolean.
    """
    def _worker():
        result = set_adapter_power(on)
        GLib.idle_add(callback, result)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_get_adapter_state(
    callback: Callable[[bool, bool], None],
) -> None:
    """Fetch adapter availability and power state asynchronously.

    Args:
        callback: Called on the GTK main thread with (available, powered).
    """
    def _worker():
        available = check_bluetooth_available()
        powered = is_adapter_powered() if available else False
        GLib.idle_add(callback, available, powered)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------

def _parse_device_list(output: str) -> List[BluetoothDevice]:
    """Parse bluetoothctl device list output.

    Expected format: 'Device AA:BB:CC:DD:EE:FF DeviceName'

    Args:
        output: Raw bluetoothctl output.

    Returns:
        A list of BluetoothDevice objects with address and name set.
    """
    devices: List[BluetoothDevice] = []
    for line in output.splitlines():
        match = re.match(r'Device\s+([0-9A-Fa-f:]{17})\s+(.*)', line.strip())
        if match:
            devices.append(BluetoothDevice(
                address=match.group(1),
                name=match.group(2).strip(),
            ))
    return devices


def _fill_device_info(device: BluetoothDevice) -> None:
    """Fill in paired/connected/trusted status from bluetoothctl info.

    Args:
        device: A BluetoothDevice to update in place.
    """
    try:
        output = _run_btctl_check(['info', device.address])
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return

    for line in output.splitlines():
        line = line.strip()
        if line.startswith('Name:'):
            name = line.split(':', 1)[1].strip()
            if name:
                device.name = name
        elif line.startswith('Paired:'):
            device.paired = 'yes' in line.lower()
        elif line.startswith('Connected:'):
            device.connected = 'yes' in line.lower()
        elif line.startswith('Trusted:'):
            device.trusted = 'yes' in line.lower()
        elif line.startswith('Icon:'):
            device.icon = line.split(':', 1)[1].strip()
