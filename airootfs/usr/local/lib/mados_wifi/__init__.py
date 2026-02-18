"""madOS WiFi Configuration Utility.

A professional GTK3-based WiFi configuration tool for madOS,
an AI-orchestrated Arch Linux distribution.

Usage:
    from mados_wifi.core import scan_networks, connect_to_network
    
    # Scan for networks
    networks = scan_networks()
    
    # Connect to a network
    result = connect_to_network("MyNetwork", "password123")
"""

__version__ = "1.0.0"
__app_id__ = "mados-wifi"

# Core API (without GTK dependencies)
from .core import (
    WiFiNetwork,
    ConnectionDetails,
    check_wifi_available,
    get_wifi_device,
    scan_networks,
    connect_to_network,
    disconnect_network,
    forget_network,
    get_active_ssid,
    get_active_connection_name,
    get_connection_details,
    get_saved_connections,
    set_auto_connect,
    set_connection_priority,
    set_static_ip,
    set_dhcp,
    set_dns_override,
    set_proxy,
)

# GUI application (requires GTK)
try:
    from .app import WiFiApp
    __all__ = [
        '__version__',
        '__app_id__',
        'WiFiApp',
        'WiFiNetwork',
        'ConnectionDetails',
        'check_wifi_available',
        'get_wifi_device',
        'scan_networks',
        'connect_to_network',
        'disconnect_network',
        'forget_network',
        'get_active_ssid',
        'get_active_connection_name',
        'get_connection_details',
        'get_saved_connections',
        'set_auto_connect',
        'set_connection_priority',
        'set_static_ip',
        'set_dhcp',
        'set_dns_override',
        'set_proxy',
    ]
except ImportError:
    # GTK not available - provide core API only
    __all__ = [
        '__version__',
        '__app_id__',
        'WiFiNetwork',
        'ConnectionDetails',
        'check_wifi_available',
        'get_wifi_device',
        'scan_networks',
        'connect_to_network',
        'disconnect_network',
        'forget_network',
        'get_active_ssid',
        'get_active_connection_name',
        'get_connection_details',
        'get_saved_connections',
        'set_auto_connect',
        'set_connection_priority',
        'set_static_ip',
        'set_dhcp',
        'set_dns_override',
        'set_proxy',
    ]
