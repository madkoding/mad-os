"""
madOS Audio Player - SQLite Database Layer
===========================================

Provides persistent storage for playlists and player state using
SQLite. The database is stored in the user's XDG data directory
(~/.local/share/mados-audio-player/playlists.db).

Schema:
    playlists  — Named playlists (id, name, created_at)
    tracks     — Tracks within playlists (position-ordered)
    settings   — Key/value store for player state
"""

import os
import sqlite3
import time


# Default database location following XDG Base Directory spec
def _default_db_path():
    """Compute the default database path.

    Returns:
        Absolute path to the SQLite database file.
    """
    xdg_data = os.environ.get(
        "XDG_DATA_HOME",
        os.path.join(os.path.expanduser("~"), ".local", "share"),
    )
    db_dir = os.path.join(xdg_data, "mados-audio-player")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "playlists.db")


# Default playlist name
DEFAULT_PLAYLIST = "Default"

# Schema version for future migrations
SCHEMA_VERSION = 1


class PlaylistDB:
    """SQLite database manager for playlists and player state.

    Handles all database operations: creating/deleting playlists,
    adding/removing/reordering tracks, and storing player settings.

    Args:
        db_path: Path to the SQLite database file.
                 Use ':memory:' for in-memory databases (tests).
                 Defaults to XDG data directory.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or _default_db_path()
        self._conn = None
        self._connect()
        self._init_schema()

    def _connect(self):
        """Open a connection to the SQLite database."""
        self._conn = sqlite3.connect(self.db_path, timeout=5)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row

    def _init_schema(self):
        """Create tables if they don't exist."""
        with self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL UNIQUE,
                    created_at  REAL    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tracks (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    position    INTEGER NOT NULL,
                    filepath    TEXT    NOT NULL,
                    title       TEXT    DEFAULT '',
                    artist      TEXT    DEFAULT '',
                    album       TEXT    DEFAULT '',
                    duration    REAL    DEFAULT 0.0,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tracks_playlist
                    ON tracks(playlist_id, position);

                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

    # ─── Playlist CRUD ──────────────────────────────────────────

    def create_playlist(self, name=DEFAULT_PLAYLIST):
        """Create a new playlist.

        Args:
            name: Playlist name (must be unique).

        Returns:
            The new playlist's row id, or existing id if name exists.
        """
        try:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO playlists (name, created_at) VALUES (?, ?)",
                    (name, time.time()),
                )
                return cur.lastrowid
        except sqlite3.IntegrityError:
            row = self._conn.execute(
                "SELECT id FROM playlists WHERE name = ?", (name,)
            ).fetchone()
            return row["id"] if row else None

    def get_playlist_id(self, name=DEFAULT_PLAYLIST):
        """Get a playlist id by name, creating it if needed.

        Args:
            name: Playlist name.

        Returns:
            Integer playlist id.
        """
        row = self._conn.execute(
            "SELECT id FROM playlists WHERE name = ?", (name,)
        ).fetchone()
        if row:
            return row["id"]
        return self.create_playlist(name)

    def list_playlists(self):
        """List all playlist names.

        Returns:
            List of (id, name) tuples ordered by creation time.
        """
        rows = self._conn.execute(
            "SELECT id, name FROM playlists ORDER BY created_at"
        ).fetchall()
        return [(r["id"], r["name"]) for r in rows]

    def rename_playlist(self, playlist_id, new_name):
        """Rename a playlist.

        Args:
            playlist_id: The playlist row id.
            new_name: The new name.

        Returns:
            True if renamed, False on conflict.
        """
        try:
            with self._conn:
                self._conn.execute(
                    "UPDATE playlists SET name = ? WHERE id = ?",
                    (new_name, playlist_id),
                )
                return True
        except sqlite3.IntegrityError:
            return False

    def delete_playlist(self, playlist_id):
        """Delete a playlist and all its tracks.

        Args:
            playlist_id: The playlist row id.
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM playlists WHERE id = ?", (playlist_id,)
            )

    def playlist_exists(self, name):
        """Check if a playlist with the given name exists.

        Args:
            name: Playlist name.

        Returns:
            True if exists.
        """
        row = self._conn.execute(
            "SELECT 1 FROM playlists WHERE name = ?", (name,)
        ).fetchone()
        return row is not None

    # ─── Track Operations ───────────────────────────────────────

    def add_track(self, playlist_id, filepath, title="", artist="",
                  album="", duration=0.0):
        """Append a track to a playlist.

        Args:
            playlist_id: Target playlist id.
            filepath: Absolute path to the audio file.
            title: Track title.
            artist: Artist name.
            album: Album name.
            duration: Duration in seconds.

        Returns:
            The new track row id.
        """
        with self._conn:
            # Get next position
            row = self._conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos "
                "FROM tracks WHERE playlist_id = ?",
                (playlist_id,),
            ).fetchone()
            pos = row["next_pos"]

            cur = self._conn.execute(
                "INSERT INTO tracks "
                "(playlist_id, position, filepath, title, artist, album, duration) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (playlist_id, pos, filepath, title, artist, album, duration),
            )
            return cur.lastrowid

    def get_tracks(self, playlist_id):
        """Get all tracks in a playlist, ordered by position.

        Args:
            playlist_id: The playlist id.

        Returns:
            List of sqlite3.Row objects with track data.
        """
        return self._conn.execute(
            "SELECT id, position, filepath, title, artist, album, duration "
            "FROM tracks WHERE playlist_id = ? ORDER BY position",
            (playlist_id,),
        ).fetchall()

    def get_track_count(self, playlist_id):
        """Get the number of tracks in a playlist.

        Args:
            playlist_id: The playlist id.

        Returns:
            Integer track count.
        """
        row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM tracks WHERE playlist_id = ?",
            (playlist_id,),
        ).fetchone()
        return row["cnt"]

    def update_track_metadata(self, track_id, title=None, artist=None,
                              album=None, duration=None):
        """Update metadata for a specific track.

        Args:
            track_id: The track row id.
            title: New title (or None to skip).
            artist: New artist (or None to skip).
            album: New album (or None to skip).
            duration: New duration (or None to skip).
        """
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if artist is not None:
            updates.append("artist = ?")
            params.append(artist)
        if album is not None:
            updates.append("album = ?")
            params.append(album)
        if duration is not None:
            updates.append("duration = ?")
            params.append(duration)

        if not updates:
            return

        params.append(track_id)
        with self._conn:
            self._conn.execute(
                f"UPDATE tracks SET {', '.join(updates)} WHERE id = ?",
                params,
            )

    def remove_track_at(self, playlist_id, position):
        """Remove a track at a given position and reindex.

        Args:
            playlist_id: The playlist id.
            position: The position (0-based index).

        Returns:
            True if a track was removed.
        """
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM tracks WHERE playlist_id = ? AND position = ?",
                (playlist_id, position),
            )
            if cur.rowcount > 0:
                self._reindex(playlist_id)
                return True
            return False

    def remove_tracks_at(self, playlist_id, positions):
        """Remove multiple tracks by position and reindex.

        Args:
            playlist_id: The playlist id.
            positions: List of positions to remove.
        """
        if not positions:
            return
        with self._conn:
            placeholders = ",".join("?" for _ in positions)
            self._conn.execute(
                f"DELETE FROM tracks WHERE playlist_id = ? "
                f"AND position IN ({placeholders})",
                [playlist_id] + list(positions),
            )
            self._reindex(playlist_id)

    def clear_tracks(self, playlist_id):
        """Remove all tracks from a playlist.

        Args:
            playlist_id: The playlist id.
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM tracks WHERE playlist_id = ?", (playlist_id,)
            )

    def _reindex(self, playlist_id):
        """Reindex track positions after removals (0-based contiguous)."""
        rows = self._conn.execute(
            "SELECT id FROM tracks WHERE playlist_id = ? ORDER BY position",
            (playlist_id,),
        ).fetchall()
        for i, row in enumerate(rows):
            self._conn.execute(
                "UPDATE tracks SET position = ? WHERE id = ?",
                (i, row["id"]),
            )

    # ─── Settings (Player State) ────────────────────────────────

    def get_setting(self, key, default=None):
        """Get a player setting.

        Args:
            key: Setting key name.
            default: Default value if not found.

        Returns:
            Setting value as string, or default.
        """
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is not None:
            return row["value"]
        return default

    def set_setting(self, key, value):
        """Set a player setting.

        Args:
            key: Setting key name.
            value: Value to store (will be converted to string).
        """
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

    def get_int_setting(self, key, default=0):
        """Get a setting as integer.

        Args:
            key: Setting key name.
            default: Default integer value.

        Returns:
            Integer value.
        """
        val = self.get_setting(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
        return default

    def get_bool_setting(self, key, default=False):
        """Get a setting as boolean.

        Args:
            key: Setting key name.
            default: Default boolean value.

        Returns:
            Boolean value.
        """
        val = self.get_setting(key)
        if val is not None:
            return val.lower() in ("1", "true", "yes")
        return default

    # ─── Cleanup ────────────────────────────────────────────────

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self):
        self.close()
