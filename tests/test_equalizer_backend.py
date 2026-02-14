#!/usr/bin/env python3
"""
Tests for madOS Audio Equalizer backend module.

Validates PipeWire configuration generation, file I/O operations,
config directory paths, EQ application logic, and backend initialization.

These tests run in CI without requiring PipeWire or audio hardware.
"""

import sys
import os
import json
import types
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so equalizer modules can be imported headlessly.
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

from mados_equalizer.backend import (
    AudioBackend,
    EQ_CONFIG_DIR,
    EQ_CONFIG_FILE,
    LEGACY_PIPEWIRE_CONFIG_FILE,
    EQ_NODE_NAME,
    EQ_NODE_DESCRIPTION,
    DEFAULT_Q,
)
from mados_equalizer.presets import FREQUENCY_BANDS


# ═══════════════════════════════════════════════════════════════════════════
# Config path validation
# ═══════════════════════════════════════════════════════════════════════════
class TestConfigPaths(unittest.TestCase):
    """Verify config directory and file paths are correct."""

    def test_config_dir_outside_pipewire_conf_d(self):
        """EQ config must NOT be in pipewire.conf.d to avoid auto-loading."""
        config_dir_str = str(EQ_CONFIG_DIR)
        self.assertNotIn('pipewire.conf.d', config_dir_str)
        self.assertNotIn('filter-chain.conf.d', config_dir_str)

    def test_config_dir_in_mados_directory(self):
        """Config directory should be under ~/.config/mados/equalizer."""
        config_dir_str = str(EQ_CONFIG_DIR)
        self.assertIn('.config/mados/equalizer', config_dir_str)

    def test_config_file_name(self):
        """Config file should be named filter-chain.conf."""
        self.assertEqual(EQ_CONFIG_FILE.name, 'filter-chain.conf')

    def test_config_file_in_eq_dir(self):
        """Config file must be inside the EQ config directory."""
        config_file_str = str(EQ_CONFIG_FILE)
        self.assertIn('mados/equalizer', config_file_str)
        self.assertIn('filter-chain.conf', config_file_str)

    def test_legacy_config_in_pipewire_conf_d(self):
        """Legacy config path should reference pipewire.conf.d for cleanup."""
        legacy_str = str(LEGACY_PIPEWIRE_CONFIG_FILE)
        self.assertIn('pipewire.conf.d', legacy_str)
        self.assertIn('mados-eq.conf', legacy_str)


# ═══════════════════════════════════════════════════════════════════════════
# AudioBackend initialization
# ═══════════════════════════════════════════════════════════════════════════
class TestAudioBackendInit(unittest.TestCase):
    """Test AudioBackend initialization and default state."""

    @patch('mados_equalizer.backend.shutil.which')
    @patch('mados_equalizer.backend.AudioBackend._detect_output_device')
    def test_init_default_state(self, mock_detect, mock_which):
        """Backend should initialize with disabled EQ and zero gains."""
        mock_which.return_value = None
        backend = AudioBackend()

        self.assertEqual(backend.gains, [0.0] * 8)
        self.assertFalse(backend.enabled)
        self.assertEqual(backend.master_volume, 1.0)
        self.assertFalse(backend.muted)
        self.assertEqual(backend.active_sink, '')

    @patch('mados_equalizer.backend.shutil.which')
    @patch('mados_equalizer.backend.AudioBackend._detect_output_device')
    def test_init_detects_pipewire(self, mock_detect, mock_which):
        """Backend should detect PipeWire when pw-cli is available."""
        def which_side_effect(cmd):
            return '/usr/bin/' + cmd if cmd == 'pw-cli' else None

        mock_which.side_effect = which_side_effect
        backend = AudioBackend()

        self.assertTrue(backend.has_pipewire)
        self.assertFalse(backend.has_wpctl)
        self.assertFalse(backend.has_pulseaudio)

    @patch('mados_equalizer.backend.shutil.which')
    @patch('mados_equalizer.backend.AudioBackend._detect_output_device')
    def test_init_calls_detect_output_device(self, mock_detect, mock_which):
        """Backend should call _detect_output_device during initialization."""
        mock_which.return_value = None
        backend = AudioBackend()

        mock_detect.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# _generate_filter_chain_config
