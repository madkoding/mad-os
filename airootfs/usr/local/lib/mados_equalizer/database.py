"""
madOS Audio Equalizer - SQLite State Persistence
==================================================

Persists equalizer session state using SQLite so that gain values,
enabled state, selected preset, and language preference survive
across application restarts.

Database location: ``~/.local/share/mados-equalizer/state.db``
"""

import os
import sqlite3
from contextlib import contextmanager


# Default database path following XDG Base Directory Specification
DEFAULT_DB_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "mados-equalizer",
)
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "state.db")

# Schema version — bump when altering tables
_SCHEMA_VERSION = 1


class EqualizerStateDB:
    """SQLite-backed state persistence for the equalizer.

    Stores session state as key-value pairs and band gains as a
    separate table for efficient per-band updates.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ``~/.local/share/mados-equalizer/state.db``.
    """

    def __init__(self, db_path=None):
        self._db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, timeout=5)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    @contextmanager
    def _transaction(self):
        """Context manager for a database transaction."""
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _create_tables(self):
        """Initialize the database schema."""
        with self._transaction():
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS session (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS band_gains (
                    band  INTEGER PRIMARY KEY,
                    gain  REAL NOT NULL DEFAULT 0.0
                );
            """)

    # ----- session key-value helpers -----

    def _get_session(self, key, default=None):
        """Retrieve a session value by key.

        Args:
            key: The session key.
            default: Value to return if key is missing.

        Returns:
            The stored value as a string, or *default*.
        """
        cur = self._conn.execute(
            "SELECT value FROM session WHERE key = ?", (key,)
        )
        row = cur.fetchone()
        return row[0] if row else default

    def _set_session(self, key, value):
        """Store a session key-value pair (upsert).

        Args:
            key: The session key.
            value: The value to store (will be converted to string).
        """
        with self._transaction():
            self._conn.execute(
                "INSERT INTO session (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    # ----- public API -----

    def save_gains(self, gains):
        """Persist the 8-band gain values.

        Args:
            gains: List of 8 float gain values in dB.
        """
        if not isinstance(gains, (list, tuple)) or len(gains) != 8:
            return
        with self._transaction():
            self._conn.execute("DELETE FROM band_gains")
            self._conn.executemany(
                "INSERT INTO band_gains (band, gain) VALUES (?, ?)",
                [(i, float(g)) for i, g in enumerate(gains)],
            )

    def load_gains(self):
        """Load the persisted 8-band gain values.

        Returns:
            List of 8 float gain values, or None if no saved state.
        """
        cur = self._conn.execute(
            "SELECT band, gain FROM band_gains ORDER BY band"
        )
        rows = cur.fetchall()
        if len(rows) != 8:
            return None
        return [row[1] for row in rows]

    def save_enabled(self, enabled):
        """Persist the EQ enabled/disabled state.

        Args:
            enabled: True if the equalizer is active.
        """
        self._set_session("enabled", "1" if enabled else "0")

    def load_enabled(self):
        """Load the persisted EQ enabled state.

        Returns:
            True if the equalizer was enabled, False otherwise.
        """
        val = self._get_session("enabled", "0")
        return val == "1"

    def save_preset(self, preset_key):
        """Persist the selected preset key.

        Args:
            preset_key: The key of the active preset (e.g. 'rock').
        """
        self._set_session("preset", preset_key or "")

    def load_preset(self):
        """Load the persisted preset key.

        Returns:
            The preset key string, or None if not saved.
        """
        val = self._get_session("preset")
        return val if val else None

    def save_language(self, language):
        """Persist the UI language preference.

        Args:
            language: Language code (e.g. 'en', 'es').
        """
        self._set_session("language", language or "")

    def load_language(self):
        """Load the persisted language preference.

        Returns:
            The language code string, or None if not saved.
        """
        val = self._get_session("language")
        return val if val else None

    def save_state(self, gains, enabled, preset_key, language):
        """Persist the full equalizer state in a single transaction.

        Args:
            gains: List of 8 float gain values in dB.
            enabled: Whether the EQ is active.
            preset_key: The active preset key.
            language: The UI language code.
        """
        with self._transaction():
            # Gains
            if isinstance(gains, (list, tuple)) and len(gains) == 8:
                self._conn.execute("DELETE FROM band_gains")
                self._conn.executemany(
                    "INSERT INTO band_gains (band, gain) VALUES (?, ?)",
                    [(i, float(g)) for i, g in enumerate(gains)],
                )

            # Session values
            for key, value in [
                ("enabled", "1" if enabled else "0"),
                ("preset", preset_key or ""),
                ("language", language or ""),
            ]:
                self._conn.execute(
                    "INSERT INTO session (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, str(value)),
                )

    def load_state(self):
        """Load the full persisted equalizer state.

        Returns:
            Dictionary with keys: gains, enabled, preset, language.
            Values are None/default when not previously saved.
        """
        return {
            "gains": self.load_gains(),
            "enabled": self.load_enabled(),
            "preset": self.load_preset(),
            "language": self.load_language(),
        }

    def close(self):
        """Close the database connection."""
        try:
            self._conn.close()
        except Exception:
            pass
