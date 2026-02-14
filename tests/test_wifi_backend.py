#!/usr/bin/env python3
"""
Tests for madOS WiFi backend (network management via iwctl/iwd).

Validates data classes, parsing helpers, and network operations by mocking
subprocess calls to iwctl and related commands.  These tests run in CI 
without requiring actual WiFi hardware or iwd.
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


# ═══════════════════════════════════════════════════════════════════════════
# Network operations (with mocked subprocess)
# ═══════════════════════════════════════════════════════════════════════════
class TestCheckWifiAvailable(unittest.TestCase):
    """Verify check_wifi_available() detects WiFi devices."""

    @patch('mados_wifi.backend._run_command')
    def test_wifi_present(self, mock_run):
        def side_effect(cmd, timeout=30):
            if cmd[0] == 'iw':
                return MagicMock(
                    stdout='phy#0\n\tInterface wlan0\n\t\tifindex 3\n\t\ttype managed\n',
                    returncode=0,
                )
            # rfkill call
            return MagicMock(returncode=0)
        mock_run.side_effect = side_effect
        self.assertTrue(check_wifi_available())

    @patch('mados_wifi.backend._run_command')
    def test_no_wifi(self, mock_run):
        def side_effect(cmd, timeout=30):
            if cmd[0] == 'iw':
                return MagicMock(stdout='', returncode=0)
            return MagicMock(returncode=0)
        mock_run.side_effect = side_effect
        self.assertFalse(check_wifi_available())

    @patch('mados_wifi.backend._run_command')
    def test_iw_not_found(self, mock_run):
        def side_effect(cmd, timeout=30):
            if cmd[0] == 'iw':
                raise FileNotFoundError
            return MagicMock(returncode=0)
        mock_run.side_effect = side_effect
        self.assertFalse(check_wifi_available())


class TestGetWifiDevice(unittest.TestCase):
    """Verify get_wifi_device() returns the first WiFi device name."""

    @patch('mados_wifi.backend._run_command')
    def test_device_found(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='phy#0\n\tInterface wlan0\n\t\tifindex 3\n',
            returncode=0,
        )
        self.assertEqual(get_wifi_device(), 'wlan0')

    @patch('mados_wifi.backend._run_command')
    def test_no_device(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='',
            returncode=0,
        )
        self.assertIsNone(get_wifi_device())

    @patch('mados_wifi.backend._run_command', side_effect=FileNotFoundError)
    def test_iw_missing(self, mock_run):
        self.assertIsNone(get_wifi_device())


class TestScanNetworks(unittest.TestCase):
    """Verify scan_networks() parses iwctl output into WiFiNetwork objects."""

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl')
    @patch('mados_wifi.backend._run_iwctl_check')
    @patch('mados_wifi.backend.time.sleep')
    def test_parse_networks(self, mock_sleep, mock_check, mock_run, mock_device):
        mock_run.return_value = MagicMock(returncode=0)
        mock_check.return_value = (
            "                           Available networks\n"
            "--------------------------------------------------------\n"
            "    Network name                    Security  Signal\n"
            "--------------------------------------------------------\n"
            "    HomeNet                          psk       ****\n"
            ">   Office                           psk       ***\n"
        )
        networks = scan_networks()
        self.assertEqual(len(networks), 2)
        # Connected network should sort first
        self.assertTrue(networks[0].in_use)
        self.assertEqual(networks[0].ssid, 'Office')
        self.assertEqual(networks[1].ssid, 'HomeNet')
        self.assertEqual(networks[1].signal, 85)
        self.assertEqual(networks[1].security, 'WPA/WPA2')

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl')
    @patch('mados_wifi.backend._run_iwctl_check')
    @patch('mados_wifi.backend.time.sleep')
    def test_signal_strength_mapping(self, mock_sleep, mock_check, mock_run, mock_device):
        """Test that star-based signal strength is correctly mapped to percentages."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_check.return_value = (
            "                           Available networks\n"
            "--------------------------------------------------------\n"
            "    Network name                    Security  Signal\n"
            "--------------------------------------------------------\n"
            "    Excellent                        psk       ****\n"
            "    Good                             psk       ***\n"
            "    Fair                             psk       **\n"
            "    Weak                             psk       *\n"
            "    VeryWeak                         psk       \n"
        )
        networks = scan_networks()
        self.assertEqual(len(networks), 5)
        # Verify star-to-percentage mapping
        signal_map = {net.ssid: net.signal for net in networks}
        self.assertEqual(signal_map['Excellent'], 85)  # ****
        self.assertEqual(signal_map['Good'], 70)       # ***
        self.assertEqual(signal_map['Fair'], 50)       # **
        self.assertEqual(signal_map['Weak'], 30)       # *
        self.assertEqual(signal_map['VeryWeak'], 10)   # no stars

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl')
    @patch('mados_wifi.backend._run_iwctl_check')
    @patch('mados_wifi.backend.time.sleep')
    def test_open_network(self, mock_sleep, mock_check, mock_run, mock_device):
        mock_run.return_value = MagicMock(returncode=0)
        mock_check.return_value = (
            "                           Available networks\n"
            "--------------------------------------------------------\n"
            "    Network name                    Security  Signal\n"
            "--------------------------------------------------------\n"
            "    OpenWifi                         open      **\n"
        )
        networks = scan_networks()
        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0].ssid, 'OpenWifi')
        self.assertEqual(networks[0].security, 'Open')
        self.assertEqual(networks[0].signal, 50)

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl')
    @patch('mados_wifi.backend._run_iwctl_check', side_effect=RuntimeError('scan failed'))
    @patch('mados_wifi.backend.time.sleep')
    def test_scan_failure(self, mock_sleep, mock_check, mock_run, mock_device):
        networks = scan_networks()
        self.assertEqual(networks, [])

    @patch('mados_wifi.backend.get_wifi_device', return_value=None)
    def test_no_device(self, mock_device):
        networks = scan_networks()
        self.assertEqual(networks, [])


