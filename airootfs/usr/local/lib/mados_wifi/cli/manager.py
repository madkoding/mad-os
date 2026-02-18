"""WiFi Manager CLI - Core logic without GTK."""

from ..core import (
    scan_networks,
    connect_to_network,
    disconnect_network,
    forget_network,
    get_active_ssid,
    get_saved_connections,
    get_wifi_device,
)


class WiFiManager:
    """WiFi management CLI with core logic only.
    
    This class provides methods for WiFi management without any GUI dependencies.
    It can be used in scripts, server applications, or headless environments.
    """
    
    def __init__(self):
        """Initialize the WiFi manager."""
        self._last_scan = None
        self._last_scan_time = None
    
    def is_wifi_available(self):
        """Check if WiFi hardware is available."""
        from ..core import check_wifi_available
        return check_wifi_available()
    
    def get_device(self):
        """Get the first WiFi device name."""
        return get_wifi_device()
    
    def scan(self, force=False):
        """Scan for available networks.
        
        Args:
            force: If True, force a new scan. Otherwise use cached results.
        
        Returns:
            List of WiFiNetwork objects.
        """
        self._last_scan = scan_networks()
        return self._last_scan
    
    def get_networks(self):
        """Get cached network list from last scan."""
        return self._last_scan or []
    
    def connect(self, ssid, password=None):
        """Connect to a WiFi network.
        
        Args:
            ssid: Network SSID.
            password: Network password (None for open networks).
        
        Returns:
            Status string: 'connected', 'wrong_password', or error message.
        """
        return connect_to_network(ssid, password)
    
    def disconnect(self):
        """Disconnect from current network."""
        return disconnect_network()
    
    def forget(self, ssid):
        """Remove a saved network.
        
        Args:
            ssid: Network SSID to forget.
        
        Returns:
            True on success, False otherwise.
        """
        return forget_network(ssid)
    
    def get_connected_ssid(self):
        """Get the currently connected network SSID."""
        return get_active_ssid()
    
    def get_saved_networks(self):
        """Get list of saved network SSIDs."""
        return get_saved_connections()
    
    def get_info(self):
        """Get connection details for the current connection."""
        from ..core import get_connection_details
        return get_connection_details()
