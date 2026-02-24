#!/usr/bin/env python3
"""
Tests for madOS Audio Equalizer preset management.

Validates preset data structures, the PresetManager CRUD operations,
gain clamping, name-to-key sanitization, and JSON serialization.

These tests run in CI without requiring PipeWire or audio hardware.
"""

import sys
import os
import json
import tempfile
import unittest

# ---------------------------------------------------------------------------
# Mock gi / gi.repository so equalizer modules can be imported headlessly.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import install_gtk_mocks
install_gtk_mocks()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_DIR, "airootfs", "usr", "local", "lib")
sys.path.insert(0, LIB_DIR)

from mados_equalizer.presets import (
    FREQUENCY_BANDS,
    BAND_LABELS,
    BAND_KEYS,
    GAIN_MIN,
    GAIN_MAX,
    GAIN_DEFAULT,
    BUILTIN_PRESETS,
    BUILTIN_PRESET_ORDER,
    PresetManager,
)


# ═══════════════════════════════════════════════════════════════════════════
# Constants validation
# ═══════════════════════════════════════════════════════════════════════════
class TestFrequencyBands(unittest.TestCase):
    """Verify frequency band constants are correct."""

    def test_eight_bands(self):
        self.assertEqual(len(FREQUENCY_BANDS), 8)

    def test_ascending_order(self):
        for i in range(len(FREQUENCY_BANDS) - 1):
            self.assertLess(FREQUENCY_BANDS[i], FREQUENCY_BANDS[i + 1])

    def test_labels_count(self):
        self.assertEqual(len(BAND_LABELS), 8)

    def test_keys_count(self):
        self.assertEqual(len(BAND_KEYS), 8)

    def test_gain_range(self):
        self.assertLess(GAIN_MIN, GAIN_DEFAULT)
        self.assertGreater(GAIN_MAX, GAIN_DEFAULT)
        self.assertEqual(GAIN_DEFAULT, 0.0)


# ═══════════════════════════════════════════════════════════════════════════
# Built-in presets
# ═══════════════════════════════════════════════════════════════════════════
class TestBuiltinPresets(unittest.TestCase):
    """Verify all built-in presets are valid."""

    def test_preset_count(self):
        self.assertEqual(len(BUILTIN_PRESETS), 10)

    def test_order_matches_presets(self):
        for key in BUILTIN_PRESET_ORDER:
            with self.subTest(key=key):
                self.assertIn(key, BUILTIN_PRESETS)

    def test_all_have_eight_gains(self):
        for key, preset in BUILTIN_PRESETS.items():
            with self.subTest(key=key):
                self.assertEqual(len(preset["gains"]), 8)

    def test_all_marked_builtin(self):
        for key, preset in BUILTIN_PRESETS.items():
            with self.subTest(key=key):
                self.assertTrue(preset["builtin"])

    def test_all_have_name(self):
        for key, preset in BUILTIN_PRESETS.items():
            with self.subTest(key=key):
                self.assertGreater(len(preset["name"]), 0)

    def test_gains_within_range(self):
        for key, preset in BUILTIN_PRESETS.items():
            for i, gain in enumerate(preset["gains"]):
                with self.subTest(key=key, band=i):
                    self.assertGreaterEqual(gain, GAIN_MIN)
                    self.assertLessEqual(gain, GAIN_MAX)

    def test_flat_is_all_zeros(self):
        flat = BUILTIN_PRESETS["flat"]["gains"]
        self.assertEqual(flat, [0, 0, 0, 0, 0, 0, 0, 0])

    def test_key_matches_dict_key(self):
        for key, preset in BUILTIN_PRESETS.items():
            with self.subTest(key=key):
                self.assertEqual(preset["key"], key)


# ═══════════════════════════════════════════════════════════════════════════
# Name-to-key sanitization
# ═══════════════════════════════════════════════════════════════════════════
class TestNameToKey(unittest.TestCase):
    """Verify PresetManager._name_to_key() sanitization."""

    def test_simple_name(self):
        self.assertEqual(PresetManager._name_to_key("Rock"), "rock")

    def test_spaces_to_underscores(self):
        self.assertEqual(PresetManager._name_to_key("Bass Boost"), "bass_boost")

    def test_special_chars_removed(self):
        self.assertEqual(PresetManager._name_to_key("My Preset!@#"), "my_preset")

    def test_leading_trailing_spaces(self):
        self.assertEqual(PresetManager._name_to_key("  test  "), "test")

    def test_empty_name(self):
        self.assertEqual(PresetManager._name_to_key(""), "unnamed")

    def test_only_special_chars(self):
        self.assertEqual(PresetManager._name_to_key("!@#$%"), "unnamed")

    def test_unicode_alphanumeric(self):
        result = PresetManager._name_to_key("Preset 123")
        self.assertEqual(result, "preset_123")