class TestConnectToNetwork(unittest.TestCase):
    """Verify connect_to_network() handles various connection outcomes."""

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl')
    def test_successful_connection(self, mock_run, mock_device):
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        self.assertEqual(connect_to_network('TestNet', 'password123'), 'connected')

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl')
    def test_wrong_password(self, mock_run, mock_device):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr='Invalid passphrase',
        )
        self.assertEqual(connect_to_network('TestNet', 'wrong'), 'wrong_password')

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl')
    def test_generic_failure(self, mock_run, mock_device):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr='Connection failed.',
        )
        self.assertEqual(connect_to_network('TestNet'), 'Connection failed.')

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl', side_effect=FileNotFoundError)
    def test_iwctl_not_found(self, mock_run, mock_device):
        self.assertEqual(connect_to_network('TestNet'), 'iwctl not found')

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl', side_effect=subprocess.TimeoutExpired(cmd='iwctl', timeout=45))
    def test_timeout(self, mock_run, mock_device):
        self.assertEqual(connect_to_network('TestNet'), 'Connection timed out')

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl')
    def test_open_network(self, mock_run, mock_device):
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        connect_to_network('OpenNet', None)
        # Verify it was called without passphrase
        args = mock_run.call_args[0][0]
        self.assertNotIn('--passphrase', args)

    @patch('mados_wifi.backend.get_wifi_device', return_value=None)
    def test_no_device(self, mock_device):
        self.assertEqual(connect_to_network('TestNet'), 'No WiFi device found')


