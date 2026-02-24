#!/usr/bin/env python3
"""
Tests for madOS Audio Equalizer SQLite state persistence.

Validates the EqualizerStateDB class: schema creation, gain storage,
session key-value persistence, full state save/load round-trips,
and edge-case handling (corrupt DB, missing data, type coercion).

These tests run in CI without requiring PipeWire or audio hardware.
"""

import sys
import os
import tempfile
import shutil
import sqlite3
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

from mados_equalizer.database import EqualizerStateDB, DEFAULT_DB_PATH


# ═══════════════════════════════════════════════════════════════════════════
# Default path validation
# ═══════════════════════════════════════════════════════════════════════════
class TestDefaultPath(unittest.TestCase):
    """Verify the default database path follows XDG conventions."""

    def test_default_db_path_under_local_share(self):
        """Default path should be under ~/.local/share/mados-equalizer."""
        self.assertIn("mados-equalizer", DEFAULT_DB_PATH)
        self.assertTrue(DEFAULT_DB_PATH.endswith("state.db"))

    def test_default_db_path_has_no_config_dir(self):
        """Database should not live in .config (that's for config files)."""
        self.assertNotIn(".config", DEFAULT_DB_PATH)


# ═══════════════════════════════════════════════════════════════════════════
# Schema creation
# ═══════════════════════════════════════════════════════════════════════════
class TestSchemaCreation(unittest.TestCase):
    """Verify tables are created correctly."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = EqualizerStateDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_session_table_exists(self):
        cur = self.db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='session'"
        )
        self.assertIsNotNone(cur.fetchone())

    def test_band_gains_table_exists(self):
        cur = self.db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='band_gains'"
        )
        self.assertIsNotNone(cur.fetchone())

    def test_journal_mode_wal(self):
        cur = self.db._conn.execute("PRAGMA journal_mode")
        mode = cur.fetchone()[0]
        self.assertEqual(mode.lower(), "wal")

    def test_opening_same_db_twice_does_not_crash(self):
        """Re-creating tables on an existing DB should be idempotent."""
        db2 = EqualizerStateDB(self.db_path)
        db2.close()


# ═══════════════════════════════════════════════════════════════════════════
# Gains persistence
# ═══════════════════════════════════════════════════════════════════════════
class TestGainsPersistence(unittest.TestCase):
    """Test saving and loading band gains."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = EqualizerStateDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_gains_empty(self):
        """With no saved gains, load_gains returns None."""
        self.assertIsNone(self.db.load_gains())

    def test_save_and_load_flat_gains(self):
        gains = [0.0] * 8
        self.db.save_gains(gains)
        loaded = self.db.load_gains()
        self.assertEqual(loaded, gains)

    def test_save_and_load_varied_gains(self):
        gains = [4.0, 3.0, 1.0, 0.0, -1.0, 1.5, 3.5, -6.0]
        self.db.save_gains(gains)
        loaded = self.db.load_gains()
        self.assertEqual(loaded, gains)

    def test_save_overwrites_previous(self):
        self.db.save_gains([1.0] * 8)
        self.db.save_gains([2.0] * 8)
        loaded = self.db.load_gains()
        self.assertEqual(loaded, [2.0] * 8)

    def test_save_invalid_length_is_noop(self):
        self.db.save_gains([1.0, 2.0])  # Too few
        self.assertIsNone(self.db.load_gains())

    def test_save_non_list_is_noop(self):
        self.db.save_gains("not a list")
        self.assertIsNone(self.db.load_gains())

    def test_gains_persist_across_connections(self):
        gains = [5.0, -3.0, 2.0, 0.0, 1.0, -1.0, 4.0, -4.0]
        self.db.save_gains(gains)
        self.db.close()

        db2 = EqualizerStateDB(self.db_path)
        loaded = db2.load_gains()
        db2.close()
        self.assertEqual(loaded, gains)

    def test_float_precision_preserved(self):
        gains = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        self.db.save_gains(gains)
        loaded = self.db.load_gains()
        for expected, actual in zip(gains, loaded):
            self.assertAlmostEqual(expected, actual, places=5)


# ═══════════════════════════════════════════════════════════════════════════
# Enabled state persistence
# ═══════════════════════════════════════════════════════════════════════════
class TestEnabledPersistence(unittest.TestCase):
    """Test saving and loading the enabled state."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = EqualizerStateDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_enabled_is_false(self):
        self.assertFalse(self.db.load_enabled())

    def test_save_enabled_true(self):
        self.db.save_enabled(True)
        self.assertTrue(self.db.load_enabled())

    def test_save_enabled_false(self):
        self.db.save_enabled(True)
        self.db.save_enabled(False)
        self.assertFalse(self.db.load_enabled())

    def test_enabled_persists_across_connections(self):
        self.db.save_enabled(True)
        self.db.close()
        db2 = EqualizerStateDB(self.db_path)
        self.assertTrue(db2.load_enabled())
        db2.close()


# ═══════════════════════════════════════════════════════════════════════════
# Preset persistence
# ═══════════════════════════════════════════════════════════════════════════
class TestPresetPersistence(unittest.TestCase):
    """Test saving and loading the active preset key."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = EqualizerStateDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_preset_is_none(self):
        self.assertIsNone(self.db.load_preset())

    def test_save_and_load_preset(self):
        self.db.save_preset("rock")
        self.assertEqual(self.db.load_preset(), "rock")

    def test_save_custom_preset_key(self):
        self.db.save_preset("my_custom_preset")
        self.assertEqual(self.db.load_preset(), "my_custom_preset")

    def test_save_empty_string_returns_none(self):
        self.db.save_preset("")
        self.assertIsNone(self.db.load_preset())

    def test_save_none_returns_none(self):
        self.db.save_preset(None)
        self.assertIsNone(self.db.load_preset())


