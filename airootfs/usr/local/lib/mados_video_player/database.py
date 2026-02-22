"""
madOS Video Player - SQLite Playlist Database
===============================================

Persists playlists using SQLite. Each saved playlist has a name and an
ordered list of file paths. The database also stores the "current" session
state (last active playlist, position, repeat/shuffle preferences).

Database location: ``~/.local/share/mados-video-player/playlists.db``
"""

import os
import sqlite3
from contextlib import contextmanager

# Default database path
DEFAULT_DB_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "mados-video-player",
)
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "playlists.db")

# Schema version — bump when altering tables
_SCHEMA_VERSION = 1


class PlaylistDB:
    """SQLite-backed playlist persistence.

    Manages saved playlists and session state for the video player.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ``~/.local/share/mados-video-player/playlists.db``.
    """

    def __init__(self, db_path=None):
        self._db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
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
                CREATE TABLE IF NOT EXISTS playlists (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL UNIQUE,
                    created_at  TEXT    DEFAULT (datetime('now')),
                    updated_at  TEXT    DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS playlist_items (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    position    INTEGER NOT NULL,
                    filepath    TEXT    NOT NULL,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                    UNIQUE (playlist_id, position)
                );

                CREATE TABLE IF NOT EXISTS session (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

    # ------------------------------------------------------------------
    # Playlist CRUD
    # ------------------------------------------------------------------

    def list_playlists(self):
        """Return a list of all saved playlist names, sorted alphabetically.

        Returns:
            List of (id, name) tuples.
        """
        cur = self._conn.execute(
            "SELECT id, name FROM playlists ORDER BY name"
        )
        return cur.fetchall()

    def save_playlist(self, name, filepaths):
        """Save (create or overwrite) a named playlist.

        Args:
            name: Playlist name.
            filepaths: Ordered list of absolute file paths.
        """
        with self._transaction():
            # Upsert playlist row
            self._conn.execute(
                """INSERT INTO playlists (name) VALUES (?)
                   ON CONFLICT(name) DO UPDATE SET updated_at=datetime('now')""",
                (name,),
            )
            playlist_id = self._conn.execute(
                "SELECT id FROM playlists WHERE name=?", (name,)
            ).fetchone()[0]

            # Replace items
            self._conn.execute(
                "DELETE FROM playlist_items WHERE playlist_id=?", (playlist_id,)
            )
            self._conn.executemany(
                "INSERT INTO playlist_items (playlist_id, position, filepath) VALUES (?, ?, ?)",
                [(playlist_id, i, fp) for i, fp in enumerate(filepaths)],
            )

    def load_playlist(self, name):
        """Load a saved playlist by name.

        Args:
            name: Playlist name.

        Returns:
            Ordered list of file paths, or None if not found.
        """
        row = self._conn.execute(
            "SELECT id FROM playlists WHERE name=?", (name,)
        ).fetchone()
        if row is None:
            return None
        playlist_id = row[0]
        cur = self._conn.execute(
            "SELECT filepath FROM playlist_items WHERE playlist_id=? ORDER BY position",
            (playlist_id,),
        )
        return [r[0] for r in cur.fetchall()]

    def delete_playlist(self, name):
        """Delete a saved playlist.

        Args:
            name: Playlist name.

        Returns:
            True if deleted, False if not found.
        """
        with self._transaction():
            cur = self._conn.execute(
                "DELETE FROM playlists WHERE name=?", (name,)
            )
            return cur.rowcount > 0

    def rename_playlist(self, old_name, new_name):
        """Rename a saved playlist.

        Args:
            old_name: Current name.
            new_name: New name.

        Returns:
            True if renamed, False if not found or new_name already exists.
        """
        try:
            with self._transaction():
                cur = self._conn.execute(
                    "UPDATE playlists SET name=?, updated_at=datetime('now') WHERE name=?",
                    (new_name, old_name),
                )
                return cur.rowcount > 0
        except sqlite3.IntegrityError:
            return False

    # ------------------------------------------------------------------
    # Session state
    # ------------------------------------------------------------------

    def set_session(self, key, value):
        """Store a session key-value pair.

        Args:
            key: Session key (e.g. 'last_playlist', 'repeat_mode').
            value: String value.
        """
        with self._transaction():
            self._conn.execute(
                "INSERT OR REPLACE INTO session (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

    def get_session(self, key, default=None):
        """Retrieve a session value.

        Args:
            key: Session key.
            default: Value to return if key is not found.

        Returns:
            The stored value as a string, or *default*.
        """
        row = self._conn.execute(
            "SELECT value FROM session WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else default

    # ------------------------------------------------------------------
    # Convenience: quick-save / quick-load session playlist
    # ------------------------------------------------------------------

    _SESSION_PLAYLIST_NAME = "__session__"

    def save_session_playlist(self, filepaths, current_index=-1,
                              repeat_mode="none", shuffle=False):
        """Persist the current session playlist and state.

        Called automatically when the player closes so the playlist
        is restored on next launch.

        Args:
            filepaths: Ordered list of file paths.
            current_index: Currently playing index.
            repeat_mode: Repeat mode string.
            shuffle: Shuffle enabled.
        """
        self.save_playlist(self._SESSION_PLAYLIST_NAME, filepaths)
        self.set_session("current_index", str(current_index))
        self.set_session("repeat_mode", repeat_mode)
        self.set_session("shuffle", "1" if shuffle else "0")

    def load_session_playlist(self):
        """Restore the last session playlist and state.

        Returns:
            A dict with keys ``filepaths``, ``current_index``,
            ``repeat_mode``, ``shuffle``; or None if no session exists.
        """
        filepaths = self.load_playlist(self._SESSION_PLAYLIST_NAME)
        if filepaths is None:
            return None
        return {
            "filepaths": filepaths,
            "current_index": int(self.get_session("current_index", "-1")),
            "repeat_mode": self.get_session("repeat_mode", "none"),
            "shuffle": self.get_session("shuffle", "0") == "1",
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