class TestDisconnectNetwork(unittest.TestCase):
    """Verify disconnect_network() behaviour."""

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl_check')
    def test_disconnect_success(self, mock_check, mock_device):
        mock_check.return_value = ''
        self.assertTrue(disconnect_network())

    @patch('mados_wifi.backend.get_wifi_device', return_value=None)
    def test_disconnect_no_device(self, mock_device):
        self.assertFalse(disconnect_network())

    @patch('mados_wifi.backend.get_wifi_device', return_value='wlan0')
    @patch('mados_wifi.backend._run_iwctl_check', side_effect=RuntimeError)
    def test_disconnect_failure(self, mock_check, mock_device):
        self.assertFalse(disconnect_network())


class TestForgetNetwork(unittest.TestCase):
    """Verify forget_network() behaviour."""

    @patch('mados_wifi.backend._run_iwctl_check')
    def test_forget_success(self, mock_check):
        mock_check.return_value = ''
        self.assertTrue(forget_network('OldNetwork'))

    @patch('mados_wifi.backend._run_iwctl_check', side_effect=RuntimeError)
    def test_forget_failure(self, mock_check):
        self.assertFalse(forget_network('OldNetwork'))


class TestGetActiveConnectionName(unittest.TestCase):
    """Verify get_active_connection_name() returns active SSID."""

    @patch('mados_wifi.backend.get_active_ssid', return_value='HomeWifi')
    def test_active_wifi(self, mock_ssid):
        self.assertEqual(get_active_connection_name(), 'HomeWifi')

    @patch('mados_wifi.backend.get_active_ssid', return_value=None)
    def test_no_active_wifi(self, mock_ssid):
        self.assertIsNone(get_active_connection_name())


class TestGetSavedConnections(unittest.TestCase):
    """Verify get_saved_connections() lists saved WiFi profiles."""

    @patch('mados_wifi.backend._run_iwctl_check')
    def test_saved_list(self, mock_check):
        mock_check.return_value = (
            "                      Known Networks\n"
            "--------------------------------------------------------\n"
            "    Name                    Security  Hidden\n"
            "--------------------------------------------------------\n"
            "    Home                     psk\n"
            "    Office                   psk       *\n"
        )
        saved = get_saved_connections()
        self.assertEqual(saved, ['Home', 'Office'])


class TestSetAutoConnect(unittest.TestCase):
    """Verify set_auto_connect() calls iwctl correctly."""

    @patch('mados_wifi.backend._run_iwctl_check')
    def test_enable(self, mock_check):
        mock_check.return_value = ''
        self.assertTrue(set_auto_connect('MyNet', True))
        args = mock_check.call_args[0][0]
        self.assertIn('yes', args)

    @patch('mados_wifi.backend._run_iwctl_check')
    def test_disable(self, mock_check):
        mock_check.return_value = ''
        self.assertTrue(set_auto_connect('MyNet', False))
        args = mock_check.call_args[0][0]
        self.assertIn('no', args)


class TestSetStaticIp(unittest.TestCase):
    """Verify set_static_ip() returns False (not supported by iwd)."""

    def test_static_with_dns(self):
        self.assertFalse(set_static_ip('MyNet', '192.168.1.100/24',
                                       '192.168.1.1', '8.8.8.8'))


class TestSetDhcp(unittest.TestCase):
    """Verify set_dhcp() returns False (not supported by iwd)."""

    def test_dhcp(self):
        self.assertFalse(set_dhcp('MyNet'))


class TestSetDnsOverride(unittest.TestCase):
    """Verify set_dns_override() returns False (not supported by iwd)."""

    def test_dns_override(self):
        self.assertFalse(set_dns_override('MyNet', '1.1.1.1 8.8.8.8'))


class TestSetProxy(unittest.TestCase):
    """Verify set_proxy() returns False (not supported by iwd)."""

    def test_set_proxy(self):
        self.assertFalse(set_proxy('MyNet', '10.0.0.1', '8080'))

    def test_clear_proxy(self):
        self.assertFalse(set_proxy('MyNet', '', ''))


if __name__ == '__main__':
    unittest.main()
