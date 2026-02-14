#!/usr/bin/env python3
"""
Tests for madOS Bluetooth support configuration.

Validates that Bluetooth packages, services, and application files are
properly configured for both the live USB environment and the
post-installation system.

These tests verify file presence, syntax, and configuration correctness
without requiring actual Bluetooth hardware.
"""

import sys
import os
import types
import unittest
import json
import subprocess

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so Bluetooth app modules can be imported headlessly.
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
AIROOTFS = os.path.join(REPO_DIR, "airootfs")
LIB_DIR = os.path.join(AIROOTFS, "usr", "local", "lib")
BIN_DIR = os.path.join(AIROOTFS, "usr", "local", "bin")

# Add lib dir to path for imports
sys.path.insert(0, LIB_DIR)


class TestBluetoothPackages(unittest.TestCase):
    """Verify Bluetooth packages are included in the ISO package list."""

    def test_packages_x86_64_has_bluez(self):
        """packages.x86_64 should include bluez."""
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            packages = [line.strip() for line in f
                        if line.strip() and not line.strip().startswith('#')]
        self.assertIn('bluez', packages,
                      "bluez must be in packages.x86_64 for live USB")

    def test_packages_x86_64_has_bluez_utils(self):
        """packages.x86_64 should include bluez-utils."""
        pkg_file = os.path.join(REPO_DIR, "packages.x86_64")
        with open(pkg_file) as f:
            packages = [line.strip() for line in f
                        if line.strip() and not line.strip().startswith('#')]
        self.assertIn('bluez-utils', packages,
                      "bluez-utils must be in packages.x86_64 for live USB")

    def test_installer_config_has_bluez(self):
        """Installer config.py PACKAGES should include bluez."""
        from mados_installer.config import PACKAGES
        self.assertIn('bluez', PACKAGES,
                      "bluez must be in installer PACKAGES for post-install")

    def test_installer_config_has_bluez_utils(self):
        """Installer config.py PACKAGES should include bluez-utils."""
        from mados_installer.config import PACKAGES
        self.assertIn('bluez-utils', PACKAGES,
                      "bluez-utils must be in installer PACKAGES for post-install")


class TestBluetoothService(unittest.TestCase):
    """Verify bluetooth.service is enabled in both live USB and post-install."""

    def test_live_usb_bluetooth_service_symlink(self):
        """bluetooth.service should be enabled in multi-user.target.wants."""
        service_link = os.path.join(
            AIROOTFS, "etc", "systemd", "system",
            "multi-user.target.wants", "bluetooth.service"
        )
        self.assertTrue(
            os.path.islink(service_link),
            "bluetooth.service must be enabled as a symlink for live USB"
        )
        target = os.readlink(service_link)
        self.assertEqual(
            "bluetooth.service",
            os.path.basename(target),
            "bluetooth.service symlink should point to the bluetooth.service unit file",
        )

    def test_post_install_enables_bluetooth(self):
        """installation.py should enable bluetooth.service."""
        install_py = os.path.join(
            LIB_DIR, "mados_installer", "pages", "installation.py"
        )
        with open(install_py) as f:
            content = f.read()
        self.assertIn('systemctl enable bluetooth',
                      content,
                      "installation.py must enable bluetooth.service")

    def test_bluetooth_main_conf_exists(self):
        """airootfs/etc/bluetooth/main.conf should exist."""
        main_conf = os.path.join(AIROOTFS, "etc", "bluetooth", "main.conf")
        self.assertTrue(
            os.path.isfile(main_conf),
            "main.conf must exist in /etc/bluetooth/"
        )

    def test_bluetooth_main_conf_auto_enable(self):
        """main.conf should contain AutoEnable=true under [General]."""
        main_conf = os.path.join(AIROOTFS, "etc", "bluetooth", "main.conf")
        with open(main_conf) as f:
            content = f.read()
        # Check for [General] section
        self.assertIn('[General]', content,
                      "main.conf must have [General] section")
        # Check for AutoEnable=true
        self.assertIn('AutoEnable=true', content,
                      "main.conf must have AutoEnable=true for auto-powering adapter")