# ═══════════════════════════════════════════════════════════════════════════
class TestGenerateFilterChainConfig(unittest.TestCase):
    """Test filter-chain configuration generation."""

    @patch('mados_equalizer.backend.shutil.which')
    @patch('mados_equalizer.backend.AudioBackend._detect_output_device')
    def setUp(self, mock_detect, mock_which):
        mock_which.return_value = None
        self.backend = AudioBackend()
        self.backend.gains = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        self.backend.active_sink = 'test_sink'

    def test_config_has_context_modules(self):
        """Generated config should have context.modules section."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn('context.modules', config)

    def test_config_has_filter_chain_module(self):
        """Generated config should load libpipewire-module-filter-chain."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn('libpipewire-module-filter-chain', config)

    def test_config_has_bq_peaking_filters(self):
        """Generated config should contain bq_peaking filter entries."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn('bq_peaking', config)

    def test_config_has_correct_node_name(self):
        """Generated config should use the EQ_NODE_NAME constant."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn(f'node.name = "{EQ_NODE_NAME}"', config)

    def test_config_has_eight_eq_bands(self):
        """Generated config should have exactly 8 EQ bands."""
        config = self.backend._generate_filter_chain_config()
        # Count occurrences of eq_band_N
        band_count = 0
        for i in range(1, 10):
            if f'eq_band_{i}' in config:
                band_count += 1
        self.assertEqual(band_count, 8)

    def test_config_band_frequencies_match(self):
        """Band frequencies in config should match FREQUENCY_BANDS."""
        config = self.backend._generate_filter_chain_config()
        for freq in FREQUENCY_BANDS:
            # Check that each frequency appears in the config
            self.assertIn(f'"Freq" = {float(freq)}', config)

    def test_config_includes_gains(self):
        """Generated config should include the gain values."""
        config = self.backend._generate_filter_chain_config()
        for gain in self.backend.gains:
            self.assertIn(f'"Gain" = {float(gain)}', config)

    def test_config_includes_q_factor(self):
        """Generated config should include Q factor for filters."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn(f'"Q" = {DEFAULT_Q}', config)

    def test_config_has_node_description(self):
        """Generated config should include node description."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn(EQ_NODE_DESCRIPTION, config)

    def test_config_has_spa_libs(self):
        """Generated config should have context.spa-libs for standalone use."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn('context.spa-libs', config)
        self.assertIn('audioconvert', config)

    def test_config_spa_libs_use_dot_notation(self):
        """SPA lib keys must use dot notation (factory names), not slashes."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn('audio.convert.*', config)
        self.assertIn('support.*', config)
        # Must NOT use path-style key patterns (old/broken format)
        self.assertNotIn('audio/convert/', config)
        # 'support/' in values (e.g. support/libspa-support) is fine;
        # only the key 'support/*' pattern was wrong.
        self.assertNotIn('support/*', config)

    def test_config_targets_active_sink(self):
        """Generated config should target the active audio sink."""
        config = self.backend._generate_filter_chain_config()
        self.assertIn(f'node.target = "{self.backend.active_sink}"', config)


