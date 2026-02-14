"""madOS WiFi Configuration - Network backend using iwd (iwctl).

All network operations are performed by invoking iwctl as a subprocess.
Long-running operations are executed in background threads to keep the
GTK main loop responsive.  UI updates are marshalled back via
GLib.idle_add.
"""

import subprocess
import threading
import shlex
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Time to wait after triggering a scan for results to be available
SCAN_WAIT_SECONDS = 3

# Signal strength mapping from iwctl stars to percentage
SIGNAL_STRENGTH_MAP = {
    4: 85,  # **** - Excellent
    3: 70,  # ***  - Good
    2: 50,  # **   - Fair
    1: 30,  # *    - Weak
    0: 10,  # No stars - Very weak
}


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
# Helper: run commands
# ---------------------------------------------------------------------------

def _run_command(cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Execute a command and return the CompletedProcess result.

    Args:
        cmd: Command and arguments to execute.
        timeout: Maximum seconds to wait.

    Returns:
        A subprocess.CompletedProcess instance.

    Raises:
        FileNotFoundError: If the command is not installed.
        subprocess.TimeoutExpired: If the command times out.
    """
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_iwctl(args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Execute an iwctl command and return the CompletedProcess result.

    Args:
        args: Arguments to pass after 'iwctl'.
        timeout: Maximum seconds to wait.

    Returns:
        A subprocess.CompletedProcess instance.
    """
    cmd = ['iwctl'] + args
    return _run_command(cmd, timeout=timeout)


def _run_iwctl_check(args: List[str], timeout: int = 30) -> str:
    """Run iwctl, raise on failure, and return stdout.

    Args:
        args: Arguments to pass after 'iwctl'.
        timeout: Maximum seconds to wait.

    Returns:
        Stripped stdout string.

    Raises:
        RuntimeError: If iwctl returns a non-zero exit code.
    """
    result = _run_iwctl(args, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f'iwctl exited with code {result.returncode}')
    return result.stdout.strip()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text.

    Args:
        text: Text that may contain ANSI escape sequences.

    Returns:
        Text with ANSI codes removed.
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def _parse_iwctl_table(output: str) -> List[List[str]]:
    """Parse iwctl's columnar table output into rows of fields.
    
    iwctl outputs tables with columns separated by multiple spaces.
    This function splits each data row into fields using two or more
    consecutive spaces as the delimiter.
    
    Note: This assumes network names and other values don't contain
    multiple consecutive spaces, which is a reasonable assumption for
    typical WiFi network names.
    
    Args:
        output: Raw iwctl output containing a table.
        
    Returns:
        List of tuples: (fields, is_connected), where fields is a list
        of column values and is_connected is True if the row starts with '>'.
    """
    lines = output.splitlines()
    rows = []
    
    in_data = False
    for line in lines:
        # Skip header lines
        if 'Available networks' in line or 'Known Networks' in line or '---' in line:
            continue
        if 'Network name' in line or 'Name' in line:
            in_data = True
            continue
        if not in_data or not line.strip():
            continue
            
        # Check for connected network marker
        is_connected = line.startswith('>')
        if is_connected:
            line = line[1:]
            
        # Split by two or more spaces to separate columns
        parts = [p for p in re.split(r'\s{2,}', line) if p.strip()]
        if parts:
            rows.append((parts, is_connected))
    
    return rows


# ---------------------------------------------------------------------------
# Public API -- synchronous (call from threads)
# ---------------------------------------------------------------------------

def check_wifi_available() -> bool:
    """Return True if at least one WiFi device is available."""
    try:
        result = _run_command(['iw', 'dev'], timeout=10)
        if result.returncode == 0:
            # Look for "Interface" lines which indicate WiFi devices
            for line in result.stdout.splitlines():
                if line.strip().startswith('Interface '):
                    return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def get_wifi_device() -> Optional[str]:
    """Return the first WiFi device name, or None."""
    try:
        result = _run_command(['iw', 'dev'], timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith('Interface '):
                    # Format: "Interface wlan0"
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
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
    device = get_wifi_device()
    if not device:
        return networks

    try:
        # Trigger a scan
        _run_iwctl(['station', device, 'scan'], timeout=10)
        # Wait for scan to complete
        time.sleep(SCAN_WAIT_SECONDS)
        # Get scan results
        output = _run_iwctl_check(['station', device, 'get-networks'], timeout=10)
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return networks

    # Strip ANSI codes and parse table
    output = _strip_ansi(output)
    rows = _parse_iwctl_table(output)

    for parts, is_connected in rows:
        if len(parts) < 2:
            continue

        # Parse columns: Network name, Security, Signal
        # Signal is represented as stars (*, **, ***, ****)
        signal_str = parts[-1].strip()
        security = parts[-2].strip() if len(parts) >= 2 else ''
        ssid_parts = parts[:-2] if len(parts) > 2 else [parts[0]]
        ssid = ' '.join(p.strip() for p in ssid_parts).strip()

        if not ssid:
            ssid = '(Hidden)'

        # Convert signal stars to percentage
        star_count = signal_str.count('*')
        signal = SIGNAL_STRENGTH_MAP.get(star_count, 10)

        # Map security types
        if security.lower() == 'open':
            security_display = 'Open'
        elif security.lower() == 'psk':
            security_display = 'WPA/WPA2'
        else:
            security_display = security

        networks.append(WiFiNetwork(
            ssid=ssid,
            bssid='',  # iwd doesn't show BSSID in get-networks
            signal=signal,
            security=security_display,
            frequency='',
            channel='',
            rate='',
            mode='',
            in_use=is_connected,
        ))

    # Sort by signal descending; connected network first
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
    device = get_wifi_device()
    if not device:
        return 'No WiFi device found'

    try:
        if password:
            # Connect with password
            args = ['--passphrase', password, 'station', device, 'connect', ssid]
        else:
            # Connect without password (open network)
            args = ['station', device, 'connect', ssid]

        result = _run_iwctl(args, timeout=45)
    except FileNotFoundError:
        return 'iwctl not found'
    except subprocess.TimeoutExpired:
        return 'Connection timed out'

    if result.returncode == 0:
        return 'connected'

    stderr = result.stderr.strip().lower()
    # Check for common error messages
    if 'passphrase' in stderr or 'authentication' in stderr or 'psk' in stderr:
        return 'wrong_password'
    if 'not found' in stderr:
        return 'Network not found'

    return result.stderr.strip() or 'Connection failed'


def disconnect_network(connection_name: Optional[str] = None) -> bool:
    """Disconnect the active WiFi connection.

    Args:
        connection_name: Ignored for iwd (kept for API compatibility).

    Returns:
        True on success.
    """
    device = get_wifi_device()
    if not device:
        return False

    try:
        _run_iwctl_check(['station', device, 'disconnect'])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def forget_network(connection_name: str) -> bool:
    """Remove a saved connection profile.

    Args:
        connection_name: The SSID to forget.

    Returns:
        True on success.
    """
    try:
        _run_iwctl_check(['known-networks', connection_name, 'forget'])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_active_connection_name() -> Optional[str]:
    """Return the name of the currently active WiFi connection, or None."""
    return get_active_ssid()


def get_active_ssid() -> Optional[str]:
    """Return the SSID of the currently active WiFi connection, or None."""
    device = get_wifi_device()
    if not device:
        return None

    try:
        output = _run_iwctl_check(['station', device, 'show'])
        output = _strip_ansi(output)

        # Parse the output
        # Format:
        #                              Station: wlan0
        # --------------------------------------------------------
        #   Settable  Property            Value
        # --------------------------------------------------------
        #             Scanning            no
        #             State               connected
        #             Connected network   MyNetwork

        for line in output.splitlines():
            # Look for "Connected network" line using regex to extract
            # the value reliably, even if the SSID contains "network"
            match = re.search(r'Connected network\s{2,}(.+)', line)
            if match:
                ssid = match.group(1).strip()
                if ssid:
                    return ssid
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_connection_details() -> Optional[ConnectionDetails]:
    """Fetch detailed information about the active WiFi connection.

    Returns:
        A ConnectionDetails object, or None if there is no active
        WiFi connection.
    """
    ssid = get_active_ssid()
    if not ssid:
        return None

    device = get_wifi_device()
    if not device:
        return None

    details = ConnectionDetails(connection_id=ssid, ssid=ssid, device=device)

    # Get station details from iwctl
    try:
        output = _run_iwctl_check(['station', device, 'show'])
        output = _strip_ansi(output)

        for line in output.splitlines():
            line = line.strip()
            if 'State' in line and 'connected' not in line.lower():
                return None  # Not connected
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Get IP address info
    try:
        result = _run_command(['ip', '-4', 'addr', 'show', device], timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith('inet '):
                    # Format: inet 192.168.1.100/24 brd 192.168.1.255 scope global wlan0
                    parts = line.split()
                    if len(parts) >= 2:
                        addr_with_cidr = parts[1]
                        if '/' in addr_with_cidr:
                            try:
                                addr, cidr = addr_with_cidr.split('/', 1)
                                details.ip4_address = addr
                                details.ip4_subnet = _cidr_to_netmask(cidr)
                            except ValueError:
                                pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Get gateway
    try:
        result = _run_command(['ip', 'route', 'show', 'default'], timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                # Format: default via 192.168.1.1 dev wlan0 proto dhcp src 192.168.1.100 metric 600
                if 'default via' in line and device in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        details.ip4_gateway = parts[2]
                    break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Get DNS servers from resolv.conf
    try:
        with open('/etc/resolv.conf', 'r') as f:
            dns_servers = []
            for line in f:
                line = line.strip()
                if line.startswith('nameserver '):
                    parts = line.split()
                    if len(parts) >= 2:
                        dns_servers.append(parts[1])
            if dns_servers:
                details.ip4_dns = ', '.join(dns_servers)
    except (IOError, FileNotFoundError):
        pass

    # Get MAC address
    try:
        result = _run_command(['ip', 'link', 'show', device], timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith('link/ether '):
                    parts = line.split()
                    if len(parts) >= 2:
                        details.mac_address = parts[1]
                    break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check if auto-connect is enabled for this network
    try:
        output = _run_iwctl_check(['known-networks', ssid, 'show'])
        output = _strip_ansi(output)
        for line in output.splitlines():
            if 'AutoConnect' in line:
                details.auto_connect = 'yes' in line.lower()
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return details


def get_saved_connections() -> List[str]:
    """Return a list of saved WiFi connection names."""
    connections: List[str] = []
    try:
        output = _run_iwctl_check(['known-networks', 'list'])
        output = _strip_ansi(output)

        # Parse using helper function
        rows = _parse_iwctl_table(output)
        for parts, _ in rows:
            if len(parts) >= 1:
                ssid = parts[0].strip()
                if ssid:
                    connections.append(ssid)
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return connections


def set_auto_connect(connection_name: str, enabled: bool) -> bool:
    """Enable or disable auto-connect for a saved connection.

    Args:
        connection_name: The SSID.
        enabled: Whether auto-connect should be on.

    Returns:
        True on success.
    """
    val = 'yes' if enabled else 'no'
    try:
        _run_iwctl_check(['known-networks', connection_name, 'set-property',
                          'AutoConnect', val])
        return True
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def set_connection_priority(connection_name: str, priority: int) -> bool:
    """Set the auto-connect priority for a saved connection.

    This is not supported by iwd directly.

    Args:
        connection_name: The SSID.
        priority: Integer priority (higher = preferred).

    Returns:
        False (not supported by iwd).
    """
    return False


def set_static_ip(connection_name: str, ip_address: str, gateway: str,
                  dns: str = '') -> bool:
    """Configure a connection for static IP addressing.

    This requires modifying systemd-networkd configuration, which is
    not implemented in this backend.

    Args:
        connection_name: The SSID.
        ip_address: IPv4 address in CIDR notation (e.g. '192.168.1.100/24').
        gateway: Gateway address.
        dns: Space-separated DNS servers.

    Returns:
        False (not supported by this backend).
    """
    return False


def set_dhcp(connection_name: str) -> bool:
    """Switch a connection back to DHCP.

    This requires modifying systemd-networkd configuration, which is
    not implemented in this backend.

    Args:
        connection_name: The SSID.

    Returns:
        False (not supported by this backend).
    """
    return False


def set_dns_override(connection_name: str, dns_servers: str) -> bool:
    """Override DNS servers for a connection.

    This requires modifying systemd-networkd or resolv.conf configuration,
    which is not implemented in this backend.

    Args:
        connection_name: The SSID.
        dns_servers: Space-separated DNS server addresses.

    Returns:
        False (not supported by this backend).
    """
    return False


def set_proxy(connection_name: str, proxy_host: str, proxy_port: str) -> bool:
    """Configure HTTP proxy for a connection.

    This is not supported by iwd directly.

    Args:
        connection_name: The SSID.
        proxy_host: The proxy hostname or IP.
        proxy_port: The proxy port.

    Returns:
        False (not supported by this backend).
    """
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

    This function is kept for backward compatibility and is tested
    separately. While not used by the iwd backend, it's maintained
    to preserve the existing test suite structure.

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
