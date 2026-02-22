"""
madOS Video Player - Playlist Manager
=======================================

Pure Python playlist management with no GTK dependencies.
Supports adding files, directories, shuffle, repeat modes,
and navigation (next/previous).
"""

import os
import random

# Supported video extensions
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".3gp", ".ogv", ".ts", ".vob",
    ".divx", ".asf", ".rm", ".rmvb", ".m2ts", ".mts",
}

# Supported audio extensions (player can handle audio-only too)
AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".ogg", ".opus", ".wav", ".aac", ".m4a",
    ".wma", ".ape", ".alac",
}

ALL_MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def is_media_file(filepath):
    """Check whether a file path has a recognized media extension.

    Args:
        filepath: Path to check.

    Returns:
        True if the extension is a known video or audio format.
    """
    _, ext = os.path.splitext(filepath)
    return ext.lower() in ALL_MEDIA_EXTENSIONS


def is_video_file(filepath):
    """Check whether a file path has a recognized video extension.

    Args:
        filepath: Path to check.

    Returns:
        True if the extension is a known video format.
    """
    _, ext = os.path.splitext(filepath)
    return ext.lower() in VIDEO_EXTENSIONS


def scan_directory(directory, recursive=False):
    """Scan a directory for media files.

    Args:
        directory: Path to the directory to scan.
        recursive: If True, scan subdirectories as well.

    Returns:
        Sorted list of absolute paths to media files found.
    """
    results = []
    if not os.path.isdir(directory):
        return results

    if recursive:
        for root, _dirs, files in os.walk(directory):
            for fname in files:
                fullpath = os.path.join(root, fname)
                if is_media_file(fullpath):
                    results.append(fullpath)
    else:
        for fname in os.listdir(directory):
            fullpath = os.path.join(directory, fname)
            if os.path.isfile(fullpath) and is_media_file(fullpath):
                results.append(fullpath)

    results.sort()
    return results


class RepeatMode:
    """Enumeration for repeat modes."""
    NONE = "none"
    ALL = "all"
    ONE = "one"