class TestBluetoothServiceActivation(unittest.TestCase):
    """Verify Bluetooth service is activated before querying bluetoothctl."""

    def test_bluetooth_status_script_starts_service(self):
        """bluetooth-status.sh should start bluetooth.service if not running."""
        script_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "scripts",
            "bluetooth-status.sh"
        )
        with open(script_path) as f:
            content = f.read()
        self.assertIn('systemctl start bluetooth.service', content,
                      "bluetooth-status.sh must start bluetooth.service")

    def test_launcher_starts_bluetooth_service(self):
        """mados-bluetooth launcher should start bluetooth.service if not running."""
        launcher = os.path.join(BIN_DIR, "mados-bluetooth")
        with open(launcher) as f:
            content = f.read()
        self.assertIn('systemctl start bluetooth.service', content,
                      "mados-bluetooth launcher must start bluetooth.service")

    def test_waybar_exec_if_starts_service(self):
        """Waybar config custom/bluetooth exec-if should start bluetooth.service."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            config = json.load(f)
        bt_config = config.get('custom/bluetooth', {})
        exec_if = bt_config.get('exec-if', '')
        self.assertIn('systemctl', exec_if,
                      "exec-if must use systemctl to activate bluetooth.service")
        self.assertIn('start', exec_if,
                      "exec-if must start bluetooth.service if not running")


class TestBluetoothApplicationFiles(unittest.TestCase):
    """Verify Bluetooth application files exist and have correct structure."""

    def test_launcher_script_exists(self):
        """mados-bluetooth launcher script should exist."""
        launcher = os.path.join(BIN_DIR, "mados-bluetooth")
        self.assertTrue(os.path.isfile(launcher),
                        "mados-bluetooth launcher must exist")

    def test_launcher_script_syntax(self):
        """mados-bluetooth launcher should have valid bash syntax."""
        launcher = os.path.join(BIN_DIR, "mados-bluetooth")
        result = subprocess.run(
            ['bash', '-n', launcher],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                         f"Bash syntax error: {result.stderr}")

    def test_launcher_calls_mados_bluetooth_module(self):
        """Launcher should invoke python3 -m mados_bluetooth."""
        launcher = os.path.join(BIN_DIR, "mados-bluetooth")
        with open(launcher) as f:
            content = f.read()
        self.assertIn('mados_bluetooth', content,
                      "Launcher must call mados_bluetooth module")

    def test_python_package_init(self):
        """mados_bluetooth/__init__.py should exist."""
        init_file = os.path.join(LIB_DIR, "mados_bluetooth", "__init__.py")
        self.assertTrue(os.path.isfile(init_file))

    def test_python_package_main(self):
        """mados_bluetooth/__main__.py should exist."""
        main_file = os.path.join(LIB_DIR, "mados_bluetooth", "__main__.py")
        self.assertTrue(os.path.isfile(main_file))

    def test_python_modules_exist(self):
        """All expected Python modules should exist."""
        expected = ['__init__.py', '__main__.py', 'app.py',
                    'backend.py', 'theme.py', 'translations.py']
        pkg_dir = os.path.join(LIB_DIR, "mados_bluetooth")
        for module in expected:
            path = os.path.join(pkg_dir, module)
            self.assertTrue(os.path.isfile(path),
                            f"{module} must exist in mados_bluetooth/")

    def test_python_syntax_all_modules(self):
        """All Python modules should have valid syntax."""
        pkg_dir = os.path.join(LIB_DIR, "mados_bluetooth")
        for fname in os.listdir(pkg_dir):
            if fname.endswith('.py'):
                fpath = os.path.join(pkg_dir, fname)
                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', fpath],
                    capture_output=True, text=True
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"Syntax error in {fname}: {result.stderr}"
                )


class TestBluetoothBackend(unittest.TestCase):
    """Verify the Bluetooth backend module structure and data classes."""

    def test_import_backend(self):
        """Backend module should be importable."""
        from mados_bluetooth import backend
        self.assertIsNotNone(backend)

    def test_bluetooth_device_dataclass(self):
        """BluetoothDevice should have the expected fields."""
        from mados_bluetooth.backend import BluetoothDevice
        device = BluetoothDevice(
            address='AA:BB:CC:DD:EE:FF',
            name='Test Device',
            paired=True,
            connected=False,
            trusted=True,
            icon='audio-headphones',
        )
        self.assertEqual(device.address, 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(device.name, 'Test Device')
        self.assertTrue(device.paired)
        self.assertFalse(device.connected)
        self.assertTrue(device.trusted)
        self.assertEqual(device.display_name, 'Test Device')

    def test_display_name_fallback(self):
        """display_name should fall back to address if name is empty."""
        from mados_bluetooth.backend import BluetoothDevice
        device = BluetoothDevice(address='AA:BB:CC:DD:EE:FF', name='')
        self.assertEqual(device.display_name, 'AA:BB:CC:DD:EE:FF')

    def test_parse_device_list(self):
        """_parse_device_list should parse bluetoothctl output correctly."""
        from mados_bluetooth.backend import _parse_device_list
        output = (
            "Device AA:BB:CC:DD:EE:FF My Headphones\n"
            "Device 11:22:33:44:55:66 Keyboard\n"
            "Some other line\n"
        )
        devices = _parse_device_list(output)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].address, 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(devices[0].name, 'My Headphones')
        self.assertEqual(devices[1].address, '11:22:33:44:55:66')
        self.assertEqual(devices[1].name, 'Keyboard')

    def test_parse_device_list_empty(self):
        """_parse_device_list should return empty list for empty input."""
        from mados_bluetooth.backend import _parse_device_list
        devices = _parse_device_list('')
        self.assertEqual(len(devices), 0)


class TestBluetoothTranslations(unittest.TestCase):
    """Verify translations are complete for all supported languages."""

    def test_all_languages_present(self):
        """All 6 languages should be available."""
        from mados_bluetooth.translations import TRANSLATIONS
        expected = ['English', 'Español', 'Français', 'Deutsch', '中文', '日本語']
        for lang in expected:
            self.assertIn(lang, TRANSLATIONS,
                          f"Language '{lang}' missing from translations")

    def test_all_keys_in_all_languages(self):
        """Every key in English should exist in all other languages."""
        from mados_bluetooth.translations import TRANSLATIONS
        english_keys = set(TRANSLATIONS['English'].keys())
        for lang, trans in TRANSLATIONS.items():
            lang_keys = set(trans.keys())
            missing = english_keys - lang_keys
            self.assertEqual(
                len(missing), 0,
                f"Language '{lang}' missing keys: {missing}"
            )

    def test_get_text_returns_correct_value(self):
        """get_text should return the correct translation."""
        from mados_bluetooth.translations import get_text
        self.assertEqual(get_text('scan', 'English'), 'Scan')
        self.assertEqual(get_text('scan', 'Español'), 'Buscar')

    def test_get_text_fallback_to_english(self):
        """get_text should fall back to English for unknown language."""
        from mados_bluetooth.translations import get_text
        result = get_text('scan', 'Klingon')
        self.assertEqual(result, 'Scan')

    def test_detect_system_language(self):
        """detect_system_language should return a valid language name."""
        from mados_bluetooth.translations import detect_system_language
        lang = detect_system_language()
        from mados_bluetooth.translations import TRANSLATIONS
        self.assertIn(lang, TRANSLATIONS)


class TestProfiledefPermissions(unittest.TestCase):
    """Verify profiledef.sh includes Bluetooth file permissions."""

    def test_profiledef_has_bluetooth_launcher(self):
        """profiledef.sh should have mados-bluetooth permission."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        self.assertIn('mados-bluetooth', content,
                      "profiledef.sh must include mados-bluetooth permissions")

    def test_profiledef_has_bluetooth_lib(self):
        """profiledef.sh should have mados_bluetooth lib permission."""
        profiledef = os.path.join(REPO_DIR, "profiledef.sh")
        with open(profiledef) as f:
            content = f.read()
        self.assertIn('mados_bluetooth', content,
                      "profiledef.sh must include mados_bluetooth lib permissions")