# ═══════════════════════════════════════════════════════════════════════════
# PresetManager with temporary config directory
# ═══════════════════════════════════════════════════════════════════════════
class TestPresetManagerOperations(unittest.TestCase):
    """Test PresetManager CRUD operations using a temporary directory."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = PresetManager.__new__(PresetManager)
        from pathlib import Path

        self.manager.config_dir = Path(self.tmpdir)
        self.manager.presets_file = self.manager.config_dir / "presets.json"
        self.manager.custom_presets = {}

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_builtin_presets(self):
        presets = self.manager.get_builtin_presets()
        self.assertEqual(len(presets), 10)

    def test_get_custom_presets_empty(self):
        presets = self.manager.get_custom_presets()
        self.assertEqual(presets, [])

    def test_get_all_presets_only_builtin(self):
        presets = self.manager.get_all_presets()
        self.assertEqual(len(presets), 10)

    def test_get_preset_builtin(self):
        preset = self.manager.get_preset("rock")
        self.assertIsNotNone(preset)
        self.assertEqual(preset["name"], "Rock")

    def test_get_preset_nonexistent(self):
        self.assertIsNone(self.manager.get_preset("nonexistent"))

    def test_save_custom_preset(self):
        gains = [1, 2, 3, 4, 5, 6, 7, 8]
        success, msg, key = self.manager.save_custom_preset("My Preset", gains)
        self.assertTrue(success)
        self.assertEqual(msg, "preset_saved")
        self.assertEqual(key, "my_preset")
        self.assertIn("my_preset", self.manager.custom_presets)

    def test_save_persists_to_disk(self):
        gains = [0] * 8
        self.manager.save_custom_preset("Disk Test", gains)
        self.assertTrue(self.manager.presets_file.exists())
        with open(self.manager.presets_file) as f:
            data = json.load(f)
        self.assertIn("disk_test", data)

    def test_save_empty_name_rejected(self):
        success, _, _ = self.manager.save_custom_preset("", [0] * 8)
        self.assertFalse(success)

    def test_save_whitespace_name_rejected(self):
        success, _, _ = self.manager.save_custom_preset("   ", [0] * 8)
        self.assertFalse(success)

    def test_save_builtin_name_rejected(self):
        """Cannot overwrite a built-in preset."""
        success, msg, _ = self.manager.save_custom_preset("Rock", [0] * 8)
        self.assertFalse(success)
        self.assertEqual(msg, "preset_exists")

    def test_save_invalid_gains_length(self):
        success, _, _ = self.manager.save_custom_preset("Bad", [0, 0])
        self.assertFalse(success)

    def test_save_gains_clamped(self):
        """Gains outside [-12, 12] should be clamped."""
        gains = [20, -20, 0, 0, 0, 0, 0, 0]
        success, _, key = self.manager.save_custom_preset("Clamped", gains)
        self.assertTrue(success)
        saved_gains = self.manager.custom_presets[key]["gains"]
        self.assertEqual(saved_gains[0], GAIN_MAX)
        self.assertEqual(saved_gains[1], GAIN_MIN)

    def test_delete_custom_preset(self):
        self.manager.save_custom_preset("ToDelete", [0] * 8)
        success, _ = self.manager.delete_custom_preset("todelete")
        self.assertTrue(success)
        self.assertNotIn("todelete", self.manager.custom_presets)

    def test_delete_builtin_rejected(self):
        success, _ = self.manager.delete_custom_preset("rock")
        self.assertFalse(success)

    def test_delete_nonexistent_rejected(self):
        success, _ = self.manager.delete_custom_preset("nope")
        self.assertFalse(success)

    def test_is_builtin(self):
        self.assertTrue(self.manager.is_builtin("rock"))
        self.assertFalse(self.manager.is_builtin("custom"))

    def test_preset_exists_builtin(self):
        self.assertTrue(self.manager.preset_exists("Rock"))

    def test_preset_exists_custom(self):
        self.manager.save_custom_preset("Custom One", [0] * 8)
        self.assertTrue(self.manager.preset_exists("Custom One"))

    def test_preset_exists_no(self):
        self.assertFalse(self.manager.preset_exists("Does Not Exist"))

    def test_get_flat_gains(self):
        gains = self.manager.get_flat_gains()
        self.assertEqual(gains, [0.0] * 8)

    def test_custom_presets_sorted_by_name(self):
        self.manager.save_custom_preset("Zebra", [0] * 8)
        self.manager.save_custom_preset("Alpha", [1] * 8)
        self.manager.save_custom_preset("Middle", [2] * 8)
        custom = self.manager.get_custom_presets()
        names = [p["name"] for p in custom]
        self.assertEqual(names, ["Alpha", "Middle", "Zebra"])

    def test_all_presets_builtin_first(self):
        self.manager.save_custom_preset("Custom", [0] * 8)
        all_presets = self.manager.get_all_presets()
        # First 10 should be builtin
        for i in range(10):
            self.assertTrue(all_presets[i]["builtin"])
        # Last should be custom
        self.assertFalse(all_presets[-1]["builtin"])


class TestPresetManagerLoadFromDisk(unittest.TestCase):
    """Test PresetManager loading presets from JSON files."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_manager_with_file(self, data):
        from pathlib import Path

        presets_file = Path(self.tmpdir) / "presets.json"
        with open(presets_file, "w") as f:
            json.dump(data, f)
        manager = PresetManager.__new__(PresetManager)
        manager.config_dir = Path(self.tmpdir)
        manager.presets_file = presets_file
        manager.custom_presets = {}
        manager._load_custom_presets()
        return manager

    def test_load_valid_presets(self):
        data = {
            "my_preset": {
                "name": "My Preset",
                "gains": [1, 2, 3, 4, 5, 6, 7, 8],
            }
        }
        manager = self._create_manager_with_file(data)
        self.assertIn("my_preset", manager.custom_presets)
        self.assertEqual(
            manager.custom_presets["my_preset"]["gains"],
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        )

    def test_load_clamps_out_of_range(self):
        data = {
            "extreme": {
                "name": "Extreme",
                "gains": [100, -100, 0, 0, 0, 0, 0, 0],
            }
        }
        manager = self._create_manager_with_file(data)
        gains = manager.custom_presets["extreme"]["gains"]
        self.assertEqual(gains[0], GAIN_MAX)
        self.assertEqual(gains[1], GAIN_MIN)

    def test_load_skips_invalid_gains_length(self):
        data = {
            "bad": {
                "name": "Bad",
                "gains": [0, 0],
            }
        }
        manager = self._create_manager_with_file(data)
        self.assertNotIn("bad", manager.custom_presets)

    def test_load_skips_missing_gains(self):
        data = {
            "bad": {
                "name": "Bad",
            }
        }
        manager = self._create_manager_with_file(data)
        self.assertNotIn("bad", manager.custom_presets)

    def test_load_corrupt_json(self):
        from pathlib import Path

        presets_file = Path(self.tmpdir) / "presets.json"
        with open(presets_file, "w") as f:
            f.write("not valid json{{{")
        manager = PresetManager.__new__(PresetManager)
        manager.config_dir = Path(self.tmpdir)
        manager.presets_file = presets_file
        manager.custom_presets = {}
        manager._load_custom_presets()
        self.assertEqual(manager.custom_presets, {})

    def test_load_nonexistent_file(self):
        from pathlib import Path

        manager = PresetManager.__new__(PresetManager)
        manager.config_dir = Path(self.tmpdir)
        manager.presets_file = Path(self.tmpdir) / "nonexistent.json"
        manager.custom_presets = {}
        manager._load_custom_presets()
        self.assertEqual(manager.custom_presets, {})

    def test_loaded_presets_marked_not_builtin(self):
        data = {
            "custom": {
                "name": "Custom",
                "gains": [0] * 8,
            }
        }
        manager = self._create_manager_with_file(data)
        self.assertFalse(manager.custom_presets["custom"]["builtin"])


if __name__ == "__main__":
    unittest.main()
