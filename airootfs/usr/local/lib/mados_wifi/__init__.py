"""madOS WiFi Configuration Utility.

A professional GTK3-based WiFi configuration tool for madOS,
an AI-orchestrated Arch Linux distribution. Uses iwd (iwctl) 
as the backend for all wireless network operations.
"""

__version__ = "1.0.0"
__app_id__ = "mados-wifi"

# Export main application class
from .app import WiFiApp

# Export backend data classes and functions
from .backend import (
    WiFiNetwork,
    ConnectionDetails,
    check_wifi_available,
    get_wifi_device,
    scan_networks,
    connect_to_network,
    disconnect_network,
    forget_network,
    get_active_connection_name,
    get_active_ssid,
    get_connection_details,
    get_saved_connections,
    set_auto_connect,
    set_connection_priority,
    set_static_ip,
    set_dhcp,
    set_dns_override,
    set_proxy,
    async_scan,
    async_connect,
    async_disconnect,
    async_forget,
    async_get_details,
)

__all__ = [
    # Metadata
    '__version__',
    '__app_id__',
    # Main application
    'WiFiApp',
    # Data classes
    'WiFiNetwork',
    'ConnectionDetails',
    # Synchronous backend functions
    'check_wifi_available',
    'get_wifi_device',
    'scan_networks',
    'connect_to_network',
    'disconnect_network',
    'forget_network',
    'get_active_connection_name',
    'get_active_ssid',
    'get_connection_details',
    'get_saved_connections',
    'set_auto_connect',
    'set_connection_priority',
    'set_static_ip',
    'set_dhcp',
    'set_dns_override',
    'set_proxy',
    # Asynchronous backend functions
    'async_scan',
    'async_connect',
    'async_disconnect',
    'async_forget',
    'async_get_details',
]
