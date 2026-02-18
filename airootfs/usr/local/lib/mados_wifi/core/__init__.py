"""Core WiFi management functionality.

This module provides the backend logic for WiFi management without any
GUI dependencies. It can be used from CLI, server applications, or tests.
"""

from .backend import (
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
    # Internal functions for testing
    _run_command,
    _run_iwctl,
    _strip_ansi,
    _parse_iwctl_table,
    _cidr_to_netmask,
    _split_nmcli_line,
)

__all__ = [
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
    '_run_command',
    '_run_iwctl',
    '_strip_ansi',
    '_parse_iwctl_table',
    '_cidr_to_netmask',
    '_split_nmcli_line',
]