# ═══════════════════════════════════════════════════════════════════════════
# _write_pipewire_config
# ═══════════════════════════════════════════════════════════════════════════
class TestWriteConfig(unittest.TestCase):
    """Test EQ config file writing."""

    @patch('mados_equalizer.backend.shutil.which')
    @patch('mados_equalizer.backend.AudioBackend._detect_output_device')
    def setUp(self, mock_detect, mock_which):
        mock_which.return_value = None
        self.backend = AudioBackend()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_creates_config_dir(self):
        """_write_config should create the config directory."""
        config_dir = Path(self.tmpdir) / 'mados' / 'equalizer'
        config_file = config_dir / 'filter-chain.conf'

        with patch('mados_equalizer.backend.EQ_CONFIG_DIR', config_dir):
            with patch('mados_equalizer.backend.EQ_CONFIG_FILE', config_file):
                result = self.backend._write_config()

        self.assertTrue(result)
        self.assertTrue(config_dir.exists())
        self.assertTrue(config_dir.is_dir())

    def test_write_creates_config_file(self):
        """_write_config should create the config file."""
        config_dir = Path(self.tmpdir) / 'mados' / 'equalizer'
        config_file = config_dir / 'filter-chain.conf'

        with patch('mados_equalizer.backend.EQ_CONFIG_DIR', config_dir):
            with patch('mados_equalizer.backend.EQ_CONFIG_FILE', config_file):
                result = self.backend._write_config()

        self.assertTrue(result)
        self.assertTrue(config_file.exists())
        self.assertTrue(config_file.is_file())

    def test_write_config_contains_valid_data(self):
        """Written config should contain valid filter-chain data."""
        config_dir = Path(self.tmpdir) / 'mados' / 'equalizer'
        config_file = config_dir / 'filter-chain.conf'

        with patch('mados_equalizer.backend.EQ_CONFIG_DIR', config_dir):
            with patch('mados_equalizer.backend.EQ_CONFIG_FILE', config_file):
                result = self.backend._write_config()

        self.assertTrue(result)

        with open(config_file, 'r') as f:
            content = f.read()

        self.assertIn('context.modules', content)
        self.assertIn('libpipewire-module-filter-chain', content)
        self.assertIn('bq_peaking', content)
        self.assertIn(EQ_NODE_NAME, content)

    def test_write_config_has_spa_libs(self):
        """Written config should contain context.spa-libs for standalone use."""
        config_dir = Path(self.tmpdir) / 'mados' / 'equalizer'
        config_file = config_dir / 'filter-chain.conf'

        with patch('mados_equalizer.backend.EQ_CONFIG_DIR', config_dir):
            with patch('mados_equalizer.backend.EQ_CONFIG_FILE', config_file):
                self.backend._write_config()

        with open(config_file, 'r') as f:
            content = f.read()

        self.assertIn('context.spa-libs', content)
        self.assertIn('audioconvert', content)

    def test_write_returns_true_on_success(self):
        """_write_config should return True on success."""
        config_dir = Path(self.tmpdir) / 'mados' / 'equalizer'
        config_file = config_dir / 'filter-chain.conf'

        with patch('mados_equalizer.backend.EQ_CONFIG_DIR', config_dir):
            with patch('mados_equalizer.backend.EQ_CONFIG_FILE', config_file):
                result = self.backend._write_config()

        self.assertTrue(result)

    def test_write_returns_false_on_readonly_dir(self):
        """_write_config should return False for read-only directory."""
        config_dir = Path(self.tmpdir) / 'readonly'
        config_file = config_dir / 'filter-chain.conf'

        # Create a read-only directory
        config_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(config_dir, 0o444)

        try:
            with patch('mados_equalizer.backend.EQ_CONFIG_DIR', config_dir):
                with patch('mados_equalizer.backend.EQ_CONFIG_FILE', config_file):
                    result = self.backend._write_config()

            self.assertFalse(result)
        finally:
            # Restore write permissions for cleanup
            os.chmod(config_dir, 0o755)

    def test_write_atomic_operation(self):
        """_write_config should write atomically (temp then rename)."""
        config_dir = Path(self.tmpdir) / 'mados' / 'equalizer'
        config_file = config_dir / 'filter-chain.conf'

        with patch('mados_equalizer.backend.EQ_CONFIG_DIR', config_dir):
            with patch('mados_equalizer.backend.EQ_CONFIG_FILE', config_file):
                result = self.backend._write_config()

        self.assertTrue(result)
        # After successful write, temp file should not exist
        tmp_file = config_file.with_suffix('.tmp')
        self.assertFalse(tmp_file.exists())


# ═══════════════════════════════════════════════════════════════════════════
# _remove_pipewire_config
# ═══════════════════════════════════════════════════════════════════════════
class TestCleanupLegacyConfig(unittest.TestCase):
    """Test legacy config cleanup."""

    @patch('mados_equalizer.backend.shutil.which')
    @patch('mados_equalizer.backend.AudioBackend._detect_output_device')
    def setUp(self, mock_detect, mock_which):
        mock_which.return_value = None
        self.backend = AudioBackend()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cleanup_deletes_legacy_pipewire_conf_d(self):
        """_cleanup_legacy_config should delete mados-eq.conf from pipewire.conf.d."""
        legacy_dir = Path(self.tmpdir) / 'pipewire.conf.d'
        legacy_file = legacy_dir / 'mados-eq.conf'
        legacy_dir.mkdir(parents=True, exist_ok=True)

        with open(legacy_file, 'w') as f:
            f.write('legacy config')

        self.assertTrue(legacy_file.exists())

        with patch('mados_equalizer.backend.LEGACY_PIPEWIRE_CONFIG_FILE', legacy_file):
            with patch.object(Path, 'home', return_value=Path(self.tmpdir)):
                self.backend._cleanup_legacy_config()

        self.assertFalse(legacy_file.exists())

    def test_cleanup_no_error_when_file_missing(self):
        """_cleanup_legacy_config should not error when legacy file is absent."""
        missing_file = Path(self.tmpdir) / 'nonexistent' / 'mados-eq.conf'

        with patch('mados_equalizer.backend.LEGACY_PIPEWIRE_CONFIG_FILE', missing_file):
            with patch.object(Path, 'home', return_value=Path(self.tmpdir)):
                # Should not raise
                self.backend._cleanup_legacy_config()

    def test_cleanup_deletes_filter_chain_conf_d(self):
        """_cleanup_legacy_config should also clean filter-chain.conf.d."""
        legacy_dir = Path(self.tmpdir) / '.config' / 'pipewire' / 'filter-chain.conf.d'
        legacy_file = legacy_dir / 'mados-eq.conf'
        legacy_dir.mkdir(parents=True, exist_ok=True)

        with open(legacy_file, 'w') as f:
            f.write('old config')

        self.assertTrue(legacy_file.exists())

        bogus = Path(self.tmpdir) / 'bogus'
        with patch('mados_equalizer.backend.LEGACY_PIPEWIRE_CONFIG_FILE', bogus):
            with patch.object(Path, 'home', return_value=Path(self.tmpdir)):
                self.backend._cleanup_legacy_config()

        self.assertFalse(legacy_file.exists())