class TestSwayConfig(unittest.TestCase):
    """Verify Sway configuration includes Bluetooth window rules."""

    def test_sway_has_bluetooth_window_rule(self):
        """Sway config should have window rule for mados-bluetooth."""
        sway_config = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "sway", "config"
        )
        with open(sway_config) as f:
            content = f.read()
        self.assertIn('mados-bluetooth', content,
                      "Sway config must have mados-bluetooth window rule")

    def test_sway_bluetooth_floating(self):
        """Bluetooth window should be configured as floating."""
        sway_config = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "sway", "config"
        )
        with open(sway_config) as f:
            content = f.read()
        self.assertIn('for_window [app_id="mados-bluetooth"] floating enable',
                      content,
                      "Bluetooth window must be floating")


class TestWaybarConfig(unittest.TestCase):
    """Verify Waybar configuration includes Bluetooth module."""

    def test_waybar_config_valid_json(self):
        """Waybar config should be valid JSON."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            config = json.load(f)
        self.assertIsInstance(config, dict)

    def test_waybar_has_bluetooth_module(self):
        """Waybar config should include bluetooth module in modules-right."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            config = json.load(f)
        right_modules = config.get('modules-right', [])
        self.assertIn('custom/bluetooth', right_modules,
                      "Waybar must have custom/bluetooth in modules-right")

    def test_waybar_bluetooth_module_config(self):
        """Waybar bluetooth module should have on-click = mados-bluetooth."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            config = json.load(f)
        bt_config = config.get('custom/bluetooth', {})
        self.assertEqual(bt_config.get('on-click'), 'mados-bluetooth',
                         "Bluetooth module on-click must launch mados-bluetooth")

    def test_waybar_bluetooth_exec_if(self):
        """Waybar bluetooth module should have exec-if to detect hardware."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            config = json.load(f)
        bt_config = config.get('custom/bluetooth', {})
        exec_if = bt_config.get('exec-if', '')
        self.assertIn('bluetoothctl', exec_if,
                       "exec-if must use bluetoothctl to detect hardware")

    def test_waybar_bluetooth_exec_script(self):
        """Waybar bluetooth module exec should reference the status script."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            config = json.load(f)
        bt_config = config.get('custom/bluetooth', {})
        exec_cmd = bt_config.get('exec', '')
        self.assertIn('bluetooth-status.sh', exec_cmd,
                       "exec must reference bluetooth-status.sh script")

    def test_bluetooth_status_script_exists(self):
        """bluetooth-status.sh script should exist."""
        script_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "scripts",
            "bluetooth-status.sh"
        )
        self.assertTrue(os.path.isfile(script_path),
                        "bluetooth-status.sh must exist")

    def test_bluetooth_status_script_valid_bash(self):
        """bluetooth-status.sh should have valid bash syntax."""
        script_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "scripts",
            "bluetooth-status.sh"
        )
        result = subprocess.run(
            ['bash', '-n', script_path],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                         f"bluetooth-status.sh has syntax errors: {result.stderr}")

    def test_waybar_bluetooth_return_type(self):
        """Waybar bluetooth module should use JSON return type."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            config = json.load(f)
        bt_config = config.get('custom/bluetooth', {})
        self.assertEqual(bt_config.get('return-type'), 'json',
                         "Bluetooth module must use JSON return type")

    def test_waybar_bluetooth_next_to_network(self):
        """Bluetooth module should be positioned next to the network module."""
        config_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "config"
        )
        with open(config_path) as f:
            config = json.load(f)
        right_modules = config.get('modules-right', [])
        net_idx = right_modules.index('network')
        bt_idx = right_modules.index('custom/bluetooth')
        self.assertEqual(bt_idx, net_idx + 1,
                         "Bluetooth must be right after network in modules-right")