# ═══════════════════════════════════════════════════════════════════════════
# Language persistence
# ═══════════════════════════════════════════════════════════════════════════
class TestLanguagePersistence(unittest.TestCase):
    """Test saving and loading the language preference."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = EqualizerStateDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_language_is_none(self):
        self.assertIsNone(self.db.load_language())

    def test_save_and_load_language(self):
        self.db.save_language("es")
        self.assertEqual(self.db.load_language(), "es")

    def test_save_empty_string_returns_none(self):
        self.db.save_language("")
        self.assertIsNone(self.db.load_language())


# ═══════════════════════════════════════════════════════════════════════════
# Full state round-trip
# ═══════════════════════════════════════════════════════════════════════════
class TestFullStateRoundTrip(unittest.TestCase):
    """Test save_state / load_state for complete round-trip persistence."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = EqualizerStateDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_load_full_state(self):
        gains = [4.0, 3.0, 1.0, 0.0, -1.0, 1.0, 3.0, 4.0]
        self.db.save_state(
            gains=gains,
            enabled=True,
            preset_key="rock",
            language="es",
        )

        state = self.db.load_state()
        self.assertEqual(state["gains"], gains)
        self.assertTrue(state["enabled"])
        self.assertEqual(state["preset"], "rock")
        self.assertEqual(state["language"], "es")

    def test_full_state_persists_across_connections(self):
        gains = [6.0, 5.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0]
        self.db.save_state(
            gains=gains,
            enabled=True,
            preset_key="bass_boost",
            language="en",
        )
        self.db.close()

        db2 = EqualizerStateDB(self.db_path)
        state = db2.load_state()
        db2.close()

        self.assertEqual(state["gains"], gains)
        self.assertTrue(state["enabled"])
        self.assertEqual(state["preset"], "bass_boost")
        self.assertEqual(state["language"], "en")

    def test_full_state_with_disabled_eq(self):
        gains = [0.0] * 8
        self.db.save_state(
            gains=gains,
            enabled=False,
            preset_key="flat",
            language="de",
        )

        state = self.db.load_state()
        self.assertFalse(state["enabled"])

    def test_empty_state_when_no_data_saved(self):
        state = self.db.load_state()
        self.assertIsNone(state["gains"])
        self.assertFalse(state["enabled"])
        self.assertIsNone(state["preset"])
        self.assertIsNone(state["language"])

    def test_save_state_with_none_preset(self):
        self.db.save_state(
            gains=[0.0] * 8,
            enabled=False,
            preset_key=None,
            language="en",
        )
        state = self.db.load_state()
        self.assertIsNone(state["preset"])

    def test_save_state_overwrites_previous(self):
        self.db.save_state([1.0] * 8, True, "rock", "en")
        self.db.save_state([2.0] * 8, False, "pop", "es")

        state = self.db.load_state()
        self.assertEqual(state["gains"], [2.0] * 8)
        self.assertFalse(state["enabled"])
        self.assertEqual(state["preset"], "pop")
        self.assertEqual(state["language"], "es")


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════
class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_close_is_idempotent(self):
        db = EqualizerStateDB(self.db_path)
        db.close()
        db.close()  # Should not raise

    def test_create_in_nonexistent_directory(self):
        deep_path = os.path.join(self.tmpdir, "a", "b", "c", "test.db")
        db = EqualizerStateDB(deep_path)
        db.save_enabled(True)
        self.assertTrue(db.load_enabled())
        db.close()

    def test_save_gains_with_integer_values(self):
        """Integer gain values should be stored and returned as floats."""
        db = EqualizerStateDB(self.db_path)
        db.save_gains([1, 2, 3, 4, 5, 6, 7, 8])
        loaded = db.load_gains()
        self.assertEqual(loaded, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        db.close()

    def test_individual_setters_compose_with_load_state(self):
        """Using individual save methods should be visible via load_state."""
        db = EqualizerStateDB(self.db_path)
        db.save_gains([3.0] * 8)
        db.save_enabled(True)
        db.save_preset("jazz")
        db.save_language("fr")

        state = db.load_state()
        self.assertEqual(state["gains"], [3.0] * 8)
        self.assertTrue(state["enabled"])
        self.assertEqual(state["preset"], "jazz")
        self.assertEqual(state["language"], "fr")
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# Database module structure
# ═══════════════════════════════════════════════════════════════════════════
class TestDatabaseModuleStructure(unittest.TestCase):
    """Verify the database module has required attributes."""

    def test_module_has_default_db_path(self):
        from mados_equalizer import database
        self.assertTrue(hasattr(database, "DEFAULT_DB_PATH"))

    def test_module_has_default_db_dir(self):
        from mados_equalizer import database
        self.assertTrue(hasattr(database, "DEFAULT_DB_DIR"))

    def test_class_has_public_api(self):
        """EqualizerStateDB must expose the required public methods."""
        required = [
            "save_gains", "load_gains",
            "save_enabled", "load_enabled",
            "save_preset", "load_preset",
            "save_language", "load_language",
            "save_state", "load_state",
            "close",
        ]
        for method_name in required:
            self.assertTrue(
                hasattr(EqualizerStateDB, method_name),
                f"Missing method: {method_name}",
            )

    def test_uses_sqlite3(self):
        """Database module must use sqlite3."""
        import inspect
        from mados_equalizer import database
        source = inspect.getsource(database)
        self.assertIn("sqlite3", source)


if __name__ == "__main__":
    unittest.main()