# ═══════════════════════════════════════════════════════════════════════════
# apply_eq validation
# ═══════════════════════════════════════════════════════════════════════════
class TestApplyEq(unittest.TestCase):
    """Test apply_eq method validation."""

    @patch('mados_equalizer.backend.shutil.which')
    @patch('mados_equalizer.backend.AudioBackend._detect_output_device')
    def setUp(self, mock_detect, mock_which):
        mock_which.return_value = None
        self.backend = AudioBackend()

    def test_apply_eq_validates_gain_count(self):
        """apply_eq should reject wrong number of gain values."""
        success, message = self.backend.apply_eq(gains=[1.0, 2.0, 3.0])
        self.assertFalse(success)
        self.assertIn('Invalid', message)

    def test_apply_eq_accepts_eight_gains(self):
        """apply_eq should accept exactly 8 gain values."""
        self.backend.enabled = False  # Disabled should just call disable_eq
        success, message = self.backend.apply_eq(gains=[0.0] * 8)
        self.assertTrue(success)

    def test_apply_eq_updates_gains(self):
        """apply_eq should update internal gains when provided."""
        self.backend.enabled = False
        gains = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        self.backend.apply_eq(gains=gains)
        self.assertEqual(self.backend.gains, gains)

    def test_apply_eq_uses_current_gains_when_none(self):
        """apply_eq should use current gains when gains param is None."""
        self.backend.enabled = False
        self.backend.gains = [1.0] * 8
        self.backend.apply_eq(gains=None)
        self.assertEqual(self.backend.gains, [1.0] * 8)

    @patch('mados_equalizer.backend.AudioBackend._write_config')
    @patch('mados_equalizer.backend.AudioBackend._start_eq_process')
    def test_apply_eq_calls_write_config_when_enabled(self, mock_start, mock_write):
        """apply_eq should write config when enabled and PipeWire available."""
        self.backend.enabled = True
        self.backend.has_pipewire = True
        mock_write.return_value = True
        mock_start.return_value = True

        success, message = self.backend.apply_eq(gains=[0.0] * 8)

        self.assertTrue(success)
        mock_write.assert_called_once()
        mock_start.assert_called_once()

    @patch('mados_equalizer.backend.AudioBackend._write_config')
    def test_apply_eq_returns_false_on_write_failure(self, mock_write):
        """apply_eq should return False if config write fails."""
        self.backend.enabled = True
        self.backend.has_pipewire = True
        mock_write.return_value = False

        success, message = self.backend.apply_eq(gains=[0.0] * 8)

        self.assertFalse(success)
        self.assertIn('Failed to write', message)

    @patch('mados_equalizer.backend.AudioBackend.disable_eq')
    def test_apply_eq_calls_disable_when_not_enabled(self, mock_disable):
        """apply_eq should call disable_eq when enabled is False."""
        self.backend.enabled = False
        mock_disable.return_value = (True, 'disabled')

        success, message = self.backend.apply_eq(gains=[0.0] * 8)

        mock_disable.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# Constants validation
# ═══════════════════════════════════════════════════════════════════════════
class TestConstants(unittest.TestCase):
    """Verify backend constants are correct."""

    def test_eq_node_name(self):
        """EQ node name should be 'mados-eq'."""
        self.assertEqual(EQ_NODE_NAME, 'mados-eq')

    def test_eq_node_description(self):
        """EQ node description should be set."""
        self.assertTrue(len(EQ_NODE_DESCRIPTION) > 0)
        self.assertIn('madOS', EQ_NODE_DESCRIPTION)

    def test_default_q_factor(self):
        """Default Q factor should be a positive number."""
        self.assertIsInstance(DEFAULT_Q, (int, float))
        self.assertGreater(DEFAULT_Q, 0)


# ═══════════════════════════════════════════════════════════════════════════
# Command checking
# ═══════════════════════════════════════════════════════════════════════════
class TestCommandChecking(unittest.TestCase):
    """Test _check_command static method."""

    def test_check_command_uses_which(self):
        """_check_command should use shutil.which."""
        with patch('mados_equalizer.backend.shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/pw-cli'
            result = AudioBackend._check_command('pw-cli')
            self.assertTrue(result)
            mock_which.assert_called_once_with('pw-cli')

    def test_check_command_returns_false_when_not_found(self):
        """_check_command should return False when command not found."""
        with patch('mados_equalizer.backend.shutil.which') as mock_which:
            mock_which.return_value = None
            result = AudioBackend._check_command('nonexistent')
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
