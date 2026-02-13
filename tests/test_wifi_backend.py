#!/usr/bin/env python3
"""
Tests for madOS WiFi backend (network management via nmcli).

Validates data classes, parsing helpers, and network operations by mocking
subprocess calls to nmcli.  These tests run in CI without requiring actual
WiFi hardware or NetworkManager.
"""

import sys
import os
import types
import unittest
from unittest.mock import patch, MagicMock
import subprocess

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so WiFi modules can be imported headlessly.
# ---------------------------------------------------------------------------
gi_mock = types.ModuleType("gi")
gi_mock.require_version = lambda *a, **kw: None

repo_mock = types.ModuleType("gi.repository")


class _StubMeta(type):
    def __getattr__(cls, name):
        return _StubWidget


class _StubWidget(metaclass=_StubMeta):
    def __init__(self, *a, **kw):
        pass

    def __init_subclass__(cls, **kw):
        pass

    def __getattr__(self, name):
        return _stub_func


def _stub_func(*a, **kw):
    return _StubWidget()


class _StubModule:
    def __getattr__(self, name):
        return _StubWidget


for name in ("Gtk", "GLib", "GdkPixbuf", "Gdk", "Pango"):
    setattr(repo_mock, name, _StubModule())

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = repo_mock

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_DIR, "airootfs", "usr", "local", "lib")
sys.path.insert(0, LIB_DIR)

from mados_wifi.backend import (
    WiFiNetwork,
    ConnectionDetails,
    _split_nmcli_line,
    _cidr_to_netmask,
    _parse_connection_fields,
    _parse_device_fields,
    check_wifi_available,
    get_wifi_device,
    scan_networks,
    connect_to_network,
    disconnect_network,
    forget_network,
    get_active_connection_name,
    get_saved_connections,
    set_auto_connect,
    set_static_ip,
    set_dhcp,
    set_dns_override,
    set_proxy,
)


# ═══════════════════════════════════════════════════════════════════════════
# WiFiNetwork data class
# ═══════════════════════════════════════════════════════════════════════════
class TestWiFiNetworkSignalCategory(unittest.TestCase):
    """Verify WiFiNetwork.signal_category property thresholds."""

    def test_excellent_signal(self):
        for sig in (80, 90, 100):
            with self.subTest(signal=sig):
                self.assertEqual(WiFiNetwork(signal=sig).signal_category, 'excellent')

    def test_good_signal(self):
        for sig in (60, 70, 79):
            with self.subTest(signal=sig):
                self.assertEqual(WiFiNetwork(signal=sig).signal_category, 'good')

    def test_fair_signal(self):
        for sig in (40, 50, 59):
            with self.subTest(signal=sig):
                self.assertEqual(WiFiNetwork(signal=sig).signal_category, 'fair')

    def test_weak_signal(self):
        for sig in (20, 30, 39):
            with self.subTest(signal=sig):
                self.assertEqual(WiFiNetwork(signal=sig).signal_category, 'weak')

    def test_none_signal(self):
        for sig in (0, 10, 19):
            with self.subTest(signal=sig):
                self.assertEqual(WiFiNetwork(signal=sig).signal_category, 'none')


class TestWiFiNetworkSignalBars(unittest.TestCase):
    """Verify WiFiNetwork.signal_bars returns correct Unicode bars."""

    def test_full_bars(self):
        self.assertEqual(WiFiNetwork(signal=80).signal_bars, '\u2588\u2588\u2588\u2588')

    def test_three_bars(self):
        self.assertEqual(WiFiNetwork(signal=60).signal_bars, '\u2588\u2588\u2588\u2591')

    def test_two_bars(self):
        self.assertEqual(WiFiNetwork(signal=40).signal_bars, '\u2588\u2588\u2591\u2591')

    def test_one_bar(self):
        self.assertEqual(WiFiNetwork(signal=20).signal_bars, '\u2588\u2591\u2591\u2591')

    def test_no_bars(self):
        self.assertEqual(WiFiNetwork(signal=0).signal_bars, '\u2591\u2591\u2591\u2591')