class TestWaybarBluetoothStyle(unittest.TestCase):
    """Verify Waybar CSS includes Bluetooth styling."""

    def test_waybar_css_has_bluetooth_style(self):
        """Waybar style.css should have #custom-bluetooth styling."""
        css_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "style.css"
        )
        with open(css_path) as f:
            content = f.read()
        self.assertIn('#custom-bluetooth', content,
                      "Waybar style.css must include #custom-bluetooth styling")

    def test_waybar_css_has_bluetooth_connected_class(self):
        """Waybar style.css should style the connected state."""
        css_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "style.css"
        )
        with open(css_path) as f:
            content = f.read()
        self.assertIn('#custom-bluetooth.connected', content,
                      "Waybar style.css must style connected Bluetooth state")

    def test_waybar_css_has_bluetooth_off_class(self):
        """Waybar style.css should style the off state."""
        css_path = os.path.join(
            AIROOTFS, "etc", "skel", ".config", "waybar", "style.css"
        )
        with open(css_path) as f:
            content = f.read()
        self.assertIn('#custom-bluetooth.off', content,
                      "Waybar style.css must style off Bluetooth state")


class TestInstallationBluetoothPackages(unittest.TestCase):
    """Verify Bluetooth packages are in the installer package lists."""

    def test_config_packages_has_bluez(self):
        """PACKAGES (combined) should include bluez."""
        from mados_installer.config import PACKAGES
        self.assertIn('bluez', PACKAGES,
                      "Installer PACKAGES must include bluez package")

    def test_config_packages_has_bluez_utils(self):
        """PACKAGES (combined) should include bluez-utils."""
        from mados_installer.config import PACKAGES
        self.assertIn('bluez-utils', PACKAGES,
                      "Installer PACKAGES must include bluez-utils package")


if __name__ == "__main__":
    unittest.main()