class Playlist:
    """Manages an ordered list of media file paths with navigation.

    Attributes:
        items: List of file paths in the playlist.
        current_index: Index of the currently selected item (-1 if empty).
        repeat_mode: One of RepeatMode.NONE, .ALL, or .ONE.
        shuffle: Whether shuffle mode is enabled.
    """

    def __init__(self):
        """Initialize an empty playlist."""
        self.items = []
        self.current_index = -1
        self.repeat_mode = RepeatMode.NONE
        self.shuffle = False
        self._shuffle_order = []
        self._shuffle_pos = -1

    @property
    def count(self):
        """Return the number of items in the playlist."""
        return len(self.items)

    @property
    def current(self):
        """Return the current file path, or None if empty."""
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    @property
    def is_empty(self):
        """Return True if the playlist has no items."""
        return len(self.items) == 0

    def clear(self):
        """Remove all items from the playlist."""
        self.items.clear()
        self.current_index = -1
        self._shuffle_order.clear()
        self._shuffle_pos = -1

    def add_file(self, filepath):
        """Add a single file to the playlist.

        Args:
            filepath: Absolute path to a media file.

        Returns:
            True if the file was added, False if not a media file.
        """
        if not os.path.isfile(filepath):
            return False
        if not is_media_file(filepath):
            return False
        self.items.append(os.path.abspath(filepath))
        if self.current_index < 0:
            self.current_index = 0
        self._rebuild_shuffle()
        return True

    def add_directory(self, directory, recursive=False):
        """Add all media files from a directory.

        Args:
            directory: Path to scan.
            recursive: If True, include subdirectories.

        Returns:
            Number of files added.
        """
        files = scan_directory(directory, recursive)
        count = 0
        for f in files:
            self.items.append(f)
            count += 1
        if count > 0 and self.current_index < 0:
            self.current_index = 0
        if count > 0:
            self._rebuild_shuffle()
        return count

    def remove(self, index):
        """Remove item at the given index.

        Args:
            index: Index of the item to remove.

        Returns:
            True if removed, False if index is invalid.
        """
        if index < 0 or index >= len(self.items):
            return False
        self.items.pop(index)
        if len(self.items) == 0:
            self.current_index = -1
        elif self.current_index >= len(self.items):
            self.current_index = len(self.items) - 1
        elif index < self.current_index:
            self.current_index -= 1
        self._rebuild_shuffle()
        return True

    def select(self, index):
        """Select an item by index.

        Args:
            index: Index to select.

        Returns:
            The file path at that index, or None if invalid.
        """
        if index < 0 or index >= len(self.items):
            return None
        self.current_index = index
        # Update shuffle position to match
        if self.shuffle and self._shuffle_order:
            try:
                self._shuffle_pos = self._shuffle_order.index(index)
            except ValueError:
                pass
        return self.items[self.current_index]

    def next(self):
        """Advance to the next track.

        Respects shuffle and repeat modes.

        Returns:
            The file path of the next track, or None if at the end.
        """
        if len(self.items) == 0:
            return None

        if self.repeat_mode == RepeatMode.ONE:
            return self.current

        if self.shuffle:
            return self._next_shuffle()

        next_idx = self.current_index + 1
        if next_idx >= len(self.items):
            if self.repeat_mode == RepeatMode.ALL:
                next_idx = 0
            else:
                return None

        self.current_index = next_idx
        return self.items[self.current_index]

    def previous(self):
        """Go back to the previous track.

        Respects shuffle and repeat modes.

        Returns:
            The file path of the previous track, or None if at the start.
        """
        if len(self.items) == 0:
            return None

        if self.repeat_mode == RepeatMode.ONE:
            return self.current

        if self.shuffle:
            return self._prev_shuffle()

        prev_idx = self.current_index - 1
        if prev_idx < 0:
            if self.repeat_mode == RepeatMode.ALL:
                prev_idx = len(self.items) - 1
            else:
                return None

        self.current_index = prev_idx
        return self.items[self.current_index]

    def cycle_repeat(self):
        """Cycle through repeat modes: NONE -> ALL -> ONE -> NONE.

        Returns:
            The new repeat mode string.
        """
        if self.repeat_mode == RepeatMode.NONE:
            self.repeat_mode = RepeatMode.ALL
        elif self.repeat_mode == RepeatMode.ALL:
            self.repeat_mode = RepeatMode.ONE
        else:
            self.repeat_mode = RepeatMode.NONE
        return self.repeat_mode

    def toggle_shuffle(self):
        """Toggle shuffle mode on or off.

        Returns:
            The new shuffle state.
        """
        self.shuffle = not self.shuffle
        if self.shuffle:
            self._rebuild_shuffle()
        return self.shuffle

    def _rebuild_shuffle(self):
        """Rebuild the shuffle order."""
        if len(self.items) == 0:
            self._shuffle_order = []
            self._shuffle_pos = -1
            return
        self._shuffle_order = list(range(len(self.items)))
        random.shuffle(self._shuffle_order)
        # Put current index at position 0 so current track is first
        if self.current_index >= 0 and self.current_index in self._shuffle_order:
            self._shuffle_order.remove(self.current_index)
            self._shuffle_order.insert(0, self.current_index)
        self._shuffle_pos = 0

    def _next_shuffle(self):
        """Get next item in shuffle order."""
        if not self._shuffle_order:
            return None
        self._shuffle_pos += 1
        if self._shuffle_pos >= len(self._shuffle_order):
            if self.repeat_mode == RepeatMode.ALL:
                self._rebuild_shuffle()
                self._shuffle_pos = 0
            else:
                self._shuffle_pos = len(self._shuffle_order) - 1
                return None
        self.current_index = self._shuffle_order[self._shuffle_pos]
        return self.items[self.current_index]

    def _prev_shuffle(self):
        """Get previous item in shuffle order."""
        if not self._shuffle_order:
            return None
        self._shuffle_pos -= 1
        if self._shuffle_pos < 0:
            if self.repeat_mode == RepeatMode.ALL:
                self._shuffle_pos = len(self._shuffle_order) - 1
            else:
                self._shuffle_pos = 0
                return None
        self.current_index = self._shuffle_order[self._shuffle_pos]
        return self.items[self.current_index]

    def get_display_name(self, index=None):
        """Get a human-friendly display name for a playlist item.

        Args:
            index: Index to look up. Defaults to current_index.

        Returns:
            The filename without path, or empty string if invalid.
        """
        if index is None:
            index = self.current_index
        if index < 0 or index >= len(self.items):
            return ""
        return os.path.basename(self.items[index])