class TestWiFiNetworkDefaults(unittest.TestCase):
    """Verify WiFiNetwork default field values."""

    def test_default_values(self):
        net = WiFiNetwork()
        self.assertEqual(net.ssid, '')
        self.assertEqual(net.bssid, '')
        self.assertEqual(net.signal, 0)
        self.assertEqual(net.security, '')
        self.assertFalse(net.in_use)


class TestConnectionDetailsDefaults(unittest.TestCase):
    """Verify ConnectionDetails default field values."""

    def test_default_values(self):
        d = ConnectionDetails()
        self.assertEqual(d.ssid, '')
        self.assertEqual(d.ip4_address, '')
        self.assertTrue(d.auto_connect)
        self.assertEqual(d.device, '')


# ═══════════════════════════════════════════════════════════════════════════
# Parsing helpers
# ═══════════════════════════════════════════════════════════════════════════
class TestSplitNmcliLine(unittest.TestCase):
    """Verify _split_nmcli_line handles escaped and unescaped colons."""

    def test_simple_line(self):
        result = _split_nmcli_line('a:b:c')
        self.assertEqual(result, ['a', 'b', 'c'])

    def test_escaped_colon(self):
        """Literal \\: in an SSID should be kept as a colon in the value."""
        result = _split_nmcli_line('field1:SSID\\:with\\:colons:field3')
        self.assertEqual(result, ['field1', 'SSID:with:colons', 'field3'])

    def test_empty_fields(self):
        result = _split_nmcli_line('a::c')
        self.assertEqual(result, ['a', '', 'c'])

    def test_trailing_colon(self):
        result = _split_nmcli_line('a:b:')
        self.assertEqual(result, ['a', 'b', ''])

    def test_single_field(self):
        result = _split_nmcli_line('only')
        self.assertEqual(result, ['only'])

    def test_empty_string(self):
        result = _split_nmcli_line('')
        self.assertEqual(result, [''])

    def test_all_escaped(self):
        result = _split_nmcli_line('\\::\\:')
        self.assertEqual(result, [':', ':'])


class TestCidrToNetmask(unittest.TestCase):
    """Verify CIDR prefix length to dotted-decimal conversion."""

    def test_cidr_24(self):
        self.assertEqual(_cidr_to_netmask('24'), '255.255.255.0')

    def test_cidr_16(self):
        self.assertEqual(_cidr_to_netmask('16'), '255.255.0.0')

    def test_cidr_8(self):
        self.assertEqual(_cidr_to_netmask('8'), '255.0.0.0')

    def test_cidr_32(self):
        self.assertEqual(_cidr_to_netmask('32'), '255.255.255.255')

    def test_cidr_0(self):
        self.assertEqual(_cidr_to_netmask('0'), '0.0.0.0')

    def test_invalid_input(self):
        """Non-numeric input should be returned as-is."""
        self.assertEqual(_cidr_to_netmask('abc'), 'abc')


class TestParseConnectionFields(unittest.TestCase):
    """Verify _parse_connection_fields populates ConnectionDetails correctly."""

    def test_basic_fields(self):
        output = (
            "connection.id:MyNetwork\n"
            "connection.autoconnect:yes\n"
            "connection.timestamp:1700000000\n"
            "802-11-wireless.ssid:TestSSID\n"
            "802-11-wireless-security.key-mgmt:wpa-psk\n"
            "ipv4.addresses:192.168.1.100/24\n"
            "ipv4.gateway:192.168.1.1\n"
            "ipv4.dns:8.8.8.8\n"
            "ipv6.addresses:fe80::1/64\n"
        )
        details = ConnectionDetails()
        _parse_connection_fields(output, details)
        self.assertEqual(details.connection_id, 'MyNetwork')
        self.assertTrue(details.auto_connect)
        self.assertEqual(details.timestamp, '1700000000')
        self.assertEqual(details.ssid, 'TestSSID')
        self.assertEqual(details.security, 'wpa-psk')
        self.assertEqual(details.ip4_address, '192.168.1.100/24')
        self.assertEqual(details.ip4_gateway, '192.168.1.1')
        self.assertEqual(details.ip4_dns, '8.8.8.8')
        self.assertEqual(details.ip6_address, 'fe80::1/64')

    def test_autoconnect_no(self):
        output = "connection.autoconnect:no\n"
        details = ConnectionDetails()
        _parse_connection_fields(output, details)
        self.assertFalse(details.auto_connect)

    def test_empty_values_skipped(self):
        output = "connection.id:--\nipv4.dns:\n"
        details = ConnectionDetails()
        _parse_connection_fields(output, details)
        # connection_id should not be set to '--', dns should stay empty
        self.assertEqual(details.connection_id, '')
        self.assertEqual(details.ip4_dns, '')


