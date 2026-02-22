"""
madOS Audio Player - Playlist Manager (SQLite-backed)
======================================================

Manages playlists with SQLite persistence. Track list, current index,
shuffle and repeat modes are stored in a SQLite database so playlists
survive across sessions.

Public API is identical to the original in-memory implementation:
    - Track class (data model for a single audio track)
    - Playlist class (navigation, shuffle, repeat, CRUD)
    - format_time() helper
    - REPEAT_OFF, REPEAT_ALL, REPEAT_ONE constants
"""

import os
import random

from .database import PlaylistDB, DEFAULT_PLAYLIST


# Repeat modes
REPEAT_OFF = 0
REPEAT_ALL = 1
REPEAT_ONE = 2


class Track:
    """Represents a single audio track in the playlist.

    Attributes:
        filepath: Absolute path to the audio file.
        title: Display title (derived from filename if no metadata).
        artist: Artist name from metadata.
        album: Album name from metadata.
        duration: Track duration in seconds (0 if unknown).
        db_id: SQLite row id for this track (None if not persisted).
    """

    def __init__(self, filepath, db_id=None):
        self.filepath = filepath
        self.title = os.path.splitext(os.path.basename(filepath))[0]
        self.artist = ""
        self.album = ""
        self.duration = 0.0
        self.db_id = db_id

    def update_metadata(self, metadata):
        """Update track metadata from a dict.

        Args:
            metadata: dict with optional 'title', 'artist', 'album' keys.
        """
        if metadata.get('title'):
            self.title = metadata['title']
        if metadata.get('artist'):
            self.artist = metadata['artist']
        if metadata.get('album'):
            self.album = metadata['album']

    def display_name(self):
        """Get a formatted display string for the track.

        Returns:
            'Artist - Title' if artist is known, otherwise just 'Title'.
        """
        if self.artist:
            return f"{self.artist} - {self.title}"
        return self.title

    def __repr__(self):
        return f"Track({self.filepath!r})"

    @classmethod
    def from_db_row(cls, row):
        """Create a Track from a SQLite row.

        Args:
            row: A sqlite3.Row with track columns.

        Returns:
            A Track instance populated from the row.
        """
        t = cls(row["filepath"], db_id=row["id"])
        t.title = row["title"] or os.path.splitext(
            os.path.basename(row["filepath"])
        )[0]
        t.artist = row["artist"] or ""
        t.album = row["album"] or ""
        t.duration = row["duration"] or 0.0
        return t


