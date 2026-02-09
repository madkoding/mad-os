"""madOS WiFi Configuration - Network backend using NetworkManager (nmcli).

All network operations are performed by invoking nmcli as a subprocess.
Long-running operations are executed in background threads to keep the
GTK main loop responsive.  UI updates are marshalled back via
GLib.idle_add.
"""

import subprocess
import threading
import shlex
import re
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WiFiNetwork:
    """Represents a single WiFi network visible from a scan."""
    ssid: str = ''
    bssid: str = ''
    signal: int = 0
    security: str = ''
    frequency: str = ''
    channel: str = ''
    rate: str = ''
    mode: str = ''
    in_use: bool = False

    @property
    def signal_category(self) -> str:
        """Return a human-readable signal quality category."""
        if self.signal >= 80:
            return 'excellent'
        elif self.signal >= 60:
            return 'good'
        elif self.signal >= 40:
            return 'fair'
        elif self.signal >= 20:
            return 'weak'
        return 'none'

    @property
    def signal_bars(self) -> str:
        """Return a Unicode bar representation of signal strength."""
        if self.signal >= 80:
            return '\u2588\u2588\u2588\u2588'   # full blocks
        elif self.signal >= 60:
            return '\u2588\u2588\u2588\u2591'
        elif self.signal >= 40:
            return '\u2588\u2588\u2591\u2591'
        elif self.signal >= 20:
            return '\u2588\u2591\u2591\u2591'
        return '\u2591\u2591\u2591\u2591'


@dataclass
class ConnectionDetails:
    """Detailed information about the active WiFi connection."""
    ssid: str = ''
    bssid: str = ''
    signal: int = 0
    security: str = ''
    ip4_address: str = ''
    ip4_gateway: str = ''
    ip4_subnet: str = ''
    ip4_dns: str = ''
    ip6_address: str = ''
    mac_address: str = ''
    frequency: str = ''
    channel: str = ''
    link_speed: str = ''
    connection_id: str = ''
    device: str = ''
    timestamp: str = ''
    auto_connect: bool = True


# ---------------------------------------------------------------------------
# Helper: run nmcli
# ---------------------------------------------------------------------------