class TestParseDeviceFields(unittest.TestCase):
    """Verify _parse_device_fields populates ConnectionDetails correctly."""

    def test_device_fields(self):
        output = (
            "GENERAL.HWADDR:AA:BB:CC:DD:EE:FF\n"
            "IP4.ADDRESS[1]:192.168.1.50/24\n"
            "IP4.GATEWAY:192.168.1.1\n"
            "IP4.DNS[1]:8.8.8.8\n"
            "IP4.DNS[2]:8.8.4.4\n"
            "WIFI.SSID:HomeWifi\n"
            "WIFI.BSSID:11:22:33:44:55:66\n"
            "WIFI.FREQ:5180 MHz\n"
            "WIFI.CHAN:36\n"
            "WIFI.RATE:300 Mbit/s\n"
            "WIFI.SIGNAL:85\n"
            "WIFI.SECURITY:WPA2\n"
        )
        details = ConnectionDetails()
        _parse_device_fields(output, details)
        self.assertEqual(details.mac_address, 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(details.ip4_address, '192.168.1.50/24')
        self.assertEqual(details.ip4_subnet, '255.255.255.0')
        self.assertEqual(details.ip4_gateway, '192.168.1.1')
        self.assertIn('8.8.8.8', details.ip4_dns)
        self.assertIn('8.8.4.4', details.ip4_dns)
        self.assertEqual(details.ssid, 'HomeWifi')
        self.assertEqual(details.bssid, '11:22:33:44:55:66')
        self.assertEqual(details.frequency, '5180 MHz')
        self.assertEqual(details.channel, '36')
        self.assertEqual(details.link_speed, '300 Mbit/s')
        self.assertEqual(details.signal, 85)
        self.assertEqual(details.security, 'WPA2')

    def test_invalid_signal_value(self):
        output = "WIFI.SIGNAL:notanumber\n"
        details = ConnectionDetails()
        _parse_device_fields(output, details)
        self.assertEqual(details.signal, 0)

    def test_ipv6_field(self):
        output = "IP6.ADDRESS[1]:fe80::1234/64\n"
        details = ConnectionDetails()
        _parse_device_fields(output, details)
        self.assertEqual(details.ip6_address, 'fe80::1234/64')


# ═══════════════════════════════════════════════════════════════════════════
# Network operations (with mocked subprocess)
# ═══════════════════════════════════════════════════════════════════════════
class TestCheckWifiAvailable(unittest.TestCase):
    """Verify check_wifi_available() detects WiFi devices."""

    @patch('mados_wifi.backend._run_nmcli')
    def test_wifi_present(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='wifi:connected\nethernet:connected\n',
            returncode=0,
        )
        self.assertTrue(check_wifi_available())

    @patch('mados_wifi.backend._run_nmcli')
    def test_no_wifi(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='ethernet:connected\n',
            returncode=0,
        )
        self.assertFalse(check_wifi_available())

    @patch('mados_wifi.backend._run_nmcli', side_effect=FileNotFoundError)
    def test_nmcli_not_found(self, mock_run):
        self.assertFalse(check_wifi_available())


class TestGetWifiDevice(unittest.TestCase):
    """Verify get_wifi_device() returns the first WiFi device name."""

    @patch('mados_wifi.backend._run_nmcli')
    def test_device_found(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='wlan0:wifi\neth0:ethernet\n',
            returncode=0,
        )
        self.assertEqual(get_wifi_device(), 'wlan0')

    @patch('mados_wifi.backend._run_nmcli')
    def test_no_device(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='eth0:ethernet\n',
            returncode=0,
        )
        self.assertIsNone(get_wifi_device())

    @patch('mados_wifi.backend._run_nmcli', side_effect=FileNotFoundError)
    def test_nmcli_missing(self, mock_run):
        self.assertIsNone(get_wifi_device())


class TestScanNetworks(unittest.TestCase):
    """Verify scan_networks() parses nmcli output into WiFiNetwork objects."""

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_parse_networks(self, mock_check):
        mock_check.return_value = (
            " :HomeNet:AA\\:BB\\:CC\\:DD\\:EE\\:FF:85:WPA2:5180 MHz:36:300 Mbit/s:Infra\n"
            "*:Office:11\\:22\\:33\\:44\\:55\\:66:60:WPA2:2437 MHz:6:54 Mbit/s:Infra\n"
        )
        networks = scan_networks()
        self.assertEqual(len(networks), 2)
        # Connected network should sort first
        self.assertTrue(networks[0].in_use)
        self.assertEqual(networks[0].ssid, 'Office')
        self.assertEqual(networks[1].ssid, 'HomeNet')
        self.assertEqual(networks[1].signal, 85)
        self.assertEqual(networks[1].security, 'WPA2')

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_hidden_network(self, mock_check):
        mock_check.return_value = (
            " ::AA\\:BB\\:CC\\:DD\\:EE\\:FF:50:WPA2:5180 MHz:36:300 Mbit/s:Infra\n"
        )
        networks = scan_networks()
        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0].ssid, '(Hidden)')

    @patch('mados_wifi.backend._run_nmcli_check', side_effect=RuntimeError('scan failed'))
    def test_scan_failure(self, mock_check):
        networks = scan_networks()
        self.assertEqual(networks, [])

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_invalid_signal(self, mock_check):
        mock_check.return_value = (
            " :TestNet:AA\\:BB\\:CC:bad:WPA2:5180:36:300:Infra\n"
        )
        networks = scan_networks()
        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0].signal, 0)