class Playlist:
    """Manages an ordered list of Track objects with SQLite persistence.

    Supports shuffle, repeat modes, and track management operations.
    All changes are persisted to a SQLite database so the playlist
    and player state survive across sessions.

    Args:
        db_path: Path to the SQLite file (None = default XDG path,
                 ':memory:' for tests).
        playlist_name: Name of the playlist to load/create.
    """

    def __init__(self, db_path=None, playlist_name=DEFAULT_PLAYLIST):
        self._db = PlaylistDB(db_path)
        self._playlist_name = playlist_name
        self._playlist_id = self._db.get_playlist_id(playlist_name)

        # Load tracks from database into in-memory list
        self.tracks = []
        self._load_tracks()

        # Restore player state from database
        self.current_index = self._db.get_int_setting("current_index", -1)
        self.shuffle = self._db.get_bool_setting("shuffle", False)
        self.repeat_mode = self._db.get_int_setting("repeat_mode", REPEAT_OFF)

        # Validate current_index against actual track count
        if self.current_index >= len(self.tracks):
            self.current_index = len(self.tracks) - 1 if self.tracks else -1

        # Shuffle state
        self._shuffle_order = []
        self._shuffle_pos = -1
        if self.shuffle:
            self._regenerate_shuffle()

    def _load_tracks(self):
        """Load tracks from the database into the in-memory list."""
        rows = self._db.get_tracks(self._playlist_id)
        self.tracks = [Track.from_db_row(r) for r in rows]

    def _save_state(self):
        """Persist current player state to the database."""
        self._db.set_setting("current_index", self.current_index)
        self._db.set_setting("shuffle", self.shuffle)
        self._db.set_setting("repeat_mode", self.repeat_mode)
        self._db.set_setting("current_playlist", self._playlist_name)

    # ─── Playlist management ────────────────────────────────────

    @property
    def playlist_name(self):
        """Name of the currently active playlist."""
        return self._playlist_name

    def list_playlists(self):
        """List all saved playlists.

        Returns:
            List of (id, name) tuples.
        """
        return self._db.list_playlists()

    def switch_playlist(self, name):
        """Switch to a different playlist (create if needed).

        Args:
            name: Name of the playlist to switch to.
        """
        self._save_state()
        self._playlist_name = name
        self._playlist_id = self._db.get_playlist_id(name)
        self._load_tracks()
        self.current_index = -1
        self._shuffle_order = []
        self._shuffle_pos = -1
        self._save_state()

    def rename_playlist(self, new_name):
        """Rename the current playlist.

        Args:
            new_name: The new name.

        Returns:
            True if renamed, False on conflict.
        """
        ok = self._db.rename_playlist(self._playlist_id, new_name)
        if ok:
            self._playlist_name = new_name
            self._save_state()
        return ok

    def delete_playlist(self, name):
        """Delete a playlist by name.

        Args:
            name: The playlist name to delete.

        Returns:
            True if deleted, False if it's the current or doesn't exist.
        """
        if name == self._playlist_name:
            return False
        playlists = self._db.list_playlists()
        for pid, pname in playlists:
            if pname == name:
                self._db.delete_playlist(pid)
                return True
        return False

    def save_playlist_as(self, name):
        """Save the current track list as a new playlist.

        Args:
            name: Name for the new playlist.

        Returns:
            True if saved successfully, False if name already exists.
        """
        if self._db.playlist_exists(name):
            return False
        new_id = self._db.create_playlist(name)
        for track in self.tracks:
            self._db.add_track(
                new_id, track.filepath, track.title,
                track.artist, track.album, track.duration,
            )
        return True

    # ─── Track CRUD ─────────────────────────────────────────────

    def add_file(self, filepath):
        """Add a single audio file to the playlist.

        Args:
            filepath: Absolute path to an audio file.

        Returns:
            The Track object added, or None if file doesn't exist.
        """
        if not os.path.isfile(filepath):
            return None
        # Prevent duplicates
        for t in self.tracks:
            if t.filepath == filepath:
                return None
        title = os.path.splitext(os.path.basename(filepath))[0]
        db_id = self._db.add_track(
            self._playlist_id, filepath, title=title,
        )
        track = Track(filepath, db_id=db_id)
        self.tracks.append(track)
        self._regenerate_shuffle()
        return track

    def add_files(self, filepaths):
        """Add multiple files to the playlist.

        Args:
            filepaths: List of absolute file paths.

        Returns:
            Number of tracks added.
        """
        added = 0
        for fp in filepaths:
            if self.add_file(fp):
                added += 1
        return added

    def add_directory(self, dirpath, audio_extensions=None):
        """Add all audio files from a directory.

        Args:
            dirpath: Directory to scan.
            audio_extensions: Set of extensions to match (default: common audio).

        Returns:
            Number of tracks added.
        """
        if audio_extensions is None:
            from .backend import MpvBackend
            audio_extensions = MpvBackend.AUDIO_EXTENSIONS

        added = 0
        for root, _dirs, files in os.walk(dirpath):
            for f in sorted(files):
                _, ext = os.path.splitext(f)
                if ext.lower() in audio_extensions:
                    track = self.add_file(os.path.join(root, f))
                    if track:
                        added += 1
        return added

    def remove_index(self, index):
        """Remove a track by index.

        Args:
            index: Index of the track to remove.

        Returns:
            True if removed, False if index out of range.
        """
        if 0 <= index < len(self.tracks):
            self._db.remove_track_at(self._playlist_id, index)
            self.tracks.pop(index)
            if self.current_index >= len(self.tracks):
                self.current_index = len(self.tracks) - 1
            elif index < self.current_index:
                self.current_index -= 1
            self._regenerate_shuffle()
            self._save_state()
            return True
        return False

    def remove_indices(self, indices):
        """Remove multiple tracks by indices.

        Args:
            indices: List of indices to remove.
        """
        for idx in sorted(indices, reverse=True):
            self.remove_index(idx)

    def clear(self):
        """Remove all tracks from the playlist."""
        self._db.clear_tracks(self._playlist_id)
        self.tracks.clear()
        self.current_index = -1
        self._shuffle_order.clear()
        self._shuffle_pos = -1
        self._save_state()

    # ─── Navigation ─────────────────────────────────────────────

    def get_current_track(self):
        """Get the currently selected track.

        Returns:
            The current Track object, or None if no track is selected.
        """
        if 0 <= self.current_index < len(self.tracks):
            return self.tracks[self.current_index]
        return None

    def set_current(self, index):
        """Set the current track by index.

        Args:
            index: Track index to select.

        Returns:
            The Track at the given index, or None if invalid.
        """
        if 0 <= index < len(self.tracks):
            self.current_index = index
            self._save_state()
            return self.tracks[index]
        return None

    def next_track(self):
        """Advance to the next track based on mode.

        Returns:
            The next Track, or None if at end (no repeat).
        """
        if not self.tracks:
            return None

        if self.repeat_mode == REPEAT_ONE:
            return self.get_current_track()

        if self.shuffle:
            return self._next_shuffle()

        next_idx = self.current_index + 1
        if next_idx >= len(self.tracks):
            if self.repeat_mode == REPEAT_ALL:
                next_idx = 0
            else:
                return None

        self.current_index = next_idx
        self._save_state()
        return self.tracks[self.current_index]

    def prev_track(self):
        """Go to the previous track.

        Returns:
            The previous Track, or None.
        """
        if not self.tracks:
            return None

        if self.repeat_mode == REPEAT_ONE:
            return self.get_current_track()

        if self.shuffle:
            return self._prev_shuffle()

        prev_idx = self.current_index - 1
        if prev_idx < 0:
            if self.repeat_mode == REPEAT_ALL:
                prev_idx = len(self.tracks) - 1
            else:
                prev_idx = 0

        self.current_index = prev_idx
        self._save_state()
        return self.tracks[self.current_index]

    # ─── Shuffle / Repeat ───────────────────────────────────────

    def toggle_shuffle(self):
        """Toggle shuffle mode on/off."""
        self.shuffle = not self.shuffle
        if self.shuffle:
            self._regenerate_shuffle()
        self._save_state()

    def cycle_repeat(self):
        """Cycle through repeat modes: OFF -> ALL -> ONE -> OFF.

        Returns:
            The new repeat mode constant.
        """
        self.repeat_mode = (self.repeat_mode + 1) % 3
        self._save_state()
        return self.repeat_mode

    def _regenerate_shuffle(self):
        """Regenerate the shuffle order."""
        if not self.tracks:
            self._shuffle_order = []
            self._shuffle_pos = -1
            return

        self._shuffle_order = list(range(len(self.tracks)))
        random.shuffle(self._shuffle_order)  # NOSONAR - not security-sensitive, just playlist order

        # Put current track at the beginning
        if 0 <= self.current_index < len(self.tracks):
            if self.current_index in self._shuffle_order:
                self._shuffle_order.remove(self.current_index)
                self._shuffle_order.insert(0, self.current_index)
            self._shuffle_pos = 0
        else:
            self._shuffle_pos = -1

    def _next_shuffle(self):
        """Get next track in shuffle order."""
        if not self._shuffle_order:
            return None

        self._shuffle_pos += 1
        if self._shuffle_pos >= len(self._shuffle_order):
            if self.repeat_mode == REPEAT_ALL:
                self._regenerate_shuffle()
                self._shuffle_pos = 0
            else:
                self._shuffle_pos = len(self._shuffle_order) - 1
                return None

        self.current_index = self._shuffle_order[self._shuffle_pos]
        self._save_state()
        return self.tracks[self.current_index]

    def _prev_shuffle(self):
        """Get previous track in shuffle order."""
        if not self._shuffle_order:
            return None

        self._shuffle_pos -= 1
        if self._shuffle_pos < 0:
            self._shuffle_pos = 0
            return (self.tracks[self._shuffle_order[0]]
                    if self._shuffle_order else None)

        self.current_index = self._shuffle_order[self._shuffle_pos]
        self._save_state()
        return self.tracks[self.current_index]

    # ─── Track metadata sync ───────────────────────────────────

    def update_track_metadata(self, track, metadata):
        """Update a track's metadata in memory and database.

        Args:
            track: The Track object to update.
            metadata: dict with optional 'title', 'artist', 'album' keys.
        """
        track.update_metadata(metadata)
        if track.db_id:
            self._db.update_track_metadata(
                track.db_id,
                title=track.title,
                artist=track.artist,
                album=track.album,
            )

    def update_track_duration(self, track, duration):
        """Update a track's duration in memory and database.

        Args:
            track: The Track object to update.
            duration: Duration in seconds.
        """
        track.duration = duration
        if track.db_id:
            self._db.update_track_metadata(track.db_id, duration=duration)

    # ─── Properties ─────────────────────────────────────────────

    @property
    def count(self):
        """Number of tracks in the playlist."""
        return len(self.tracks)

    @property
    def is_empty(self):
        """Whether the playlist is empty."""
        return len(self.tracks) == 0

    def total_duration_str(self):
        """Get total playlist duration as formatted string.

        Returns:
            String like '1:23:45' or '0:00' if unknown.
        """
        total = sum(t.duration for t in self.tracks)
        return format_time(total)

    # ─── Cleanup ────────────────────────────────────────────────

    def close(self):
        """Save state and close the database connection."""
        self._save_state()
        self._db.close()


def format_time(seconds):
    """Format seconds into a time string.

    Args:
        seconds: Number of seconds.

    Returns:
        Formatted string like '3:45' or '1:02:30'.
    """
    if seconds <= 0 or seconds != seconds:  # handles NaN
        return "0:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