def _run_nmcli(args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Execute an nmcli command and return the CompletedProcess result.

    Args:
        args: Arguments to pass after 'nmcli'.
        timeout: Maximum seconds to wait.

    Returns:
        A subprocess.CompletedProcess instance.

    Raises:
        FileNotFoundError: If nmcli is not installed.
        subprocess.TimeoutExpired: If the command times out.
    """
    cmd = ['nmcli'] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_nmcli_check(args: List[str], timeout: int = 30) -> str:
    """Run nmcli, raise on failure, and return stdout.

    Args:
        args: Arguments to pass after 'nmcli'.
        timeout: Maximum seconds to wait.

    Returns:
        Stripped stdout string.

    Raises:
        RuntimeError: If nmcli returns a non-zero exit code.
    """
    result = _run_nmcli(args, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f'nmcli exited with code {result.returncode}')
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Public API -- synchronous (call from threads)
# ---------------------------------------------------------------------------

def check_wifi_available() -> bool:
    """Return True if at least one WiFi device is managed by NetworkManager."""
    try:
        result = _run_nmcli(['-t', '-f', 'TYPE,STATE', 'device'])
        for line in result.stdout.strip().splitlines():
            parts = line.split(':')
            if len(parts) >= 2 and parts[0] == 'wifi':
                return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def get_wifi_device() -> Optional[str]:
    """Return the first WiFi device name, or None."""
    try:
        result = _run_nmcli(['-t', '-f', 'DEVICE,TYPE', 'device'])
        for line in result.stdout.strip().splitlines():
            parts = line.split(':')
            if len(parts) >= 2 and parts[1] == 'wifi':
                return parts[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def scan_networks() -> List[WiFiNetwork]:
    """Scan for available WiFi networks and return a sorted list.

    Networks are sorted by signal strength (strongest first).
    Duplicate SSIDs (multiple BSSIDs) are kept so the user
    can see all access points.

    Returns:
        A list of WiFiNetwork objects.
    """
    networks: List[WiFiNetwork] = []

    try:
        output = _run_nmcli_check([
            '-t', '-f',
            'IN-USE,SSID,BSSID,SIGNAL,SECURITY,FREQ,CHAN,RATE,MODE',
            'dev', 'wifi', 'list', '--rescan', 'yes',
        ])
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return networks

    for line in output.splitlines():
        # nmcli -t uses ':' as delimiter.  SSIDs may contain colons
        # that are escaped as '\:'.  We split carefully.
        parts = _split_nmcli_line(line)
        if len(parts) < 9:
            continue

        in_use = parts[0].strip() == '*'
        ssid = parts[1].strip()
        if not ssid:
            # Hidden network with no SSID broadcast
            ssid = '(Hidden)'

        try:
            signal = int(parts[3].strip())
        except ValueError:
            signal = 0

        networks.append(WiFiNetwork(
            ssid=ssid,
            bssid=parts[2].strip(),
            signal=signal,
            security=parts[4].strip() if parts[4].strip() else 'Open',
            frequency=parts[5].strip(),
            channel=parts[6].strip(),
            rate=parts[7].strip(),
            mode=parts[8].strip(),
            in_use=in_use,
        ))

    # Sort by signal descending; connected network first.
    networks.sort(key=lambda n: (n.in_use, n.signal), reverse=True)
    return networks


def connect_to_network(ssid: str, password: Optional[str] = None,
                       hidden: bool = False) -> str:
    """Attempt to connect to a WiFi network.

    Args:
        ssid: The network SSID to connect to.
        password: The network password (None for open networks).
        hidden: Whether the network is hidden (not broadcasting SSID).

    Returns:
        A status string: 'connected', 'wrong_password', or an error message.
    """
    args = ['dev', 'wifi', 'connect', ssid]
    if password:
        args += ['password', password]
    if hidden:
        args += ['hidden', 'yes']

    try:
        result = _run_nmcli(args, timeout=45)
    except FileNotFoundError:
        return 'nmcli not found'
    except subprocess.TimeoutExpired:
        return 'Connection timed out'

    if result.returncode == 0:
        return 'connected'

    stderr = result.stderr.strip().lower()
    if 'secrets were required' in stderr or 'no suitable' in stderr:
        return 'wrong_password'
    return result.stderr.strip() or 'Connection failed'


def disconnect_network(connection_name: Optional[str] = None) -> bool:
    """Disconnect the active WiFi connection.

    Args:
        connection_name: The connection name/id.  If None, disconnects
            the wifi device directly.

    Returns:
        True on success.
    """
    try:
        if connection_name:
            _run_nmcli_check(['con', 'down', connection_name])
        else:
            device = get_wifi_device()
            if device:
                _run_nmcli_check(['dev', 'disconnect', device])
            else:
                return False
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def forget_network(connection_name: str) -> bool:
    """Remove a saved connection profile.

    Args:
        connection_name: The connection name/id to delete.

    Returns:
        True on success.
    """
    try:
        _run_nmcli_check(['con', 'delete', connection_name])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_active_connection_name() -> Optional[str]:
    """Return the name of the currently active WiFi connection, or None."""
    try:
        output = _run_nmcli_check(['-t', '-f', 'NAME,TYPE', 'con', 'show', '--active'])
        for line in output.splitlines():
            parts = line.split(':')
            if len(parts) >= 2 and '802-11-wireless' in parts[1]:
                return parts[0]
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_active_ssid() -> Optional[str]:
    """Return the SSID of the currently active WiFi connection, or None."""
    device = get_wifi_device()
    if not device:
        return None
    try:
        output = _run_nmcli_check([
            '-t', '-f', 'GENERAL.CONNECTION', 'dev', 'show', device,
        ])
        for line in output.splitlines():
            key_val = line.split(':', 1)
            if len(key_val) == 2:
                val = key_val[1].strip()
                if val and val != '--':
                    return val
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_connection_details() -> Optional[ConnectionDetails]:
    """Fetch detailed information about the active WiFi connection.

    Returns:
        A ConnectionDetails object, or None if there is no active
        WiFi connection.
    """
    con_name = get_active_connection_name()
    if not con_name:
        return None

    details = ConnectionDetails(connection_id=con_name)

    # Active connection details from the connection profile
    try:
        output = _run_nmcli_check([
            '-t', '-f',
            'connection.id,connection.autoconnect,connection.timestamp,'
            '802-11-wireless.ssid,802-11-wireless-security.key-mgmt,'
            'ipv4.addresses,ipv4.gateway,ipv4.dns,ipv6.addresses',
            'con', 'show', con_name,
        ])
        _parse_connection_fields(output, details)
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Runtime / device-level details
    device = get_wifi_device()
    if device:
        try:
            output = _run_nmcli_check([
                '-t', '-f',
                'GENERAL.HWADDR,WIRED-PROPERTIES,'
                'IP4.ADDRESS,IP4.GATEWAY,IP4.DNS,'
                'IP6.ADDRESS,'
                'WIFI.SSID,WIFI.BSSID,WIFI.FREQ,WIFI.CHAN,'
                'WIFI.RATE,WIFI.SIGNAL,WIFI.SECURITY',
                'dev', 'show', device,
            ])
            _parse_device_fields(output, details)
        except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return details


def get_saved_connections() -> List[str]:
    """Return a list of saved WiFi connection names."""
    connections: List[str] = []
    try:
        output = _run_nmcli_check(['-t', '-f', 'NAME,TYPE', 'con', 'show'])
        for line in output.splitlines():
            parts = line.split(':')
            if len(parts) >= 2 and '802-11-wireless' in parts[1]:
                connections.append(parts[0])
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return connections


def set_auto_connect(connection_name: str, enabled: bool) -> bool:
    """Enable or disable auto-connect for a saved connection.

    Args:
        connection_name: The connection name/id.
        enabled: Whether auto-connect should be on.

    Returns:
        True on success.
    """
    val = 'yes' if enabled else 'no'
    try:
        _run_nmcli_check(['con', 'modify', connection_name,
                          'connection.autoconnect', val])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def set_connection_priority(connection_name: str, priority: int) -> bool:
    """Set the auto-connect priority for a saved connection.

    Args:
        connection_name: The connection name/id.
        priority: Integer priority (higher = preferred).

    Returns:
        True on success.
    """
    try:
        _run_nmcli_check(['con', 'modify', connection_name,
                          'connection.autoconnect-priority', str(priority)])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def set_static_ip(connection_name: str, ip_address: str, gateway: str,
                  dns: str = '') -> bool:
    """Configure a connection for static IP addressing.

    Args:
        connection_name: The connection name/id.
        ip_address: IPv4 address in CIDR notation (e.g. '192.168.1.100/24').
        gateway: Gateway address.
        dns: Space-separated DNS servers.

    Returns:
        True on success.
    """
    try:
        _run_nmcli_check(['con', 'modify', connection_name,
                          'ipv4.method', 'manual',
                          'ipv4.addresses', ip_address,
                          'ipv4.gateway', gateway])
        if dns:
            _run_nmcli_check(['con', 'modify', connection_name,
                              'ipv4.dns', dns])
        # Re-apply the connection so settings take effect
        _run_nmcli(['con', 'up', connection_name])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def set_dhcp(connection_name: str) -> bool:
    """Switch a connection back to DHCP.

    Args:
        connection_name: The connection name/id.

    Returns:
        True on success.
    """
    try:
        _run_nmcli_check(['con', 'modify', connection_name,
                          'ipv4.method', 'auto',
                          'ipv4.addresses', '',
                          'ipv4.gateway', '',
                          'ipv4.dns', ''])
        _run_nmcli(['con', 'up', connection_name])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def set_dns_override(connection_name: str, dns_servers: str) -> bool:
    """Override DNS servers for a connection.

    Args:
        connection_name: The connection name/id.
        dns_servers: Space-separated DNS server addresses.

    Returns:
        True on success.
    """
    try:
        _run_nmcli_check(['con', 'modify', connection_name,
                          'ipv4.dns', dns_servers,
                          'ipv4.ignore-auto-dns', 'yes'])
        _run_nmcli(['con', 'up', connection_name])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def set_proxy(connection_name: str, proxy_host: str, proxy_port: str) -> bool:
    """Configure HTTP proxy for a connection.

    NetworkManager uses the proxy.method and proxy.pac-url or
    environment variables.  For simplicity we use connection-level
    proxy settings.

    Args:
        connection_name: The connection name/id.
        proxy_host: The proxy hostname or IP.
        proxy_port: The proxy port.

    Returns:
        True on success.
    """
    try:
        if proxy_host and proxy_port:
            pac_url = f'http://{proxy_host}:{proxy_port}'
            _run_nmcli_check(['con', 'modify', connection_name,
                              'proxy.method', 'auto',
                              'proxy.pac-url', pac_url])
        else:
            _run_nmcli_check(['con', 'modify', connection_name,
                              'proxy.method', 'none'])
        _run_nmcli(['con', 'up', connection_name])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Async wrappers -- run in background thread, callback on main thread
# ---------------------------------------------------------------------------

def async_scan(callback: Callable[[List[WiFiNetwork]], None]) -> None:
    """Scan for WiFi networks asynchronously.

    Args:
        callback: Called on the GTK main thread with the scan results.
    """
    def _worker():
        networks = scan_networks()
        GLib.idle_add(callback, networks)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_connect(ssid: str, password: Optional[str],
                  callback: Callable[[str], None],
                  hidden: bool = False) -> None:
    """Connect to a network asynchronously.

    Args:
        ssid: The network SSID.
        password: The password (or None for open).
        callback: Called on the GTK main thread with the status string.
        hidden: Whether this is a hidden network.
    """
    def _worker():
        status = connect_to_network(ssid, password, hidden=hidden)
        GLib.idle_add(callback, status)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_disconnect(callback: Callable[[bool], None],
                     connection_name: Optional[str] = None) -> None:
    """Disconnect from the current network asynchronously.

    Args:
        callback: Called on the GTK main thread with success boolean.
        connection_name: Optional connection name.
    """
    def _worker():
        result = disconnect_network(connection_name)
        GLib.idle_add(callback, result)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_forget(connection_name: str,
                 callback: Callable[[bool], None]) -> None:
    """Forget (delete) a saved connection asynchronously.

    Args:
        connection_name: The connection name/id.
        callback: Called on the GTK main thread with success boolean.
    """
    def _worker():
        result = forget_network(connection_name)
        GLib.idle_add(callback, result)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def async_get_details(callback: Callable[[Optional[ConnectionDetails]], None]) -> None:
    """Fetch connection details asynchronously.

    Args:
        callback: Called on the GTK main thread with ConnectionDetails or None.
    """
    def _worker():
        details = get_connection_details()
        GLib.idle_add(callback, details)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------

def _split_nmcli_line(line: str) -> List[str]:
    """Split an nmcli terse-mode output line on unescaped colons.

    nmcli escapes literal colons in values as '\\:'.  This function
    splits only on unescaped colons and then unescapes the results.

    Args:
        line: A single line of nmcli -t output.

    Returns:
        A list of field values.
    """
    parts: List[str] = []
    current: List[str] = []
    i = 0
    while i < len(line):
        if line[i] == '\\' and i + 1 < len(line) and line[i + 1] == ':':
            current.append(':')
            i += 2
        elif line[i] == ':':
            parts.append(''.join(current))
            current = []
            i += 1
        else:
            current.append(line[i])
            i += 1
    parts.append(''.join(current))
    return parts


def _parse_connection_fields(output: str, details: ConnectionDetails) -> None:
    """Parse nmcli connection show output into a ConnectionDetails object."""
    for line in output.splitlines():
        key_val = line.split(':', 1)
        if len(key_val) != 2:
            continue
        key = key_val[0].strip()
        val = key_val[1].strip()
        if not val or val == '--':
            continue

        if key == 'connection.id':
            details.connection_id = val
        elif key == 'connection.autoconnect':
            details.auto_connect = val.lower() == 'yes'
        elif key == 'connection.timestamp':
            details.timestamp = val
        elif key == '802-11-wireless.ssid':
            details.ssid = val
        elif key == '802-11-wireless-security.key-mgmt':
            details.security = val
        elif key == 'ipv4.addresses':
            details.ip4_address = val
        elif key == 'ipv4.gateway':
            details.ip4_gateway = val
        elif key == 'ipv4.dns':
            details.ip4_dns = val
        elif key == 'ipv6.addresses':
            details.ip6_address = val


def _parse_device_fields(output: str, details: ConnectionDetails) -> None:
    """Parse nmcli device show output into a ConnectionDetails object."""
    for line in output.splitlines():
        key_val = line.split(':', 1)
        if len(key_val) != 2:
            continue
        key = key_val[0].strip()
        val = key_val[1].strip()
        if not val or val == '--':
            continue

        if key == 'GENERAL.HWADDR':
            details.mac_address = val
        elif key.startswith('IP4.ADDRESS'):
            if not details.ip4_address:
                details.ip4_address = val
            # Extract subnet from CIDR notation
            if '/' in val:
                cidr = val.split('/')[1]
                details.ip4_subnet = _cidr_to_netmask(cidr)
        elif key.startswith('IP4.GATEWAY'):
            if not details.ip4_gateway:
                details.ip4_gateway = val
        elif key.startswith('IP4.DNS'):
            if details.ip4_dns:
                details.ip4_dns += ', ' + val
            else:
                details.ip4_dns = val
        elif key.startswith('IP6.ADDRESS'):
            if not details.ip6_address:
                details.ip6_address = val
        elif key == 'WIFI.SSID':
            details.ssid = val
        elif key == 'WIFI.BSSID':
            details.bssid = val
        elif key == 'WIFI.FREQ':
            details.frequency = val
        elif key == 'WIFI.CHAN':
            details.channel = val
        elif key == 'WIFI.RATE':
            details.link_speed = val
        elif key == 'WIFI.SIGNAL':
            try:
                details.signal = int(val)
            except ValueError:
                pass
        elif key == 'WIFI.SECURITY':
            details.security = val


def _cidr_to_netmask(cidr_str: str) -> str:
    """Convert a CIDR prefix length to a dotted-decimal subnet mask.

    Args:
        cidr_str: The prefix length as a string (e.g. '24').

    Returns:
        The subnet mask (e.g. '255.255.255.0').
    """
    try:
        cidr = int(cidr_str)
    except ValueError:
        return cidr_str

    mask = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
    return '.'.join(str((mask >> (8 * i)) & 0xFF) for i in range(3, -1, -1))