class TestConnectToNetwork(unittest.TestCase):
    """Verify connect_to_network() handles various connection outcomes."""

    @patch('mados_wifi.backend._run_nmcli')
    def test_successful_connection(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertEqual(connect_to_network('TestNet', 'password123'), 'connected')

    @patch('mados_wifi.backend._run_nmcli')
    def test_wrong_password(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr='Error: Secrets were required, but not provided.',
        )
        self.assertEqual(connect_to_network('TestNet', 'wrong'), 'wrong_password')

    @patch('mados_wifi.backend._run_nmcli')
    def test_generic_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr='Connection activation failed.',
        )
        self.assertEqual(connect_to_network('TestNet'), 'Connection activation failed.')

    @patch('mados_wifi.backend._run_nmcli', side_effect=FileNotFoundError)
    def test_nmcli_not_found(self, mock_run):
        self.assertEqual(connect_to_network('TestNet'), 'nmcli not found')

    @patch('mados_wifi.backend._run_nmcli', side_effect=subprocess.TimeoutExpired(cmd='nmcli', timeout=45))
    def test_timeout(self, mock_run):
        self.assertEqual(connect_to_network('TestNet'), 'Connection timed out')

    @patch('mados_wifi.backend._run_nmcli')
    def test_hidden_network_args(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        connect_to_network('HiddenNet', 'pass', hidden=True)
        args = mock_run.call_args[0][0]
        self.assertIn('hidden', args)
        self.assertIn('yes', args)


class TestDisconnectNetwork(unittest.TestCase):
    """Verify disconnect_network() behaviour."""

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_disconnect_by_name(self, mock_check):
        mock_check.return_value = ''
        self.assertTrue(disconnect_network('MyConnection'))

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_nmcli_check')
    def test_disconnect_by_device(self, mock_check, mock_device):
        mock_check.return_value = ''
        self.assertTrue(disconnect_network())

    @patch('mados_wifi.backend.get_wifi_device', return_value=None)
    def test_disconnect_no_device(self, mock_device):
        self.assertFalse(disconnect_network())

    @patch('mados_wifi.backend._run_nmcli_check', side_effect=RuntimeError)
    def test_disconnect_failure(self, mock_check):
        self.assertFalse(disconnect_network('MyConnection'))


class TestForgetNetwork(unittest.TestCase):
    """Verify forget_network() behaviour."""

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_forget_success(self, mock_check):
        mock_check.return_value = ''
        self.assertTrue(forget_network('OldNetwork'))

    @patch('mados_wifi.backend._run_nmcli_check', side_effect=RuntimeError)
    def test_forget_failure(self, mock_check):
        self.assertFalse(forget_network('OldNetwork'))


class TestGetActiveConnectionName(unittest.TestCase):
    """Verify get_active_connection_name() parses active connections."""

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_active_wifi(self, mock_check):
        mock_check.return_value = 'HomeWifi:802-11-wireless\nEthernet:802-3-ethernet'
        self.assertEqual(get_active_connection_name(), 'HomeWifi')

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_no_active_wifi(self, mock_check):
        mock_check.return_value = 'Ethernet:802-3-ethernet'
        self.assertIsNone(get_active_connection_name())


class TestGetSavedConnections(unittest.TestCase):
    """Verify get_saved_connections() lists saved WiFi profiles."""

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_saved_list(self, mock_check):
        mock_check.return_value = (
            'Home:802-11-wireless\n'
            'Office:802-11-wireless\n'
            'LAN:802-3-ethernet'
        )
        saved = get_saved_connections()
        self.assertEqual(saved, ['Home', 'Office'])


class TestSetAutoConnect(unittest.TestCase):
    """Verify set_auto_connect() calls nmcli correctly."""

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_enable(self, mock_check):
        mock_check.return_value = ''
        self.assertTrue(set_auto_connect('MyNet', True))
        args = mock_check.call_args[0][0]
        self.assertIn('yes', args)

    @patch('mados_wifi.backend._run_nmcli_check')
    def test_disable(self, mock_check):
        mock_check.return_value = ''
        self.assertTrue(set_auto_connect('MyNet', False))
        args = mock_check.call_args[0][0]
        self.assertIn('no', args)


class TestSetStaticIp(unittest.TestCase):
    """Verify set_static_ip() configures static addressing."""

    @patch('mados_wifi.backend._run_nmcli')
    @patch('mados_wifi.backend._run_nmcli_check')
    def test_static_with_dns(self, mock_check, mock_run):
        mock_check.return_value = ''
        self.assertTrue(set_static_ip('MyNet', '192.168.1.100/24',
                                       '192.168.1.1', '8.8.8.8'))
        # Should call nmcli_check at least twice (ip + dns)
        self.assertGreaterEqual(mock_check.call_count, 2)


class TestSetDhcp(unittest.TestCase):
    """Verify set_dhcp() resets to automatic addressing."""

    @patch('mados_wifi.backend._run_nmcli')
    @patch('mados_wifi.backend._run_nmcli_check')
    def test_dhcp(self, mock_check, mock_run):
        mock_check.return_value = ''
        self.assertTrue(set_dhcp('MyNet'))
        args = mock_check.call_args[0][0]
        self.assertIn('auto', args)


class TestSetDnsOverride(unittest.TestCase):
    """Verify set_dns_override() configures custom DNS."""

    @patch('mados_wifi.backend._run_nmcli')
    @patch('mados_wifi.backend._run_nmcli_check')
    def test_dns_override(self, mock_check, mock_run):
        mock_check.return_value = ''
        self.assertTrue(set_dns_override('MyNet', '1.1.1.1 8.8.8.8'))


class TestSetProxy(unittest.TestCase):
    """Verify set_proxy() configures and clears proxy settings."""

    @patch('mados_wifi.backend._run_nmcli')
    @patch('mados_wifi.backend._run_nmcli_check')
    def test_set_proxy(self, mock_check, mock_run):
        mock_check.return_value = ''
        self.assertTrue(set_proxy('MyNet', '10.0.0.1', '8080'))

    @patch('mados_wifi.backend._run_nmcli')
    @patch('mados_wifi.backend._run_nmcli_check')
    def test_clear_proxy(self, mock_check, mock_run):
        mock_check.return_value = ''
        self.assertTrue(set_proxy('MyNet', '', ''))
        args = mock_check.call_args[0][0]
        self.assertIn('none', args)


if __name__ == '__main__':
    unittest.main()
